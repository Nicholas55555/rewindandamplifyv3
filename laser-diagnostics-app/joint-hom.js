/* Exact saved instrument/design results; no fitting or power simulation here. */
'use strict';
(function(){
 const $=id=>document.getElementById(id),S=window.RESEARCH_DATA.sources;
 const pct=(x,n=2)=>(100*x).toFixed(n)+'%';
 function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
 function value(area,label,number,note){const cell=el('div','research-value');cell.append(el('small','',label),el('strong','',number),el('span','',note));area.append(cell);}
 const main=S.joint_hom.regimes.find(r=>r.name==='controlled'),source=main.cases.find(c=>c.name==='coherent_nominal'),nullCase=main.cases.find(c=>c.name==='classical_nominal');
 value($('joint-main-values'),'Nominal coherent flags',pct(source.flag_rate),`${source.flagged_records} / ${source.records.toLocaleString()} records`);
 value($('joint-main-values'),'Classical nominal false flags',pct(nullCase.flag_rate),`${nullCase.flagged_records} / ${nullCase.records.toLocaleString()} records`);
 value($('joint-main-values'),'Passive observation','No information','the specified two record laws are identical');
 $('joint-main-finding').textContent='The measurement instrument is implemented and independently checked. Its first controlled test is a useful negative result: 64 pairs barely distinguish these two specified hypotheses. Passive data cannot distinguish them at all. A quantum hidden-state description alone does not make that state observable.';
 const study=S.dot_design_validation,design=S.dot_design;
 for(const trial of study.power_trials){const o=el('option','',trial.attempted_pairs.toLocaleString()+` pairs · ${trial.independent_blocks.toLocaleString()} reset blocks`);o.value=trial.independent_blocks;$('dot-design-budget').append(o);}
 $('dot-design-budget').value='646';
 function render(){
  const trial=study.power_trials.find(t=>t.independent_blocks===Number($('dot-design-budget').value)),find=name=>trial.cases.find(c=>c.name===name),q=find('coherent_nominal'),c=find('classical_nominal'),mode=find('classical_mode_mismatch'),loss=find('classical_loss_shift'),readout=find('classical_readout_shift');
  const area=$('dot-design-values');area.replaceChildren();
  for(const [label,row,note]of [['Nominal detection',q,'specified coherent source'],['Nominal false flags',c,'specified classical source'],['Mode-mismatch false flags',mode,'still a classical source']])value(area,label,pct(row.flag_rate),`${note} · 95% ${pct(row.wilson95[0])}–${pct(row.wilson95[1])}`);
  $('dot-design-detail').textContent=`${trial.independent_blocks.toLocaleString()} independent four-pair blocks cost ${trial.attempted_pairs.toLocaleString()} attempted pairs / ${trial.source_excitations.toLocaleString()} modeled source excitations per record. Independent calibration supplies a strict nominal-null threshold. The environment is not retained between these blocks.`;
  $('dot-design-warning').textContent=`At this budget, unmodeled readout changes give ${pct(readout.flag_rate)} false flags and lower collection gives ${pct(loss.flag_rate)}. Mode mismatch gives ${pct(mode.flag_rate)}. More data can amplify a wrong acquisition model; a flag is not proof of a coherent defect.`;
  const body=$('dot-power-table').querySelector('tbody');body.replaceChildren();
  for(const t of study.power_trials){const row=el('tr',t.independent_blocks===trial.independent_blocks?'selected':'');row.append(el('th','',t.attempted_pairs.toLocaleString()));row.firstChild.scope='row';for(const name of ['coherent_nominal','classical_nominal'])row.append(el('td','',pct(t.cases.find(c=>c.name===name).flag_rate)));body.append(row);}
 }
 const hmm=study.prediction_scores.hmm_8.paired_gain_vs_calibrated_physical;
 $('dot-hmm-finding').textContent=`The 8-state HMM differs by ${hmm.mean.toFixed(7)} nats per attempted pair from the given-physics predictor; its paired 95% interval [${hmm.approximate_interval95[0].toFixed(7)}, ${hmm.approximate_interval95[1].toFixed(7)}] includes zero. Both HMM sizes use the same 20,000 training blocks, ten starts each. All starts reach the 200-iteration cap; global optimality is not established. An exact classical categorical law reproduces every finite-block distribution.`;
 const low=design.loss_sensitivity.find(x=>x.design==='selected'&&x.parameters.eta===.2),nominal=design.selected.information;
 $('dot-design-cost').textContent=`An exact-model sufficient bound needs ${(nominal.sufficient_independent_blocks_alpha05_power80*4).toLocaleString()} attempted pairs at 80% photon survival for ≤5% false flags and ≥80% power. At 20% survival it rises to ${(low.information.sufficient_independent_blocks_alpha05_power80*4).toLocaleString()}. These are sufficient bounds for known calibration and perfect resets, not minimum costs or validated acquisition times.`;
 $('dot-design-budget').addEventListener('change',render);render();window.JointHomUI={render};
})();
