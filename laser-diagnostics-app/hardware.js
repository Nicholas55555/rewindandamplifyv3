/* Raw campaign summaries only; no submission, mitigation or live inference. */
'use strict';
(function(){
 const $=id=>document.getElementById(id),H=window.RESEARCH_DATA.sources.hardware;
 const pct=(x,n=2)=>x===null?'Not available':(100*x).toFixed(n)+'%',num=x=>Number(x).toLocaleString();
 function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
 function value(area,label,number,note){const e=el('div','research-value');e.append(el('small','',label),el('strong','',number),el('span','',note));area.append(e);}
 function link(area,href,text){const a=el('a','hardware-evidence-link',text);a.href=href;if(href.startsWith('https:')){a.target='_blank';a.rel='noopener noreferrer';}area.append(a);}
 const localPath=path=>'evidence/hardware/'+path.replace(/^hardware_campaign\//,'');
 $('hardware-summary').textContent=`${H.jobs} completed jobs · ${num(H.science_circuit_executions)} science + ${num(H.calibration_circuit_executions)} calibration circuit executions · ${num(H.total_shots)} shots · ${num(H.actual_campaign_quantum_seconds)} charged QPU seconds. This is QPU usage, not wall time or a price.`;
 const hero=H.headline_original;
 for(const [key,label]of [['local','Steered local reflection'],['full','Steered full reflection']]){
  const r=hero[key],card=el('article','hardware-result-card');card.append(el('h4','',label),el('strong','',pct(r.probability)),el('p','',`${num(r.accepted)} / ${num(r.shots)} raw accepted trials · 95% ${pct(r.wilson95[0])}–${pct(r.wilson95[1])}`));
  const list=el('dl');for(const [term,text]of [['Native two-qubit gates',num(r.native_two_qubit_gates)],['Conditional-history TV error',r.selected_history_tv_to_unsteered.toFixed(4)],['Logical ideal acceptance',pct(r.logical_ideal_acceptance)]]){const row=el('div');row.append(el('dt','',term),el('dd','',text));list.append(row);}card.append(list);$('hardware-original').append(card);
 }
 const delta=hero.difference,ci=delta.independent_shot_wilson_based_interval95;
 $('hardware-original-finding').textContent=`Local reflection accepts ${(100*delta.probability_difference).toFixed(2)} percentage points more in this fresh run (95% interval ${(100*ci[0]).toFixed(2)}–${(100*ci[1]).toFixed(2)} points), with fewer native gates. Its accepted distribution still has TV error ${hero.local.selected_history_tv_to_unsteered.toFixed(4)}. More useful shots and a correct answer are separate checks.`;
 const families={dot_frozen:'Dot: original photon-pair overlap',dot_joint:'Dot: retained joint-photon instrument',dot_selected_four_pair:'Dot: selected four-pair design',atomic:'Atomic channel emulation',photon:'Photon occupations and interference',spatial:'Spatial 2×2 query',optical_dilation:'Deep retained optical instrument'};
 for(const [key,label]of Object.entries(families)){const o=el('option','',label);o.value=key;$('hardware-family').append(o);}
 $('hardware-family').value='dot_selected_four_pair';
 function selected(){return H.family_results[$('hardware-family').value][Number($('hardware-circuit').value)];}
 function render(){
  const row=selected(),o=row.observables,run=H.runs.find(r=>r.id===row.run),area=$('hardware-values');area.replaceChildren();
  $('hardware-circuit-context').textContent=`${row.name} · ${row.run} · ${num(row.shots)} shots · ${row.logical_qubits} logical qubits · ${num(row.native_two_qubit_gate_count)} compiled native two-qubit gates · depth ${num(row.compiled_depth)}.`;
  let scope=o.scope||o.interpretation||'Raw measured probability distributions; finite-shot error is included. No optical apparatus is measured.';
  if(o.histories){
   const h=o.histories[$('hardware-history').value];
   value(area,'Recorded history frequency',pct(h.observed.probability),`${h.observed.successes} / ${h.observed.shots} shots; ideal ${pct(h.ideal_probability)}; 95% ${pct(h.observed.wilson95[0])}–${pct(h.observed.wilson95[1])}`);
   value(area,'Whole flag-history TV',o.flag_history_tv.toFixed(4),'distance from ideal record distribution; includes shot noise');
   if(h.conditional_memory_zero){value(area,`Memory zero | history (${o.memory_measurement_basis})`,pct(h.conditional_memory_zero.probability),`${h.conditional_memory_zero.successes} / ${h.conditional_memory_zero.shots} selected shots; ideal ${pct(h.ideal_conditional_memory_zero)}; 95% ${pct(h.conditional_memory_zero.wilson95[0])}–${pct(h.conditional_memory_zero.wilson95[1])}`);}
   else value(area,'Raw SWAP overlap estimate',o.raw_swap_overlap_estimate.toFixed(4),`ideal ${o.ideal_overlap.toFixed(4)}; derived from raw coincidence counts`);
   $('hardware-comparison').textContent=`Flag history ${$('hardware-history').value} is chronological. ${row.reference_marginal_qubits?'This wider circuit has only a declared flag/memory marginal reference, not a full-register reference. ':''}Conditional memory probabilities are measured only in the named basis; they are not complete state tomography.`;
  }else if(Object.hasOwn(o,'raw_event_probability')){
   value(area,'Raw accepted event',pct(o.raw_event_probability),`${o.accepted_shots} / ${o.shots} shots; ideal ${pct(o.ideal_event_probability)}`);
   value(area,'Selected-data TV error',o.selected_data_z_distribution_tv===null?'No accepted shots':o.selected_data_z_distribution_tv.toFixed(4),'conditional answer distribution; not state fidelity');
   value(area,'Whole data-register TV',o.data_z_distribution_tv.toFixed(4),'unconditional measured Z distribution');
   $('hardware-comparison').textContent=`No workspace postselection is applied. Dirty workspace fraction ${pct(o.dirty_workspace_fraction)}. A small event-rate error can coexist with a wrong conditional answer.`;
  }else if(Object.hasOwn(o,'raw_system_zero_probability')){
   value(area,'Raw system-zero outcome',pct(o.raw_system_zero_probability),`ideal ${pct(o.ideal_system_zero_probability)}; ${o.basis} basis`);
   value(area,'Absolute probability error',pct(o.absolute_probability_error),'raw channel-output difference, not an event-acceptance task');
   value(area,'95% shot interval',`${pct(o.raw_system_zero_wilson95[0])}–${pct(o.raw_system_zero_wilson95[1])}`,'excludes calibration and drift');
   $('hardware-comparison').textContent='This tests one finite-pulse atomic-channel encoding. It does not reproduce the complete unknown-onset laser-monitoring experiment.';
  }else if(Object.hasOwn(o,'occupancy_tv')){
   value(area,'Photon-occupation TV',o.occupancy_tv.toFixed(4),'digital occupation law versus ideal');
   value(area,'Raw mean occupation, port A',o.raw_moments.mean_a.mean.toFixed(4),`ideal ${o.raw_moments.mean_a.ideal.toFixed(4)}`);
   value(area,'Source-flag failure fraction',pct(o.source_flag_failure_fraction),'failed modeled preparations remain charged');
   $('hardware-comparison').textContent='This is an encoded photon-number/interference component. It does not repeat a full photon-dose-budget phase estimate or expose a resist.';
  }else throw Error('Unsupported hardware observable schema: '+row.name);
  if(row.raw_reference_marginal_z_tv!==undefined)scope+=` Raw declared-marginal TV: ${row.raw_reference_marginal_z_tv.toFixed(4)}. Ideal multinomial expected TV at this shot count: ${row.ideal_multinomial_expected_reference_marginal_tv_at_these_shots.toFixed(4)}.`;
  else if(row.raw_full_z_tv!==undefined)scope+=` Raw full-register Z TV: ${row.raw_full_z_tv.toFixed(4)}. Ideal multinomial expected TV at this shot count: ${row.ideal_multinomial_expected_full_z_tv_at_these_shots.toFixed(4)}. These are measured-distribution comparisons, not state fidelity.`;
  $('hardware-scope').textContent=scope;
  const evidence=$('hardware-evidence');evidence.replaceChildren();link(evidence,localPath(run.raw_path),'Raw counts ↗');evidence.append(document.createTextNode(' · '));link(evidence,localPath(run.analysis_path),'Full analysis ↗');evidence.append(document.createTextNode(' · '));link(evidence,localPath(run.plan_path),'Submitted plan ↗');
 }
 function circuit(){const o=selected().observables,h=$('hardware-history');h.replaceChildren();$('hardware-history-label').hidden=!o.histories;if(o.histories){const histories=Object.keys(o.histories).sort();for(const key of histories){const option=el('option','',key);option.value=key;h.append(option);}h.value=histories[0];}render();}
 function family(){const s=$('hardware-circuit');s.replaceChildren();H.family_results[$('hardware-family').value].forEach((row,i)=>{const o=el('option','',row.name+' · '+row.run);o.value=i;s.append(o);});circuit();}
 $('hardware-family').addEventListener('change',family);$('hardware-circuit').addEventListener('change',circuit);$('hardware-history').addEventListener('change',render);family();
 const failed=H.family_results.optical_dilation.find(r=>r.name==='optical_2bin_0p03_all_r1');
 if(!failed)throw Error('Missing declared deep failure control');
 const f=failed.observables;
 value($('hardware-failure-values'),'Raw / ideal event rate',pct(f.raw_event_probability)+' / '+pct(f.ideal_event_probability),`${f.accepted_shots} / ${f.shots} accepted shots`);
 value($('hardware-failure-values'),'Selected-data TV error',f.selected_data_z_distribution_tv.toFixed(4),'conditional distribution differs strongly');
 value($('hardware-failure-values'),'Compiled native gates',num(failed.native_two_qubit_gate_count),`${failed.logical_qubits} logical qubits; actual routed circuit`);
 for(const run of H.runs){const card=el('article','hardware-job');card.append(el('strong','',run.id),el('code','',run.job_id),el('p','',`${run.science_circuits} science + ${run.calibration_circuits} calibration circuits · ${num(run.shots_per_pub)} shots each · ${run.actual_quantum_seconds} QPU seconds`));link(card,run.workload_portal_url,'IBM Workloads ↗');link(card,localPath(run.raw_path),'Local raw counts ↗');link(card,localPath(run.plan_path),'Plan ↗');$('hardware-jobs').append(card);}
 window.HardwareUI={family,circuit,render};
})();
