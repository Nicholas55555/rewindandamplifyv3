/* Render exact saved research outputs. Selectors never refit or rerun a model. */
'use strict';
(function(){
 const B=window.RESEARCH_DATA,S=B.sources,$=id=>document.getElementById(id);
 const colors=['#edb568','#64d9e9','#b9a8e5'];
 const pct=(x,n=2)=>(100*x).toFixed(n)+'%';
 const signed=x=>(x>=0?'+':'')+(100*x).toFixed(2)+'%';
 const label={
  unseen_nominal_sessions:'New nominal sessions',unseen_short_coherence:'Reduced atomic coherence',atomic_reference_changes:'Atomic reference also changes',primary_reference_changes:'Primary optical reference changes',common_sampled_path_changes:'Shared sampled path changes',source_power_changes_only_in_null:'Power changes in both populations',
  stable_source:'Stable source',source_step_20pct:'+20% field step',source_telegraph_20pct:'+20% telegraph drive',source_step_10pct:'+10% field step',source_telegraph_fast:'Faster telegraph switching',stable_source_efficiency_loss:'Stable source · efficiency loss',stable_source_dark_increase:'Stable source · increased dark counts',stable_source_emitter_detuning:'Stable source · emitter detuning',stable_source_cavity_loss:'Stable source · cavity loss',stable_source_deadtime:'Stable source · detector dead time',stable_source_afterpulse:'Stable source · afterpulsing',stable_source_combined_detector:'Stable source · combined detector changes',source_step_with_efficiency_loss:'+20% field step + efficiency loss',
  ideal:'Ideal efficiency',high_efficiency:'High efficiency · 81% total',moderate_loss:'Moderate loss · 48% total',severe_loss:'Severe loss · 12% total',ten_percent_preparation:'10% preparation success',one_percent_preparation:'1% preparation success',detector_loss:'Detector loss · 27% total'
 };
 function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
 function select(id,values,chosen){const s=$(id);s.replaceChildren();for(const v of values){const o=el('option','',label[v]||v);o.value=v;s.append(o);}s.value=chosen;}
 function bar(container,name,value,details,index,ci){
  const row=el('div','metric research-metric'),heading=el('div','metric-title');heading.append(el('span','',name),el('strong','',pct(value)));
  const track=el('div','bar-track'),fill=el('div','bar-fill');fill.style.width=pct(value,6);fill.style.background=colors[index%3];track.append(fill);
  row.append(heading,track,el('small','',details));
  if(ci)row.append(el('small','',`Descriptive 95% interval ${pct(ci[0])}–${pct(ci[1])}`));
  container.append(row);
 }
 function value(container,title,number,note,color){const cell=el('div','research-value');cell.append(el('small','',title));const n=el('strong','',number);if(color)n.style.color=color;cell.append(n,el('span','',note));container.append(cell);}
 function frequency(){
  const c=S.frequency.scenarios.find(x=>x.id===$('frequency-case').value),agreement=$('frequency-rule').value==='agreement';
  const ids=['classical',agreement?'classical_quantum_agreement':'classical_quantum',agreement?'two_classical_agreement':'two_classical'];
  const names=['Conventional receiver',`+ Atomic reference${agreement?' · agreement':''}`,`+ Independent coherent reference${agreement?' · agreement':''}`];
  const descriptions={unseen_nominal_sessions:'Independent new sessions drawn from the calibration population. The source onset is hidden from the detector.',unseen_short_coherence:'New atomic coherence times are reduced by a factor of 0.06. All fitted rules and thresholds stay frozen.',atomic_reference_changes:'A separate ±0.7 Hz atomic-reference step can occur in both source-event and frequency-null records.',primary_reference_changes:'A separate ±0.7 Hz primary-reference step can occur in both source-event and frequency-null records.',common_sampled_path_changes:'A separate ±0.7 Hz shared-path step appears in every frequency channel. These observations cannot distinguish it from a source shift.',source_power_changes_only_in_null:'A 10% intensity step occurs in both populations. Frequency-null records contain no injected source-frequency step.'};
  $('frequency-description').textContent=descriptions[c.id];const area=$('frequency-metrics');area.replaceChildren();
  ids.forEach((id,i)=>{const m=c.methods[id];bar(area,names[i],m.detection_within_32s,`${m.counts.detection_within_32s.toLocaleString()} / ${c.records_per_class.toLocaleString()} source-event records · false alarms ${pct(m.false_alarm_rate)} (${m.counts.false_alarm_rate} / ${c.records_per_class.toLocaleString()} frequency-null records)`,i,m.detection_within_32s_ci95);});
  const q=c.methods[ids[1]],cc=c.methods[ids[2]],a=c.methods.classical;
  let finding;
  if(c.id==='unseen_nominal_sessions'&&!agreement){const p=c.paired_comparisons.classical_to_classical_quantum;finding=`The atomic addition gains ${(100*p.detection_difference).toFixed(2)} percentage points over this receiver (95% interval ${(100*p.detection_difference_ci95[0]).toFixed(2)}–${(100*p.detection_difference_ci95[1]).toFixed(2)}). The independent coherent reference reaches ${pct(cc.detection_within_32s)} and wins this benchmark.`;}
  else if(c.id==='common_sampled_path_changes')finding=`A second lens cannot remove a shared ambiguity. False source alarms reach ${pct(q.false_alarm_rate)} with the atomic combination and ${pct(cc.false_alarm_rate)} with the second coherent reference.`;
  else if(c.id==='unseen_short_coherence')finding=`With this coherence loss, atomic-combination detection is ${pct(q.detection_within_32s)}, versus ${pct(a.detection_within_32s)} for the receiver alone. An added channel is not automatically an improvement.`;
  else if(agreement)finding=`Agreement trades sensitivity for consistency. Its false-alarm rates here are ${pct(q.false_alarm_rate)} (atomic) and ${pct(cc.false_alarm_rate)} (second coherent). Compare both with the nominal 5% whole-record target; agreement does not guarantee source attribution.`;
  else finding=`A reference or detector change can imitate a source event. Inspect the false-alarm rates as well as timely detection; the same frozen rules are applied to this stress condition.`;
  $('frequency-finding').textContent=finding;
 }
 function drive(){
  const id=$('drive-case').value,c=S.drive.cases[id],prior=S.prior.cases[id],source=c.has_source_change_generator;
  const main=c.methods.physical_history,eligible=main.detection_within32.records;
  const nullControl=S.drive.cases[id==='source_step_with_efficiency_loss'?'stable_source_efficiency_loss':'stable_source'];
  $('drive-description').textContent=source?`${label[id]}. The source path is hidden from all estimators. A conditional quantum state persists between observations; each record is reset only at its beginning.`:`${label[id]}. There is no source-drive change. An alarm is a false source attribution, even if a real detector or emitter perturbation occurred.`;
  $('drive-metric-title').textContent=source?'First valid detection within 32 bins':'False source alarms in a complete 96-bin record';
  $('drive-denominator').textContent=source?`${eligible} eligible source-onset records; ${main.no_event_records} records never activate and ${main.late_onset_records} activate too late for 32-bin follow-up. Premature alarms and misses count as failures.`:'512 held-out records per condition, across four independent calibration/training pipelines. Bars share a 0–100% scale.';
  const area=$('drive-metrics');area.replaceChildren();
  ['physical_history','classical_hmm','count_contrast'].forEach((id,i)=>{const m=c.methods[id],stat=source?m.detection_within32:m.record_alarm_fraction;
   const count=Math.round(stat.value*stat.records),nullRate=nullControl.methods[id].record_alarm_fraction.value;
   const detail=source?`${count} / ${stat.records} eligible records · premature alarms ${pct(m.prealarm_fraction_of_eligible_events.value)} · restricted delay ${m.restricted_delay32_bins.value.toFixed(2)} / 32 bins. False alarms ${pct(nullRate)} in separate source-stable 96-bin records${$('drive-case').value==='source_step_with_efficiency_loss'?' with efficiency loss':''}.`:`${count} / ${stat.records} source-stable records · nominal threshold target 5% per record`;
   bar(area,['Physical-history filter','Three-state classical HMM','Adjacent-window count contrast'][i],stat.value,detail,i,stat.hierarchical_bootstrap_95);
  });
  const values=$('drive-rmse');values.replaceChildren();
  value(values,'Uses the observed bits',prior.observation_based_rmse.value.toFixed(4),'causal posterior mean',colors[1]);
  value(values,'Same prior · no observed bits',prior.prior_only_rmse.value.toFixed(4),'no per-record update',colors[0]);
  value(values,'Keep fitted baseline',c.zero_change_fraction_rmse.value.toFixed(4),'no source-change estimate',colors[2]);
  const diff=prior.prior_only_rmse.value-prior.observation_based_rmse.value;
  $('drive-prior-finding').textContent=`The observation-based RMSE is ${Math.abs(diff).toFixed(4)} ${diff>=0?'lower':'higher'} than the prior-only value. Its signed drive bias is ${signed(c.physical_fraction_bias.value)} of baseline. ${source?'Improvement over a constant alone does not establish useful measurement information.':'The one-sided source-change prior can produce a positive estimate even when the source is stable.'}`;
  $('drive-finding').textContent=source?`This operating point does not provide useful prompt source diagnosis. Across source cases, most RMSE improvement over a constant is already explained by the fitted prior. The observations only slightly improve the +20% step and worsen the other four source-case RMSEs.`:`Detector and emitter controls test attribution. A modeled change in the observed record is not proof of a changed laser. The additional calibration needed for a physical device remains unmeasured.`;
 }
 function phase(){
  const c=S.phase.cases.find(x=>x.id===$('phase-case').value),key=$('phase-budget').value,b=c.budgets[key],setup=c.setup;
  $('phase-description').textContent=`Unknown phase over a full 2π range. Total transmission × detection efficiency: ${pct(setup.object_transmission*setup.detection_efficiency,0)}. Preparation success: ${pct(setup.preparation_success,0)}. ${key==='equal_sample_photons'?'20,000 mean object-incident photons for each method.':'10,000 source-attempt clocks for each method; photon dose can differ.'}`;
  const area=$('phase-metrics');area.replaceChildren();
  ['coherent','hybrid','noon'].forEach((id,i)=>{const m=b[id],g=m.global,r=m.resources,card=el('article','phase-card');card.append(el('h4','',['Coherent comparator','Charged coherent + NOON hybrid','Pure two-photon NOON'][i]));
   card.append(el('span','phase-value-label','Full-2π phase RMSE'),el('strong','phase-rmse',g.rmse_full_2pi_rad.toFixed(5)+' rad'));
   card.append(el('p','caption',`95% Monte Carlo interval ${g.rmse_mc_interval95_rad[0].toFixed(5)}–${g.rmse_mc_interval95_rad[1].toFixed(5)} rad`));
   const details=el('dl','phase-details');for(const [k,v]of [['Within a π branch',g.rmse_modulo_pi_rad.toFixed(5)+' rad'],['Wrong π branch',pct(g.wrong_pi_branch_rate)],['95% upper branch-error bound',pct(g.wrong_pi_branch_wilson95[1],3)],['Mean photons before object',r.sample_incident_mean_photons_before_object.toLocaleString(undefined,{maximumFractionDigits:0})],['Source attempts',r.attempted_clocks.toLocaleString()],['Time at assumed 1 MHz',r.elapsed_seconds_at_assumed_clock.toFixed(3)+' s']]){const row=el('div');row.append(el('dt','',k),el('dd','',v));details.append(row);}card.append(details);area.append(card);
  });
  const coherent=b.coherent.global.rmse_full_2pi_rad,hybrid=b.hybrid.global.rmse_full_2pi_rad;
  $('phase-finding').textContent=`The hybrid has ${hybrid<coherent?'lower':'higher'} global RMSE than the specified coherent comparator in this setting (${hybrid.toFixed(5)} versus ${coherent.toFixed(5)} rad). Pure NOON’s fine fringe is π-periodic: a small within-branch error hides its global ambiguity. Loss and failed preparation can erase a favorable precision or time comparison.`;
 }
 function progress(){
  const values=$('inference-values');values.replaceChildren();
  value(values,'Synthetic truth',S.inference_aware.generator_parameters.g_defect.toFixed(3),'coupling in model units');
  value(values,'Ignore detector dead time',S.inference_ignored.joint_parameters.g_defect.toFixed(3),'fitted hidden coupling',colors[0]);
  value(values,'Model detector dead time',S.inference_aware.joint_parameters.g_defect.toFixed(3),'fitted hidden coupling',colors[1]);
  const ledger=$('spatial-values'),f=S.spatial;ledger.replaceChildren();
  const q=f.circuits.find(c=>c.style==='clean'&&c.status==='completed').qubits;
  value(ledger,'Explicit clean-ancilla circuit',q.toLocaleString()+' qubits','196 data + 23 score + 170 additional clean ancillas',colors[1]);
  for(const id of ['ceil','floor'])value(ledger,`${id==='ceil'?'Upper':'Lower'} rounded weights`,f.explicit_synthesis_costs[id].complete_one_round_generic_cx_constructive_upper_bound.toLocaleString()+' CX','one complete round · constructive upper bound',colors[0]);
 }
 function show(id){document.querySelectorAll('[data-study]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.study===id));document.querySelectorAll('.research-study').forEach(s=>s.hidden=s.id!=='research-'+id);if(id==='dot'&&window.QuantumDotUI)requestAnimationFrame(()=>window.QuantumDotUI.drawHistogram());}
 select('frequency-case',S.frequency.scenarios.map(c=>c.id),'unseen_nominal_sessions');select('drive-case',Object.keys(S.drive.cases),'source_step_20pct');select('phase-case',S.phase.cases.map(c=>c.id),'high_efficiency');
 for(const id of ['frequency-case','frequency-rule'])$(id).addEventListener('change',frequency);
 $('drive-case').addEventListener('change',drive);for(const id of ['phase-case','phase-budget'])$(id).addEventListener('change',phase);
 document.querySelectorAll('[data-study]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.study)));
 frequency();drive();phase();progress();window.ResearchUI={show,frequency,drive,phase};
})();
