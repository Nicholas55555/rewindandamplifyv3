'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const crypto=require('node:crypto');
const M=require('./model.js');
const near=(a,b,t=1e-12)=>assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);
test('Amplification matches independently saved Qiskit statevector at r=1',()=>{
 const source=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/two_bin_double.json')));
 near(M.amplifyProbability(source.event.retained_model_probability,1),source.event.qiskit_amplified_probability);
 near(M.amplifyProbability(source.event.retained_model_probability,0),source.event.retained_model_probability);
});
test('Amplification boundaries, overshoot and parameter guards',()=>{
 for(let r=0;r<30;r++){near(M.amplifyProbability(0,r),0);near(M.amplifyProbability(1,r),1);}
 assert.ok(M.amplifyProbability(.1,3)<M.amplifyProbability(.1,2));
 assert.throws(()=>M.amplifyProbability(-.01,1));assert.throws(()=>M.amplifyProbability(.1,1.5));
});
test('Ramsey response obeys asymmetric readout and decoherence',()=>{
 near(M.ramseyProbability(0,.02,.2),.49);
 near(M.ramseyProbability(12.5,.02,1e15),.96);
 near(M.ramseyProbability(-12.5,.02,1e15),.02);
 near(M.ramseyProbability(10,0,.2),.49);
 near(M.ramseyProbability(5,.02,.2)+M.ramseyProbability(-5,.02,.2),.98);
 assert.ok(Math.abs(M.ramseyProbability(5,.02,.01)-.49)<Math.abs(M.ramseyProbability(5,.02,.2)-.49));
});
test('Frozen app rates and trace values match research evidence exactly',()=>{
 const context={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'data.js'),'utf8'),context);
 const d=context.window.DEMO_DATA;
 for(const [original,copy]of [['results.json','sensor_results.json'],['example_traces.json','example_traces.json']]){
  const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
  assert.equal(hash(fs.readFileSync(path.join(__dirname,'evidence',copy))),d.source_sha256[original]);
  const canonical=path.join(__dirname,'../laser_sensor_viability',original);
  if(fs.existsSync(canonical))assert.equal(hash(fs.readFileSync(canonical)),d.source_sha256[original]);
 }
 const r=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/sensor_results.json')));
 const t=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/example_traces.json')));
 assert.equal(d.scenarios.length,r.scenarios.length);assert.ok(d.scenarios.length>=8);
 assert.ok(d.methods.some(m=>m.id==='two_classical'));
 for(const c of d.scenarios){const src=r.scenarios.find(s=>s.id===c.id);for(const m of d.methods){near(c.methods[m.id].detection_rate,src.methods[m.id].detection_rate);near(c.methods[m.id].false_alarm_rate,src.methods[m.id].false_alarm_rate);}
 assert.equal(JSON.stringify(c.trace),JSON.stringify(t.scenarios[c.id]));}
});
test('Original after-click explorer retains the verified query and distinct long-query hardware counts',()=>{
 const context={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'data.js'),'utf8'),context);
 const data=context.window.DEMO_DATA;
 const bytes=fs.readFileSync(path.join(__dirname,'evidence/original_after_click_verification.json'));
 const source=JSON.parse(bytes);
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),data.original_sha256);
 assert.equal(JSON.stringify(data.original),JSON.stringify(source));
 const canonical=path.join(__dirname,'../research-validation/original_after_click_verification.json');
 if(fs.existsSync(canonical))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(canonical)).digest('hex'),data.original_sha256);
 assert.equal(data.original.event.selected_step,3);
 assert.equal(JSON.stringify(data.original.event.future_steps),'[4,5,6]');
 const job=data.original.hardware_jobs[0];
 const plain=job.rows.find(r=>r.model_id==='with_hidden_defect'&&r.variant==='plain');
 const amplified=job.rows.find(r=>r.model_id==='with_hidden_defect'&&r.variant==='local_steered');
 assert.equal(plain.source_meta.kind,'loop');assert.equal(amplified.source_meta.tau,3);
 assert.equal(plain.raw_selected_count,290);assert.equal(amplified.raw_selected_count,3354);
 near(amplified.raw_conditional_probabilities[2],amplified.raw_future_joint_counts[2]/amplified.raw_selected_count);
 const modeled=data.original.models.no_hidden_defect;
 assert.ok(modeled.ideal_circuits.memory_only_steered.max_conditional_error>.09);
 assert.ok(modeled.ideal_circuits.full_steered.max_conditional_error<1e-12);
});

function research(){const context={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'research-data.js'),'utf8'),context);return context.window.RESEARCH_DATA;}
test('Current research has byte-exact evidence copies and canonical hashes, separate from the old sensor',()=>{
 const d=research(),hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
 assert.equal(Object.keys(d.sources).length,14);
 for(const [key,meta] of Object.entries(d.provenance)){
  const bytes=fs.readFileSync(path.join(__dirname,meta.local));assert.equal(hash(bytes),meta.sha256);
  assert.equal(JSON.stringify(d.sources[key]),JSON.stringify(JSON.parse(bytes)));
  const canonical=path.join(__dirname,'..',meta.canonical);if(fs.existsSync(canonical))assert.equal(hash(fs.readFileSync(canonical)),meta.sha256);
 }
 assert.equal(d.sources.frequency.mode,'main');assert.ok(d.sources.frequency.protocol.detector.includes('onset is never supplied'));
 const old=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/sensor_results.json')));
 assert.notEqual(JSON.stringify(d.sources.frequency.scenarios),JSON.stringify(old.scenarios));
});
test('Quantum-dot case values preserve imposed brightness and distinct overlap physics',()=>{
 const d=research().sources.dot;assert.equal(d.benchmark_cases.length,4);
 for(const [i,c] of d.benchmark_cases.entries()){
  near(c.conditional_overlap,[1,.5,.2,.25][i]);near(c.single_photon_survival_probability,.2);assert.equal(c.ideal_g2_zero_imposed,0);
  near(c.coincidence_probability_per_excitation_pair,.2**2*(1-c.conditional_overlap)/2);
  const gamma=1/c.first.lifetime_s,a=gamma+2*c.first.pure_dephasing_per_s;
  near(c.conditional_overlap,gamma*a/(a*a+c.differential_angular_detuning_per_s**2));
 }
 assert.ok(d.assumptions.some(s=>s.includes('not calibrated')));assert.ok(d.provenance.all_quadrature_checks_passed);
});
test('Quantum-dot trap correlations keep equal marginals and loss charges pair attempts',()=>{
 const d=research().sources.dot;
 d.classical_trap_pair_comparison.forEach((c,i)=>{
  near(c.conditional_overlap,[1,.984,.92,.6][i]);
  assert.equal(JSON.stringify(c.each_single_photon_marginal_offset_probabilities),'[0.5,0.5]');
  for(const row of c.joint_endpoint_probabilities)near(row[0]+row[1],.5);
 });
 for(const c of d.collection_loss_sweep){near(c.conditional_overlap,.5);near(c.both_photons_survive_probability,c.single_photon_survival_probability**2);}
 const loss=eta=>d.collection_loss_sweep.find(c=>c.single_photon_survival_probability===eta);
 near(loss(.2).expected_excitation_pairs_per_surviving_pair/loss(.8).expected_excitation_pairs_per_surviving_pair,16);
 assert.equal(loss(0).expected_excitation_pairs_per_surviving_pair,null);
});
test('Six external HOM histograms retain every raw bin, source checksum and separate attribution',()=>{
 const d=research(),r=d.sources.hom_reference;
 assert.equal(r.license.id,'CC-BY-4.0');assert.equal(r.compatibility.team_data,false);assert.equal(r.compatibility.team_fit,false);
 assert.equal(d.hom_histograms.length,6);assert.equal(r.files.length,6);
 for(const h of d.hom_histograms){const meta=r.files.find(f=>f.path===h.file),bytes=fs.readFileSync(path.join(__dirname,h.local));
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),h.sha256);assert.equal(h.sha256,meta.sha256);
  const lines=bytes.toString('utf8').trim().split(/\r?\n/);assert.equal(lines.shift(),'Time (ps),Counts');assert.equal(lines.length,5000);
  lines.forEach((line,i)=>{const [t,c]=line.split(',').map(Number);assert.equal(h.time_ps[i],t);assert.equal(h.counts[i],c);});
  assert.equal(h.counts.reduce((a,b)=>a+b,0),meta.count_sum);assert.equal(meta.duration_seconds,null);
 }
 assert.equal(JSON.stringify(r.paper_reported_corrected_visibility.map(c=>c.value)),'[0.803,0.826,0.774]');
 assert.notEqual(r.paper_reported_corrected_visibility[0].value,d.sources.dot.benchmark_cases[0].conditional_overlap);
});
test('HOM reanalysis remains tied to the raw data and separates conditional intervals from protocol sensitivity',()=>{
 const d=research(),a=d.sources.hom_analysis;assert.equal(a.schema,'hom-area-analysis-v1');
 assert.equal(a.reference_manifest_sha256,d.provenance.hom_reference.sha256);
 assert.match(a.scope,/not exact author-pipeline reproduction/);assert.match(a.uncertainty_scope,/excludes normalization/);
 for(const h of d.hom_histograms)assert.equal(a.raw_sha256[h.file],h.sha256);
 assert.equal(a.cases.length,3);
 for(const c of a.cases){
  assert.equal(c.sensitivity.length,70);assert.equal(c.paper_reported.independent_comparison,false);
  const p=c.primary;near(p.raw_visibility,1-p.co_central_reference_ratio/p.cross_central_reference_ratio);
  const r=a.configuration.reflectivity_mean_sd[0],t=1-r,g=a.configuration.g2_mean_sd[0];
  near(p.corrected_visibility,(r*r+t*t)/(2*r*t)*(p.raw_visibility+g)/(1-g));
  assert.ok(p.corrected_interval95[0]<p.corrected_visibility&&p.corrected_interval95[1]>p.corrected_visibility);
  near(Math.min(...c.sensitivity.map(v=>v.corrected_visibility)),c.sensitivity_range_all_declared_variants[0]);
  near(Math.max(...c.sensitivity.map(v=>v.corrected_visibility)),c.sensitivity_range_all_declared_variants[1]);
 }
});
test('Unknown-onset data preserve record denominators and the independent coherent comparator',()=>{
 const f=research().sources.frequency;assert.equal(f.scenarios.length,6);
 for(const c of f.scenarios)for(const m of Object.values(c.methods)){
  near(m.detection_within_32s,m.counts.detection_within_32s/c.records_per_class);
  near(m.false_alarm_rate,m.counts.false_alarm_rate/c.records_per_class);
 }
 const c=f.scenarios[0];assert.equal(c.records_per_class,1920);
 near(c.methods.classical.detection_within_32s,986/1920);near(c.methods.classical_quantum.detection_within_32s,1114/1920);
 near(c.methods.two_classical.detection_within_32s,1881/1920);
 assert.equal(f.protocol.record_cycles,128);assert.equal(f.protocol.restricted_delay_s,32);
});
test('Drive results retain all 13 cases and the post-holdout prior-only control',()=>{
 const d=research().sources;assert.equal(Object.keys(d.drive.cases).length,13);
 assert.equal(d.prior.main_results_sha256,research().provenance.drive.sha256);assert.match(d.prior.scope,/Post-holdout descriptive/);
 for(const [id,c] of Object.entries(d.drive.cases))near(c.physical_fraction_rmse.value,d.prior.cases[id].observation_based_rmse.value);
 const step=d.drive.cases.source_step_20pct.methods.physical_history;
 near(step.detection_within32.value,19/512);assert.equal(step.detection_within32.records,512);
 const tele=d.drive.cases.source_telegraph_20pct.methods.physical_history;
 assert.equal(tele.detection_within32.records+tele.no_event_records+tele.late_onset_records,512);
 assert.equal(tele.detection_within32.records,480);
 for(const id of ['source_telegraph_20pct','source_step_10pct','source_telegraph_fast','source_step_with_efficiency_loss'])assert.ok(d.prior.cases[id].observation_based_rmse.value>d.prior.cases[id].prior_only_rmse.value);
 assert.equal(d.drive.config.steps,96);
});
test('Inspection uses the global task, charged budgets, and explicit construction costs',()=>{
 const d=research().sources,p=d.phase.cases.find(c=>c.id==='high_efficiency').budgets.equal_sample_photons;
 for(const m of Object.values(p))assert.equal(m.resources.sample_incident_mean_photons_before_object,20000);
 assert.ok(p.noon.global.rmse_full_2pi_rad>2);assert.ok(p.noon.global.rmse_modulo_pi_rad<.01);
 assert.ok(p.hybrid.global.wrong_pi_branch_wilson95[1]>0);
 const clean=d.spatial.circuits.filter(c=>c.style==='clean');assert.equal(clean.length,2);
 for(const c of clean){assert.equal(c.qubits,389);assert.equal(c.qpy_round_trip,'passed');}
 assert.equal(d.spatial.explicit_synthesis_costs.ceil.complete_one_round_generic_cx_constructive_upper_bound,2874028);
 assert.equal(d.spatial.explicit_synthesis_costs.floor.complete_one_round_generic_cx_constructive_upper_bound,3382108);
 assert.equal(d.inference_ignored.test_sha256,d.inference_aware.test_sha256);
});


test('Implemented joint HOM study retains passive negative and main denominators',()=>{
 const r=research().sources.joint_hom;
 const passive=r.regimes.find(x=>x.name==='passive');for(const c of passive.cases)assert.equal(c.flagged_records,0);
 const controlled=r.regimes.find(x=>x.name==='controlled');
 for(const c of controlled.cases){near(c.flag_rate,c.flagged_records/c.records);assert.equal(c.pair_trials_per_record,64);assert.equal(c.records,2000);}
 near(controlled.cases.find(c=>c.name==='coherent_nominal').flag_rate,112/2000);
 near(controlled.cases.find(c=>c.name==='classical_nominal').flag_rate,90/2000);
});
test('Selected dot design retains full power curve, reset resources, nuisances and strong HMM control',()=>{
 const d=research().sources,r=d.dot_design_validation;
 assert.equal(r.provenance.design_results_sha256,research().provenance.dot_design.sha256);
 assert.equal(r.power_trials.length,6);
 for(const t of r.power_trials){assert.equal(t.attempted_pairs,4*t.independent_blocks);assert.equal(t.source_excitations,8*t.independent_blocks);for(const c of t.cases)near(c.flag_rate,c.flags/c.records);}
 const largest=r.power_trials.at(-1);near(largest.cases.find(c=>c.name==='classical_loss_shift').flag_rate,.72);
 near(largest.cases.find(c=>c.name==='classical_mode_mismatch').flag_rate,.5325);
 const h=r.prediction_scores.hmm_8.paired_gain_vs_calibrated_physical;assert.ok(h.approximate_interval95[0]<0&&h.approximate_interval95[1]>0);
 for(const fit of r.classical_hmms){assert.equal(fit.starts,10);assert.ok(fit.all_start_iterations.every(n=>n===200));}
 near(d.dot_design.selected.information.sufficient_independent_blocks_alpha05_power80,1911);
});
test('Current IBM campaign retains immutable raw hashes, shots and conditional-answer failures',()=>{
 const h=research().sources.hardware;assert.equal(h.status,'complete');assert.equal(h.jobs,10);assert.equal(new Set(h.runs.map(r=>r.job_id)).size,h.jobs);
 assert.equal(h.total_shots,h.runs.reduce((sum,r)=>sum+r.total_shots,0));near(h.actual_campaign_quantum_seconds,h.runs.reduce((sum,r)=>sum+r.actual_quantum_seconds,0));
 for(const r of h.runs)assert.equal(r.workload_portal_url,'https://quantum.cloud.ibm.com/workloads');
 for(const [rel,expected]of Object.entries(h.input_sha256)){const local=path.join(__dirname,'evidence/hardware',rel.replace(/^hardware_campaign\//,''));assert.equal(crypto.createHash('sha256').update(fs.readFileSync(local)).digest('hex'),expected);}
 for(const row of [h.headline_original.local,h.headline_original.full])near(row.probability,row.accepted/row.shots);
 assert.equal(h.headline_original.local.accepted,6300);assert.equal(h.headline_original.full.accepted,5674);
 const failure=h.family_results.optical_dilation.find(r=>r.name==='optical_2bin_0p03_all_r1');near(failure.observables.raw_event_probability,8/512);assert.ok(failure.observables.selected_data_z_distribution_tv>.75);
 for(const row of h.family_results.optical_dilation.filter(r=>r.observables.accepted_shots===0))assert.equal(row.observables.selected_data_z_distribution_tv,null);
 assert.ok(h.family_results.dot_selected_four_pair.every(r=>Array.isArray(r.reference_marginal_qubits)));
});
