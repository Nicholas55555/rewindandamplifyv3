'use strict';
/* The research tabs may only animate formulas that agree with the studies they illustrate.

   lab/research.js restates four small formulas from the follow-up studies. These tests re-read each study's
   saved results and hold the formulas to them, and then check that the numbers the tabs display (lab/data.js,
   written by lab/make_data.py) are the saved ones.

   Run:  node --test lab/test_research.cjs
*/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const E = require('./engine.js');
const R = require('./research.js');
const D = require('./data.js').research;

const ROOT = path.join(__dirname, '..');
const json = rel => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
const near = (a, b, tol = 1e-12, what = '') => assert.ok(Math.abs(a - b) <= tol, `${what} ${a} != ${b}`);

// ------------------------------------------------------------------ photons
test('Photon overlap formula reproduces all four benchmark source pairs', () => {
  const study = json('quantum_dot_bridge/results.json');
  assert.deepEqual(study.benchmark_cases.map(c => c.case), ['ideal', 'pure_dephasing', 'differential_detuning', 'combined_dephasing_and_detuning']);
  for (const c of study.benchmark_cases) {
    const rate = 1 / c.first.lifetime_s;
    const overlap = R.overlap(c.differential_angular_detuning_per_s / rate, 2 * c.first.pure_dephasing_per_s / rate);
    near(overlap, c.conditional_overlap, 1e-12, c.case);
    near(R.coincidence(overlap, c.single_photon_survival_probability), c.coincidence_probability_per_excitation_pair, 1e-15, c.case);
  }
});

test('A hidden two-state environment: pair overlap and coincidences match every stored switching probability', () => {
  const study = json('quantum_dot_bridge/results.json'), trap = study.classical_trap_pair_comparison;
  const different = R.overlap(D.photons.detuning_in_linewidths, 0);
  near(different, 0.2, 1e-12, 'photons two linewidths apart');
  assert.deepEqual(trap.map(t => t.switch_probability_between_endpoints), [0, 0.02, 0.1, 0.5]);
  for (const t of trap) {
    const overlap = R.pairOverlap(t.switch_probability_between_endpoints, different);
    near(overlap, t.conditional_overlap, 1e-12);
    near(R.coincidence(overlap, t.single_photon_survival_probability), t.coincidence_probability_per_excitation_pair, 1e-15);
    assert.deepEqual(t.each_single_photon_marginal_offset_probabilities, [0.5, 0.5], 'one photon alone looks the same in every case');
  }
});

test('The Photons tab shows the saved numbers: 0.0% against 0.8%, the IBM overlaps, the GaAs visibilities', () => {
  const P = D.photons, study = json('quantum_dot_bridge/results.json'), trap = study.classical_trap_pair_comparison;
  near(P.coincidence_per_attempt.shared, trap[0].coincidence_probability_per_excitation_pair, 0);
  near(P.coincidence_per_attempt.independent, trap[3].coincidence_probability_per_excitation_pair, 0);
  assert.equal((100 * P.coincidence_per_attempt.independent).toFixed(1), '0.8');
  assert.deepEqual([P.overlap.shared, P.overlap.independent, P.survival], [1, 0.6, 0.2]);
  const families = json('hardware_campaign/results.json').family_results.dot_frozen.filter(r => r.run === 'dots_plain_v1');
  const row = name => families.find(r => r.name === name).observables;
  near(P.on_ibm.shared.overlap, row('frozen_pair_p0').raw_swap_overlap_estimate, 0);
  near(P.on_ibm.independent.overlap, row('frozen_pair_p0.5').raw_swap_overlap_estimate, 0);
  assert.deepEqual([P.on_ibm.shared.overlap.toFixed(2), P.on_ibm.independent.overlap.toFixed(2)], ['0.81', '0.52']);
  const hom = json('quantum_dot_bridge/hom_analysis/results.json');
  assert.equal(hom.attribution.source_authors[0], 'Julian Münzberg');
  assert.deepEqual(P.gaas.map(g => g.separation_ns), [13.1, 26.2, 39.4]);
  P.gaas.forEach((g, i) => {
    near(g.visibility, hom.cases[i].primary.corrected_visibility, 0);
    assert.deepEqual(g.interval95, hom.monte_carlo.cases[i].corrected.interval95);
  });
  assert.deepEqual(P.gaas.map(g => g.visibility.toFixed(2)), ['0.80', '0.83', '0.77']);
  const fit = n => json(`qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit${n}.json`);
  near(P.dead_time.ignored, fit(0).joint_parameters.g_defect, 0); near(P.dead_time.modelled, fit(1).joint_parameters.g_defect, 0);
  near(P.dead_time.truth, fit(1).generator_parameters.g_defect, 0);
  assert.deepEqual([P.dead_time.ignored.toFixed(3), P.dead_time.modelled.toFixed(3), P.dead_time.truth], ['0.069', '0.706', 0.65]);
});

// ------------------------------------------------------------------ lasers
test('Atomic response: the closed form follows the study’s Bloch integration within 0.0005', () => {
  const study = json('laser_sensor_viability/results.json'), curve = study.response_curve, c = study.config;
  let worst = 0, checked = 0;
  curve.detuning_hz.forEach((hz, i) => {
    if (Math.abs(hz) > 10) return;
    // the stored curve includes the readout errors: P(read excited) = e01 + (1 − e01 − e10) p
    const ideal = (curve.probability[i] - c.readout_01) / (1 - c.readout_01 - c.readout_10);
    worst = Math.max(worst, Math.abs(R.atomsExcited(hz, { pulse: c.pulse_s, dark: c.dark_s, t2: c.t2_s }) - ideal)); checked++;
  });
  assert.ok(checked >= 200 && worst < 5e-4, `worst difference ${worst} over ${checked} detunings`);
  for (const row of D.lasers.atomic_on_ibm) near(R.atomsExcited(row.detuning_hz), row.model, 2e-4, `${row.detuning_hz} Hz`);
  near(R.atomsExcited(0), 0.5, 1e-12);
});

test('The Lasers tab shows the saved rates and replays stored records', () => {
  const L = D.lasers, study = json('laser_sensor_viability/followup/main/results.json');
  const traces = json('laser_sensor_viability/followup/main/example_traces.json');
  assert.deepEqual([L.config.atoms, L.config.cycles, L.config.wavelength_nm, L.step_hz, L.window_s], [64, 128, 698, 0.5, 32]);
  const ids = { nominal: 'unseen_nominal_sessions', short_coherence: 'unseen_short_coherence', shared_path: 'common_sampled_path_changes' };
  for (const [key, id] of Object.entries(ids)) {
    const saved = study.scenarios.find(s => s.id === id), shown = L.scenarios[key], trace = traces[id], e = shown.example;
    assert.equal(shown.records, 1920);
    for (const m of ['classical', 'quantum', 'classical_quantum', 'two_classical']) {
      near(shown.monitors[m].caught, saved.methods[m].detection_within_32s, 0, `${key} ${m}`);
      near(shown.monitors[m].false_alarm, saved.methods[m].false_alarm_rate, 0, `${key} ${m}`);
      assert.equal(e.first_alarm_s[m], trace.first_alarm_s[m]);
      // scores are stored relative to each monitor's own threshold, so an alarm is the first value above 1
      const first = e.scores[m].findIndex(v => v > 1);
      assert.equal(first < 0 ? -1 : e.score_times_s[0] + first, trace.first_alarm_s[m], `${key} ${m} alarm time`);
    }
    assert.deepEqual([e.onset_s, e.nuisance_onset_s], [trace.onset_cycle, trace.nuisance_onset_cycle]);
    assert.equal(e.laser_hz.length, 128); assert.equal(e.scores.classical.length, 97);
    trace.source_frequency_hz.forEach((v, i) => near(e.laser_hz[i], v, 5.1e-5));
    trace.observations.forEach((row, i) => { near(e.receiver_hz[i], row[1], 5.1e-5); near(e.atoms_hz[i], row[3], 5.1e-5); });
    trace.atomic_excited_fraction.forEach((v, i) => near(e.atoms_excited[i] / 64, v, 1e-9));
  }
  const n = L.scenarios.nominal.monitors;
  assert.deepEqual(['classical', 'quantum', 'classical_quantum', 'two_classical'].map(m => (100 * n[m].caught).toFixed(1)), ['51.4', '7.7', '58.0', '98.0']);
  assert.deepEqual(L.scenarios.nominal.example.first_alarm_s, { classical: 100, quantum: -1, classical_quantum: 85, two_classical: 74 });
  const atomic = json('hardware_campaign/results.json').family_results.atomic;
  for (const [row, name] of [[L.atomic_on_ibm[0], 'atomic_d-5_Z'], [L.atomic_on_ibm[1], 'atomic_d+0_Z'], [L.atomic_on_ibm[2], 'atomic_d+5_Z']]) {
    const saved = atomic.find(r => r.name === name);
    near(row.measured, saved.observables.raw_system_zero_probability, 0); near(row.model, saved.observables.ideal_system_zero_probability, 0);
    assert.deepEqual([row.qubits, row.two_qubit_gates, row.shots], [4, 22, 2048]);
  }
});

// ------------------------------------------------------------------ chipmaking
test('Exposure model: cell means, cell accuracy and all-cells-correct match the study for all three kinds of light', () => {
  const study = json('quantum_lithography_poc/exposure_followup/results.json').cases[1];
  assert.equal(study.setup.threshold_events, R.EXPOSURE.threshold);
  const guard = R.guardCells(R.EXPOSURE.cells);
  assert.deepEqual([guard.filter(g => g > 0).length, guard.filter(g => g < 0).length, guard.filter(g => g === 0).length], [10, 10, 12]);
  for (const key of ['noon', 'phase_cycled', 'phase_cycled_burst']) {
    const best = study.methods[key].best_threshold_accuracy;
    const means = R.cellMeans(R.exposure(key), best.sample_incident_photons / (2 * R.EXPOSURE.arm), R.EXPOSURE.cells);
    means.forEach((mean, j) => near(mean, best.cell_mean_events[j], 1e-9 * best.cell_mean_events[j], `${key} cell ${j}`));
    const quality = R.printQuality(means, study.setup.threshold_events);
    near(quality.accuracy, best.guard_cell_accuracy, 1e-10, key); near(quality.allCorrect, best.all_guard_cells_correct_probability, 1e-10, key);
    assert.equal(quality.scored, 20);
  }
  // the fine stripes appear for laser light too: what differs is the contrast
  const contrast = key => { const c = R.exposure(key); return c[2] / c[0]; };
  assert.deepEqual(['noon', 'phase_cycled', 'phase_cycled_burst'].map(k => contrast(k).toFixed(3)), ['0.433', '0.205', '0.253']);
  assert.deepEqual(['noon', 'phase_cycled', 'phase_cycled_burst'].map(k => R.exposure(k)[1]), [0, 0, 0]);
});

test('The Chipmaking tab shows the saved numbers: 95.2 / 78.3 / 83.3%, 389 qubits against 156, 50.4% wrong half-turn', () => {
  const C = D.chips, study = json('quantum_lithography_poc/exposure_followup/results.json').cases[1];
  for (const key of ['noon', 'phase_cycled', 'phase_cycled_burst']) {
    const best = study.methods[key].best_threshold_accuracy;
    near(C.methods[key].cell_accuracy, best.guard_cell_accuracy, 0); near(C.methods[key].all_correct, best.all_guard_cells_correct_probability, 0);
    near(C.methods[key].photons, best.sample_incident_photons, 0);
  }
  assert.deepEqual(['noon', 'phase_cycled', 'phase_cycled_burst'].map(k => (100 * C.methods[k].cell_accuracy).toFixed(1)), ['95.2', '78.3', '83.3']);
  assert.deepEqual(['noon', 'phase_cycled', 'phase_cycled_burst'].map(k => (C.methods[k].photons / 1e6).toFixed(2)), ['14.88', '6.81', '0.84']);
  const spatial = json('finals-lithography/full_spatial_circuit/results.json'), q = C.full_query;
  assert.deepEqual([q.qubits, q.count_qubits + q.score_qubits + q.clean_qubits, q.cells], [389, 389, 49]);
  assert.equal(q.qubits, spatial.circuits[1].qubits);
  assert.equal(q.cx_upper_bound.floor, spatial.explicit_synthesis_costs.floor.complete_one_round_generic_cx_constructive_upper_bound);
  assert.equal(q.device_qubits, json('hardware_campaign/coverage.json').confirmed_device_qubits);
  assert.ok(q.qubits > q.device_qubits && q.cx_upper_bound.floor > 3e6);
  assert.equal((100 * q.event_probability.floor).toFixed(2), '0.42');
  const phase = json('quantum_lithography_poc/phase_inspection_followup/results.json').cases[1].budgets.equal_sample_photons;
  for (const key of ['coherent', 'noon', 'hybrid']) {
    near(C.phase[key].rmse_rad, phase[key].global.rmse_full_2pi_rad, 0); near(C.phase[key].wrong_branch, phase[key].global.wrong_pi_branch_rate, 0);
  }
  assert.deepEqual([C.phase.noon.wrong_branch, C.phase.coherent.wrong_branch, C.phase.hybrid.wrong_branch], [0.504, 0, 0]);
});

test('Random exposures drawn in the browser follow the model they are drawn from', () => {
  const random = E.seeded(20261114), means = R.cellMeans(R.exposure('noon'), D.chips.methods.noon.photons / (2 * R.EXPOSURE.arm), R.EXPOSURE.cells);
  const guard = R.guardCells(R.EXPOSURE.cells), trials = 4000;
  let right = 0, scored = 0, perfect = 0, sum = 0;
  for (let t = 0; t < trials; t++) {
    let ok = 0, n = 0;
    means.forEach((mean, j) => { const count = R.poisson(mean, random); if (j === 0) sum += count; if (!guard[j]) return; n++; if ((count >= R.EXPOSURE.threshold) === (guard[j] > 0)) ok++; });
    right += ok; scored += n; if (ok === n) perfect++;
  }
  const exact = R.printQuality(means, R.EXPOSURE.threshold);
  near(sum / trials, means[0], 0.4, 'mean count of the brightest cell');
  near(right / scored, exact.accuracy, 0.006, 'cell accuracy'); near(perfect / trials, exact.allCorrect, 0.035, 'perfect exposures');
});
