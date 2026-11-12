/* Rewind & Amplify Lab — the small formulas behind the three research tabs.

   Each function restates a formula used by a follow-up study in this repository, and lab/test_research.cjs holds
   it to the numbers that study saved. The headline figures on the tabs are not computed here: they are saved
   results, copied into lab/data.js by lab/make_data.py. Nothing here talks to hardware or to the network. */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.LabResearch = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // ------------------------------------------------------------------ photons (quantum_dot_bridge/)
  /** Overlap of two photons from an emitter of linewidth Γ. `detuning` is their frequency difference and
      `dephasing` is twice the pure-dephasing rate, both in units of Γ. Two identical photons give 1. */
  function overlap(detuning, dephasing) {
    const width = 1 + (dephasing || 0);
    return width / (width * width + detuning * detuning);
  }
  /** Mean overlap of a pair when a two-state environment switches between the photons with probability pSwitch. */
  const pairOverlap = (pSwitch, overlapWhenDifferent) => 1 - pSwitch * (1 - overlapWhenDifferent);
  /** Chance that one attempt ends with one photon in each detector of a balanced beam splitter:
      both photons must survive, and then they split with probability (1 − overlap) / 2. */
  const coincidence = (pairOverlapValue, survival) => survival * survival * (1 - pairOverlapValue) / 2;

  // ------------------------------------------------------------------ lasers (laser_sensor_viability/)
  /** Fraction of atoms left excited by the two-pulse sequence when the laser is `detuningHz` away from the atoms.
      A closed form of the study's Bloch integration, which it matches to within 0.0005 over ±10 Hz:
      the effective interrogation time is the dark time plus 4/π of a pulse, and the contrast is what the
      starting polarisation and T2 decay leave. */
  function atomsExcited(detuningHz, setup) {
    const s = Object.assign({ pulse: 0.0025, dark: 0.02, t2: 0.2, polarisation: 0.98 }, setup);
    const time = s.dark + 4 * s.pulse / Math.PI, contrast = s.polarisation * Math.exp(-(s.dark + s.pulse) / s.t2);
    return 0.5 + 0.5 * contrast * Math.sin(2 * Math.PI * detuningHz * time);
  }

  // ------------------------------------------------------------------ chipmaking (quantum_lithography_poc/exposure_followup/)
  const EXPOSURE = { cells: 32, arm: 0.8, linear: 2e-5, twoPhoton: 1e-3, jitter: 0.15, blurNm: 40, periodNm: 800, duty: 0.1, threshold: 20 };
  const sinc = x => (x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x));
  /** Activation events per clock in one resist cell, as coefficients of [1, cos φ, cos 2φ] across one 800 nm period.
      'noon' is two-photon light; 'phase_cycled' is laser light with half its exposures shifted half a fringe;
      'phase_cycled_burst' is that laser light bunched into bursts ten times brighter. */
  function exposure(method, setup) {
    const s = Object.assign({}, EXPOSURE, setup), M = s.cells, a = s.arm, b = s.arm;
    const g1 = [(a + b) / M, 0, 0];                                     // one-photon rate: phase cycling removes its fringe
    let g2 = method === 'noon' ? [(a * a + b * b) / (M * M), 0, 2 * a * b / (M * M)]
                               : [((a + b) ** 2 + 2 * a * b) / (M * M), 0, 2 * a * b / (M * M)];
    if (method === 'phase_cycled_burst') g2 = g2.map(v => v / s.duty);
    const transfer = h => Math.exp(-((s.jitter * h) ** 2) / 2) * Math.exp(-((2 * Math.PI * h * s.blurNm / s.periodNm) ** 2) / 2) * sinc(h / M);
    return [0, 1, 2].map(h => (s.linear * g1[h] + s.twoPhoton * g2[h]) * transfer(h));
  }
  /** Mean number of events in each cell after `clocks` clocks. The sample receives (2 × arm) × clocks photons. */
  function cellMeans(coefficients, clocks, cells) {
    return Array.from({ length: cells }, (_, j) => {
      const phi = 2 * Math.PI * j / cells;
      return clocks * (coefficients[0] + coefficients[1] * Math.cos(phi) + coefficients[2] * Math.cos(2 * phi));
    });
  }
  /** Which cells are scored: +1 well inside a stripe that should print, −1 well inside one that should not, 0 at an edge. */
  const guardCells = cells => Array.from({ length: cells }, (_, j) => { const c = Math.cos(4 * Math.PI * j / cells); return c >= 0.7 ? 1 : c <= -0.7 ? -1 : 0; });
  /** P(Poisson(mean) >= k). */
  function poissonAtLeast(mean, k) {
    let term = Math.exp(-mean), below = 0;
    for (let n = 0; n < k; n++) { below += term; term *= mean / (n + 1); }
    return 1 - below;
  }
  /** Share of scored cells printed correctly on average, and the chance that every scored cell is correct. */
  function printQuality(means, threshold) {
    const guard = guardCells(means.length);
    let sum = 0, all = 1, scored = 0;
    means.forEach((mean, j) => {
      if (!guard[j]) return;
      const printed = poissonAtLeast(mean, threshold), ok = guard[j] > 0 ? printed : 1 - printed;
      sum += ok; all *= ok; scored++;
    });
    return { accuracy: sum / scored, allCorrect: all, scored };
  }
  /** One Poisson draw (Knuth's method: fine for the means of a few tens used here). */
  function poisson(mean, random) {
    const limit = Math.exp(-mean);
    let n = 0, product = random();
    while (product > limit) { n++; product *= random(); }
    return n;
  }

  return { overlap, pairOverlap, coincidence, atomsExcited, EXPOSURE, exposure, cellMeans, guardCells, poissonAtLeast, printQuality, poisson };
});
