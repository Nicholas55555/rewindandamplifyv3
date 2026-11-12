'use strict';
/* The Lab's JavaScript engine must agree with Qiskit, or the Lab is a cartoon.

   Every reference number below was produced by the Python package in rewindandamplify-main/qrsm_grover:
   the frozen file research-validation/original_after_click_verification.json (ideal Qiskit circuits checked against
   the exact filter), and the constants in REFERENCE, printed by lab/make_reference.py from that same package.

   Run:  node --test lab/test_engine.cjs
*/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const E = require('./engine.js');

const near = (a, b, tol = 1e-12, what = '') => assert.ok(Math.abs(a - b) <= tol, `${what} ${a} != ${b} (tolerance ${tol})`);
const frozen = JSON.parse(fs.readFileSync(path.join(__dirname, '../research-validation/original_after_click_verification.json'), 'utf8'));
const REFERENCE = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference.json'), 'utf8'));
const MODELS = { with_hidden_defect: E.makeModel(), no_hidden_defect: E.makeModel({ defect: false }) };
const VARIANTS = {
  plain: { r: 0, reflection: 'full', steered: false },
  full_steered: { r: 1, reflection: 'full', steered: true },
  local_steered: { r: 1, reflection: 'memory+last-1', steered: true },
  memory_only_steered: { r: 1, reflection: 'memory', steered: true },
};

test('The model parameters are the ones the frozen Qiskit evidence used', () => {
  const p = frozen.models.with_hidden_defect.parameters;
  assert.equal(E.DEFAULTS.theta, p.drive_theta);
  assert.equal(E.DEFAULTS.gamma, p.emission_gamma);
  assert.deepEqual([E.DEFAULTS.phi], p.defect_couplings_phi);
  assert.deepEqual([E.DEFAULTS.zeta], p.defect_rotations_zeta);
  assert.equal(MODELS.no_hidden_defect.k, 0);
  assert.equal(MODELS.with_hidden_defect.nMemory, 2);
});

test('Kraus operators equal Qiskit Operator(step) entry by entry', () => {
  for (const [id, model] of Object.entries(MODELS)) {
    const K = E.kraus(model), ref = REFERENCE.models[id].kraus;
    for (let y = 0; y < 2; y++) {
      assert.equal(K[y].d, ref[y].length);
      for (let r = 0; r < K[y].d; r++) for (let c = 0; c < K[y].d; c++) {
        near(K[y].re[r * K[y].d + c], ref[y][r][c][0], 1e-13, `${id} K${y}[${r},${c}].re`);
        near(K[y].im[r * K[y].d + c], ref[y][r][c][1], 1e-13, `${id} K${y}[${r},${c}].im`);
      }
    }
  }
});

test('One step is a valid measurement: K0†K0 + K1†K1 = I', () => {
  for (const model of Object.values(MODELS)) for (const gamma of [null, 0.05, 1]) {
    const K = E.kraus(model, gamma), d = K[0].d;
    for (let a = 0; a < d; a++) for (let b = 0; b < d; b++) {
      let re = 0, im = 0;
      for (const k of K) for (let r = 0; r < d; r++) {
        // conj(k[r,a]) * k[r,b]
        re += k.re[r * d + a] * k.re[r * d + b] + k.im[r * d + a] * k.im[r * d + b];
        im += k.re[r * d + a] * k.im[r * d + b] - k.im[r * d + a] * k.re[r * d + b];
      }
      near(re, a === b ? 1 : 0, 1e-13); near(im, 0, 1e-13);
    }
  }
});

test('History probabilities match the exact filter for every 3-step and 6-step record', () => {
  for (const [id, model] of Object.entries(MODELS)) for (const T of [3, 6]) {
    const probs = E.historyProbabilities(model, T), ref = REFERENCE.models[id]['history_probabilities_T' + T];
    assert.equal(probs.length, ref.length);
    let total = 0;
    probs.forEach((p, y) => { near(p, ref[y], 1e-13, `${id} T=${T} y=${y}`); total += p; });
    near(total, 1, 1e-12);
  }
});

test('The headline answers: 4.67% with the defect, 10.10% without', () => {
  for (const [id, model] of Object.entries(MODELS)) {
    const got = E.afterClick(model, 3, 3), want = frozen.models[id];
    near(got.pClick, want.original_event_probability, 1e-13, `${id} P(click at 3)`);
    got.conditional.forEach((c, j) => near(c, want.exact_conditional_probabilities[j], 1e-13, `${id} lag ${j + 1}`));
    got.plain.forEach((c, j) => near(c, REFERENCE.models[id].plain_click_rates[j], 1e-13));
  }
  assert.equal((100 * E.afterClick(MODELS.with_hidden_defect, 3, 3).conditional[2]).toFixed(2), '4.67');
  assert.equal((100 * E.afterClick(MODELS.no_hidden_defect, 3, 3).conditional[2]).toFixed(2), '10.10');
  assert.equal((100 * E.afterClick(MODELS.with_hidden_defect, 3, 3).pClick).toFixed(2), '3.95');
});

test('With no defect a click wipes the memory, so the future repeats the start of the run', () => {
  const model = MODELS.no_hidden_defect, T = 3, probs = E.historyProbabilities(model, T);
  const fresh = [1, 2, 3].map(t => probs.reduce((s, p, y) => s + (((y >> (t - 1)) & 1) ? p : 0), 0));
  E.afterClick(model, 3, 3).conditional.forEach((c, j) => near(c, fresh[j], 1e-13));
});

test('The whole query circuit matches the frozen ideal Qiskit runs, for both models and all four builds', () => {
  for (const [id, model] of Object.entries(MODELS)) for (const [name, v] of Object.entries(VARIANTS)) {
    const want = frozen.models[id].ideal_circuits[name];
    const steer = v.steered ? E.steerFor(model, 3) : null;
    if (v.steered) near(steer, want.emission_override_at_step3, 1e-13, `${id} ${name} steer`);
    assert.equal(v.r, want.r); assert.equal(v.reflection, want.reflection);
    const got = E.loopQuery(model, 3, 3, { r: v.r, reflection: v.reflection, steer });
    near(got.eventProbability, want.event_probability, 1e-12, `${id} ${name} event probability`);
    got.conditional.forEach((c, j) => near(c, want.conditional_probabilities[j], 1e-12, `${id} ${name} lag ${j + 1}`));
  }
});

test('Full reflection follows sin²((2r+1)θ) and never changes the conditional answer', () => {
  const model = MODELS.with_hidden_defect, T = 3, p = E.clickProbability(model, T);
  for (let r = 0; r <= 4; r++) {
    const got = E.amplifiedHistory(model, T, { r, reflection: 'full' });
    near(got.hit, E.successProbability(p, r), 1e-12, `r=${r}`);
    near(got.tv, 0, 1e-12, `conditional error at r=${r}`);
  }
});

test('Steering sets p to 1/4 when it can, and one full iteration then succeeds with certainty', () => {
  const model = MODELS.no_hidden_defect, steer = E.steerFor(model, 3);
  near(E.amplifiedHistory(model, 3, { r: 0, steer }).hit, 0.25, 1e-12);
  near(E.amplifiedHistory(model, 3, { r: 1, steer }).hit, 1, 1e-12);
  // with the defect, the clicked step cannot emit harder than certainty, so steering saturates below 1/4
  assert.equal(E.steerFor(MODELS.with_hidden_defect, 3), 1);
  near(E.amplifiedHistory(MODELS.with_hidden_defect, 3, { r: 0, steer: 1 }).hit, REFERENCE.models.with_hidden_defect.steered_event_probability, 1e-12);
});

test('Steering reweights only: the conditional distribution of marked histories is untouched', () => {
  for (const model of Object.values(MODELS)) near(E.amplifiedHistory(model, 3, { r: 0, steer: E.steerFor(model, 3) }).tv, 0, 1e-12);
});

test('Local reflection: matches fastsim hit rates and conditional error', () => {
  for (const [id, model] of Object.entries(MODELS)) for (const kind of ['full', 'memory+last-1', 'memory']) {
    const got = E.amplifiedHistory(model, 3, { r: 1, reflection: kind, steer: E.steerFor(model, 3) });
    const want = REFERENCE.models[id].steered_r1[kind];
    near(got.hit, want.hit, 1e-12, `${id} ${kind} hit`);
    near(got.tv, want.tv, 1e-12, `${id} ${kind} tv`);
  }
});

test('Rewinding undoes the machine exactly: A†A = I', () => {
  for (const model of Object.values(MODELS)) {
    const ops = E.purifiedOps(model, 4), s = E.run(E.zeroState(model.nMemory + 4), ops);
    E.run(s, ops, true);
    near(s.re[0], 1, 1e-12);
    near(E.probabilityWhere(s, i => i !== 0), 0, 1e-12);
  }
});

test('The stage snapshots the animation draws are consistent with the final result', () => {
  const model = MODELS.with_hidden_defect, steer = E.steerFor(model, 3);
  const got = E.amplifiedHistory(model, 3, { r: 1, reflection: 'full', steer, stages: true });
  assert.deepEqual(got.stages.map(s => s.label), ['prepare', 'mark', 'rewind', 'reflect', 'replay']);
  const [prepare, mark, rewind, , replay] = got.stages;
  near(prepare.hit, mark.hit, 1e-12);                         // marking changes signs, not probabilities
  near(rewind.blank, (1 - 2 * prepare.hit) ** 2, 1e-12);      // what rewinds to blank is |<0|A†S_f A|0>|²
  near(replay.hit, got.hit, 1e-12);
  for (let y = 0; y < 8; y++) {
    const sign = (y >> 2) & 1 ? -1 : 1;                       // only histories with a click at step 3 flip
    near(mark.signed[y], sign * prepare.signed[y], 1e-12);
  }
});

test('Single runs sampled in the browser follow the exact click statistics', () => {
  for (const [id, model] of Object.entries(MODELS)) {
    const random = E.seeded(20261114), K = E.kraus(model), N = 200000, T = 6;
    const exact = E.afterClick(model, 3, 3);
    let kept = 0, later = 0;
    for (let i = 0; i < N; i++) {
      const bits = E.sampleRun(model, T, random, K).bits;
      if (bits[2]) { kept++; later += bits[5]; }
    }
    const sd = Math.sqrt(exact.pClick * (1 - exact.pClick) / N);
    assert.ok(Math.abs(kept / N - exact.pClick) < 4.5 * sd, `${id} click rate ${kept / N} vs ${exact.pClick}`);
    const c = exact.conditional[2], sdc = Math.sqrt(c * (1 - c) / kept);
    assert.ok(Math.abs(later / kept - c) < 4.5 * sdc, `${id} conditional ${later / kept} vs ${c}`);
  }
});

test('Populations shown in the animation are probabilities, and a click empties the emitter', () => {
  const model = MODELS.with_hidden_defect, K = E.kraus(model);
  let psi = E.groundMemory(model);
  const always = () => 0, never = () => 1;
  for (let t = 0; t < 5; t++) {
    const pre = E.preEmission(model, psi);
    for (const v of pre.afterDrive.concat(pre.afterExchange)) assert.ok(v >= -1e-12 && v <= 1 + 1e-12);
    const click = E.sampleStep(model, K, psi, always);
    assert.equal(click.y, 1);
    near(E.populations(model, click.psi)[0], 0, 1e-12);       // the photon carried the emitter's excitation away
    psi = E.sampleStep(model, K, psi, never).psi;
    near(E.norm2(psi), 1, 1e-12);
  }
});

test('Guards', () => {
  assert.throws(() => E.makeModel({ gamma: 1.5 }));
  assert.throws(() => E.reflectionQubits(MODELS.with_hidden_defect, 3, 'nonsense'));
  assert.throws(() => E.run(E.zeroState(2), [['swap', 0, 1]]));
  assert.equal(E.historyToString(4, 3), '001');
});
