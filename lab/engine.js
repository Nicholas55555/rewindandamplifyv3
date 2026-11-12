/* Rewind & Amplify — exact QRSM engine for the browser and Node.

   A gate-for-gate JavaScript port of the Qiskit package in rewindandamplify-main/qrsm_grover
   (model.py, amplify.py, fastsim.py, queries.py). It builds the same circuits from the same gates and
   simulates them as a statevector, so every number the Lab shows is computed, not stored.

   Conventions match Qiskit: qubit 0 is the least significant bit. Qubit order is
   (emitter, defects..., light_1 ... light_T), and a history integer uses bit t for the click at step t + 1.

   lab/test_engine.cjs checks this file against the frozen Qiskit results in
   research-validation/original_after_click_verification.json to 1e-12.
*/
(function (root, factory) {
  'use strict';
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.QRSMEngine = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // The numbers from the hidden-defect project: QRSM() in qrsm_grover/model.py.
  const DEFAULTS = Object.freeze({ theta: 0.6, gamma: 0.2, phi: 0.45, zeta: 0.3 });

  /** A model: an emitter with phi.length hidden defects. `defect: false` gives the emitter-only machine. */
  function makeModel(options) {
    const o = Object.assign({ defect: true }, DEFAULTS, options || {});
    const list = v => (Array.isArray(v) ? v.slice() : [v]);
    const phi = o.defect ? list(o.phi) : [];
    const zeta = o.defect ? list(o.zeta) : [];
    if (phi.length !== zeta.length) throw new RangeError('phi and zeta need one entry per defect');
    if (!(o.gamma >= 0 && o.gamma <= 1)) throw new RangeError('gamma is a probability');
    return Object.freeze({ theta: +o.theta, gamma: +o.gamma, phi: Object.freeze(phi), zeta: Object.freeze(zeta),
                           k: phi.length, nMemory: 1 + phi.length });
  }

  // ------------------------------------------------------------------ statevector

  function zeroState(n) {
    if (n > 20) throw new RangeError('this simulator is for small circuits');
    const re = new Float64Array(1 << n), im = new Float64Array(1 << n);
    re[0] = 1;
    return { n, re, im };
  }

  function cloneState(s) {
    return { n: s.n, re: Float64Array.from(s.re), im: Float64Array.from(s.im) };
  }

  /** Apply the 2x2 matrix [[a, b], [c, d]] to qubit q, given as [a.re, a.im, b.re, b.im, c.re, c.im, d.re, d.im].
      With `control` set, only where that qubit is 1. */
  function apply1(s, q, m, control) {
    const re = s.re, im = s.im, size = re.length, bit = 1 << q;
    const cbit = control === undefined || control === null ? 0 : 1 << control;
    for (let i = 0; i < size; i++) {
      if (i & bit) continue;
      if (cbit && !(i & cbit)) continue;
      const j = i | bit;
      const ar = re[i], ai = im[i], br = re[j], bi = im[j];
      re[i] = m[0] * ar - m[1] * ai + m[2] * br - m[3] * bi;
      im[i] = m[0] * ai + m[1] * ar + m[2] * bi + m[3] * br;
      re[j] = m[4] * ar - m[5] * ai + m[6] * br - m[7] * bi;
      im[j] = m[4] * ai + m[5] * ar + m[6] * bi + m[7] * br;
    }
  }

  // Qiskit's definitions: RY(t) = [[cos t/2, -sin t/2], [sin t/2, cos t/2]], RZ(l) = diag(e^{-il/2}, e^{+il/2}).
  const ryMatrix = t => { const c = Math.cos(t / 2), s = Math.sin(t / 2); return [c, 0, -s, 0, s, 0, c, 0]; };
  const rzMatrix = l => { const c = Math.cos(l / 2), s = Math.sin(l / 2); return [c, -s, 0, 0, 0, 0, c, s]; };
  const X = [0, 0, 1, 0, 1, 0, 0, 0];

  /** Run a list of gates. Each is ['ry', q, angle], ['rz', q, angle], ['cx', control, target] or
      ['cry', control, target, angle]. With `inverse`, run the adjoint: reversed order, negated angles. */
  function run(s, ops, inverse) {
    const count = ops.length;
    for (let i = 0; i < count; i++) {
      const op = inverse ? ops[count - 1 - i] : ops[i];
      const sign = inverse ? -1 : 1;
      switch (op[0]) {
        case 'ry': apply1(s, op[1], ryMatrix(sign * op[2])); break;
        case 'rz': apply1(s, op[1], rzMatrix(sign * op[2])); break;
        case 'cx': apply1(s, op[2], X, op[1]); break;
        case 'cry': apply1(s, op[2], ryMatrix(sign * op[3]), op[1]); break;
        default: throw new Error('unknown gate ' + op[0]);
      }
    }
    return s;
  }

  /** Flip the sign of every basis state where `bit` is 1: a Z gate, the oracle for "a click at this step". */
  function flipWhereOne(s, q) {
    const re = s.re, im = s.im, bit = 1 << q;
    for (let i = 0; i < re.length; i++) if (i & bit) { re[i] = -re[i]; im[i] = -im[i]; }
  }

  /** Flip the sign of every basis state where all the watched qubits are 0: the zero reflection S_0. */
  function flipWhereAllZero(s, qubits) {
    let mask = 0;
    for (const q of qubits) mask |= 1 << q;
    const re = s.re, im = s.im;
    for (let i = 0; i < re.length; i++) if (!(i & mask)) { re[i] = -re[i]; im[i] = -im[i]; }
  }

  function probabilityWhere(s, test) {
    let total = 0;
    for (let i = 0; i < s.re.length; i++) if (test(i)) total += s.re[i] * s.re[i] + s.im[i] * s.im[i];
    return total;
  }

  // ------------------------------------------------------------------ the machine

  /** One step's gates in the project's order: drive, detune, exchange, emit. Emitter is qubit 0, defects 1..k. */
  function stepOps(model, light, theta, gamma) {
    const ops = [['ry', 0, theta === undefined || theta === null ? model.theta : theta]];
    for (let d = 0; d < model.k; d++) ops.push(['rz', 1 + d, model.zeta[d]]);
    for (let d = 0; d < model.k; d++) {
      // exchange(angle, src=defect, dst=emitter): a real Givens rotation that swaps one excitation
      ops.push(['cx', 0, 1 + d], ['cry', 1 + d, 0, 2 * model.phi[d]], ['cx', 0, 1 + d]);
    }
    const g = gamma === undefined || gamma === null ? model.gamma : gamma;
    const alpha = Math.asin(Math.sqrt(g));
    // emission into a light known to start in |0>
    ops.push(['cry', 0, light, 2 * alpha], ['cx', light, 0]);
    return ops;
  }

  /** The reversible machine A as a gate list: T steps, a fresh light for each, nothing measured. */
  function purifiedOps(model, T, gammas, firstLight) {
    const start = firstLight === undefined ? model.nMemory : firstLight;
    let ops = [];
    for (let t = 0; t < T; t++) ops = ops.concat(stepOps(model, start + t, null, gammas ? gammas[t] : null));
    return ops;
  }

  // ------------------------------------------------------------------ the exact model (Kraus form)

  /** K_0 and K_1: what one step does to the memory given no click, or a click. Row-major d x d complex. */
  function kraus(model, gamma) {
    const n = model.nMemory, d = 1 << n, ops = stepOps(model, n, null, gamma);
    const K = [0, 1].map(() => ({ d, re: new Float64Array(d * d), im: new Float64Array(d * d) }));
    for (let input = 0; input < d; input++) {
      const s = { n: n + 1, re: new Float64Array(2 * d), im: new Float64Array(2 * d) };
      s.re[input] = 1;
      run(s, ops);
      for (let y = 0; y < 2; y++) for (let out = 0; out < d; out++) {
        K[y].re[out * d + input] = s.re[y * d + out];
        K[y].im[out * d + input] = s.im[y * d + out];
      }
    }
    return K;
  }

  function matVec(K, psi) {
    const d = K.d, re = new Float64Array(d), im = new Float64Array(d);
    for (let r = 0; r < d; r++) {
      let xr = 0, xi = 0;
      for (let c = 0; c < d; c++) {
        const kr = K.re[r * d + c], ki = K.im[r * d + c];
        xr += kr * psi.re[c] - ki * psi.im[c];
        xi += kr * psi.im[c] + ki * psi.re[c];
      }
      re[r] = xr; im[r] = xi;
    }
    return { re, im };
  }

  const norm2 = v => { let t = 0; for (let i = 0; i < v.re.length; i++) t += v.re[i] * v.re[i] + v.im[i] * v.im[i]; return t; };

  function groundMemory(model) {
    const d = 1 << model.nMemory, psi = { re: new Float64Array(d), im: new Float64Array(d) };
    psi.re[0] = 1;
    return psi;
  }

  /** P(every history) by brute force: 2**T rows. Index y has bit t set for a click at step t + 1. */
  function historyProbabilities(model, T, gammas) {
    let branches = [groundMemory(model)];
    for (let t = 0; t < T; t++) {
      const K = kraus(model, gammas ? gammas[t] : null);
      branches = branches.map(b => matVec(K[0], b)).concat(branches.map(b => matVec(K[1], b)));
    }
    return Float64Array.from(branches, norm2);
  }

  /** The chance each memory qubit is excited in a pure memory state: what the animation shows as glow. */
  function populations(model, psi) {
    const out = new Array(model.nMemory).fill(0);
    for (let i = 0; i < psi.re.length; i++) {
      const w = psi.re[i] * psi.re[i] + psi.im[i] * psi.im[i];
      for (let q = 0; q < model.nMemory; q++) if ((i >> q) & 1) out[q] += w;
    }
    return out;
  }

  /** One measured step of a single run. Returns the click, its probability and the conditioned memory. */
  function sampleStep(model, K, psi, random) {
    const clicked = matVec(K[1], psi), p1 = norm2(clicked);
    const y = random() < p1 ? 1 : 0;
    const next = y ? clicked : matVec(K[0], psi);
    const scale = 1 / Math.sqrt(norm2(next));
    for (let i = 0; i < next.re.length; i++) { next.re[i] *= scale; next.im[i] *= scale; }
    return { y, pClick: p1, psi: next };
  }

  /** The memory just before emission in one step: after drive, detune and exchange. For the animation only. */
  function preEmission(model, psi) {
    const n = model.nMemory, s = { n, re: Float64Array.from(psi.re), im: Float64Array.from(psi.im) };
    const ops = stepOps(model, n).slice(0, -2);
    const afterDrive = { n, re: Float64Array.from(psi.re), im: Float64Array.from(psi.im) };
    run(afterDrive, ops.slice(0, 1));
    run(s, ops);
    return { afterDrive: populations(model, afterDrive), afterExchange: populations(model, s) };
  }

  /** A whole run of T steps. Returns the click bits and the memory populations after each step. */
  function sampleRun(model, T, random, K) {
    const ks = K || kraus(model);
    let psi = groundMemory(model);
    const bits = [], pops = [];
    for (let t = 0; t < T; t++) {
      const r = sampleStep(model, ks, psi, random);
      bits.push(r.y); psi = r.psi; pops.push(populations(model, psi));
    }
    return { bits, populations: pops };
  }

  /** The exact answers after a click at step t0: click rates, conditional click rates and g2, for lags 1..tau. */
  function afterClick(model, t0, tau) {
    const T = t0 + tau, probs = historyProbabilities(model, T);
    const at = (y, t) => ((y >> (t - 1)) & 1) === 1;
    let pClick = 0;
    const plain = new Array(tau).fill(0), joint = new Array(tau).fill(0);
    for (let y = 0; y < probs.length; y++) {
      if (at(y, t0)) pClick += probs[y];
      for (let j = 1; j <= tau; j++) {
        if (at(y, t0 + j)) { plain[j - 1] += probs[y]; if (at(y, t0)) joint[j - 1] += probs[y]; }
      }
    }
    const conditional = joint.map(v => v / pClick);
    return { pClick, plain, conditional, g2: conditional.map((c, i) => c / plain[i]) };
  }

  // ------------------------------------------------------------------ rewind and amplify

  const rotationAngle = p => Math.asin(Math.sqrt(p));
  /** The ideal chance of a marked outcome after r full iterations: sin^2((2r + 1) asin(sqrt(p))). */
  const successProbability = (p, r) => Math.sin((2 * r + 1) * rotationAngle(p)) ** 2;
  /** The emission strength for the clicked step that makes the marked probability `target`, or 1 if it cannot. */
  const steeredGamma = (p, gamma, target) => Math.min(1, (target === undefined ? 0.25 : target) * gamma / p);

  function clickProbability(model, T) {
    const probs = historyProbabilities(model, T);
    let p = 0;
    for (let y = 0; y < probs.length; y++) if ((y >> (T - 1)) & 1) p += probs[y];
    return p;
  }

  /** The emission strength for step T that makes one iteration enough, from the exact click rate. */
  const steerFor = (model, T) => steeredGamma(clickProbability(model, T), model.gamma);

  /** Named reflections: 'full', 'memory', or 'memory+last-w' for the memory and the last w lights. */
  function reflectionQubits(model, T, kind) {
    const n = model.nMemory, range = (a, b) => Array.from({ length: b - a }, (_, i) => a + i);
    if (kind === 'full') return range(0, n + T);
    if (kind === 'memory') return range(0, n);
    if (kind.startsWith('memory+last-')) return range(0, n).concat(range(n + T - (+kind.split('-').pop()), n + T));
    throw new RangeError('unknown reflection ' + kind);
  }

  function lightDistribution(s, nMemory, T) {
    const out = new Float64Array(1 << T), mask = (1 << T) - 1;
    for (let i = 0; i < s.re.length; i++) out[(i >> nMemory) & mask] += s.re[i] * s.re[i] + s.im[i] * s.im[i];
    return out;
  }

  function conditionalDistribution(probs, marked) {
    let total = 0;
    for (let y = 0; y < probs.length; y++) if (marked(y)) total += probs[y];
    return Float64Array.from(probs, (p, y) => (marked(y) ? p / total : 0));
  }

  function totalVariation(p, q) {
    let t = 0;
    for (let i = 0; i < p.length; i++) t += Math.abs(p[i] - q[i]);
    return t / 2;
  }

  /** "A click at step T" amplified r times on a T-step machine. `stages` keeps every sub-step for the animation.

      One iteration is: mark (Z on the last light), rewind (A dagger), reflect about zero on the watched qubits,
      replay (A). Watching every qubit is textbook amplitude amplification; watching fewer is cheaper and approximate. */
  function amplifiedHistory(model, T, options) {
    const o = Object.assign({ r: 1, reflection: 'full', steer: null, stages: false }, options || {});
    const n = model.nMemory, markQubit = n + T - 1;
    const gammas = o.steer === null ? null : Array.from({ length: T }, (_, t) => (t === T - 1 ? o.steer : null));
    const A = purifiedOps(model, T, gammas), watched = reflectionQubits(model, T, o.reflection);
    const marked = y => ((y >> (T - 1)) & 1) === 1;
    const s = run(zeroState(n + T), A);
    const stages = [];
    const snapshot = label => {
      if (!o.stages) return;
      const dist = lightDistribution(s, n, T);
      let hit = 0;
      for (let y = 0; y < dist.length; y++) if (marked(y)) hit += dist[y];
      let mask = 0;
      for (const q of watched) mask |= 1 << q;
      stages.push({ label, distribution: dist, hit, blank: probabilityWhere(s, i => !(i & mask)),
                    signed: signedHistoryAmplitudes(s, n, T) });
    };
    snapshot('prepare');
    for (let i = 0; i < o.r; i++) {
      flipWhereOne(s, markQubit); snapshot('mark');
      run(s, A, true); snapshot('rewind');
      flipWhereAllZero(s, watched); snapshot('reflect');
      run(s, A); snapshot('replay');
    }
    const distribution = lightDistribution(s, n, T);
    let hit = 0;
    for (let y = 0; y < distribution.length; y++) if (marked(y)) hit += distribution[y];
    const exact = conditionalDistribution(historyProbabilities(model, T), marked);
    const conditional = conditionalDistribution(distribution, marked);
    return { hit, distribution, conditional, exactConditional: exact, tv: totalVariation(conditional, exact),
             watched, qubits: n + T, stages };
  }

  /** Each history's amplitude size with the sign of its largest component. Meaningful right after prepare and mark,
      where every memory branch of a history shares one sign change; used only to draw the mark step. */
  function signedHistoryAmplitudes(s, nMemory, T) {
    const d = 1 << nMemory, out = new Float64Array(1 << T);
    for (let y = 0; y < out.length; y++) {
      let w = 0, big = 0, sign = 1;
      for (let m = 0; m < d; m++) {
        const i = (y << nMemory) | m, a = s.re[i] * s.re[i] + s.im[i] * s.im[i];
        w += a;
        if (a > big) { big = a; sign = s.re[i] < 0 ? -1 : 1; }
      }
      out[y] = sign * Math.sqrt(w);
    }
    return out;
  }

  /** Grover inside the loop: run t0 steps, amplify "a click at step t0", then run tau more steps on fresh lights.
      Returns the chance of keeping a shot and the click rate at each later step among the kept shots. */
  function loopQuery(model, t0, tau, options) {
    const o = Object.assign({ r: 0, reflection: 'full', steer: null }, options || {});
    const n = model.nMemory, markQubit = n + t0 - 1;
    const gammas = o.steer === null ? null : Array.from({ length: t0 }, (_, t) => (t === t0 - 1 ? o.steer : null));
    const A = purifiedOps(model, t0, gammas), watched = reflectionQubits(model, t0, o.reflection);
    const s = run(zeroState(n + t0 + tau), A);
    for (let i = 0; i < o.r; i++) {
      flipWhereOne(s, markQubit);
      run(s, A, true);
      flipWhereAllZero(s, watched);
      run(s, A);
    }
    run(s, purifiedOps(model, tau, null, n + t0));
    const kept = probabilityWhere(s, i => (i >> markQubit) & 1);
    const conditional = [];
    for (let j = 0; j < tau; j++) {
      const later = n + t0 + j;
      conditional.push(probabilityWhere(s, i => ((i >> markQubit) & 1) && ((i >> later) & 1)) / kept);
    }
    return { eventProbability: kept, conditional, qubits: n + t0 + tau };
  }

  // ------------------------------------------------------------------ helpers for the page

  /** A small seeded generator (mulberry32), so a replayed demo shows the same runs. */
  function seeded(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const historyToString = (y, T) => Array.from({ length: T }, (_, t) => (y >> t) & 1).join('');

  return { DEFAULTS, makeModel, zeroState, cloneState, run, stepOps, purifiedOps, kraus, matVec, norm2, groundMemory,
           historyProbabilities, populations, sampleStep, sampleRun, preEmission, afterClick, rotationAngle,
           successProbability, steeredGamma, clickProbability, steerFor, reflectionQubits, lightDistribution,
           conditionalDistribution, totalVariation, amplifiedHistory, loopQuery, seeded, historyToString,
           flipWhereOne, flipWhereAllZero, probabilityWhere };
});
