/* Rewind & Amplify Lab — the page.

   Everything that moves here is driven by lab/engine.js, an exact simulation of the Qiskit circuits.
   Measured IBM numbers come from lab/data.js, which lab/make_data.py copies from the saved analyses.
   No network calls, no stored "answers" for the model, no live quantum jobs. */
(function () {
  'use strict';
  const E = window.QRSMEngine, DATA = window.LAB_DATA;
  const $ = id => document.getElementById(id);
  const C = { ink: '#f6f3eb', soft: '#c9d5dd', muted: '#8fa4b3', line: '#22394b', line2: '#2f4b61', cyan: '#64d9e9',
              amber: '#edb568', violet: '#b9a8e5', blue: '#7ea6c4', red: '#f08a7c', green: '#86d6a4', dark: '#07131f' };
  const SANS = '"Segoe UI Variable Display","Segoe UI",system-ui,-apple-system,Arial,sans-serif';
  const MONO = '"Cascadia Mono","Cascadia Code",Consolas,ui-monospace,Menlo,monospace';
  const T = 6, T0 = 3, TAU = 3;
  const SCENES = ['signal', 'machine', 'question', 'rewind', 'answer', 'hardware', 'photons', 'lasers', 'chips', 'impact'];
  const RESEARCH_TABS = ['photons', 'lasers', 'chips'];
  const SCOPE = ['Live exact simulation in your browser · IBM numbers are saved raw counts · no quantum advantage is claimed',
                 'Follow-up studies: our simulations and a reanalysis of published data · no photons, lasers or wafers were measured by us'];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DEFAULT_PHI = E.DEFAULTS.phi;
  let source = Math.random;                 // ?seed=N swaps in a seeded generator so a capture can be repeated
  const random = () => source();

  const state = { scene: 'signal', level: 'plain', defect: true, phi: DEFAULT_PHI, reveal: false, speed: 1, paused: false,
                  sound: false, tour: null };

  // ------------------------------------------------------------------ small helpers
  const pct = (v, d = 2) => (100 * v).toFixed(d) + '%';
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const ease = u => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
  const span = (u, a, b) => clamp((u - a) / (b - a), 0, 1);
  const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
  const comma = n => n.toLocaleString('en-US');

  function fit(canvas) {
    // Keep the drawing coordinates the element was authored with, and add device pixels for a sharp projector image.
    const w = +canvas.dataset.w || (canvas.dataset.w = canvas.width, canvas.width);
    const h = +canvas.dataset.h || (canvas.dataset.h = canvas.height, canvas.height);
    const dpr = clamp(window.devicePixelRatio || 1, 1, 2);
    if (canvas.width !== Math.round(w * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w: +w, h: +h };
  }
  function text(ctx, s, x, y, o) {
    const p = Object.assign({ size: 13, color: C.muted, align: 'left', weight: 400, mono: false, spacing: 0, base: 'alphabetic' }, o);
    ctx.font = `${p.weight} ${p.size}px ${p.mono ? MONO : SANS}`;
    ctx.fillStyle = p.color; ctx.textAlign = p.align; ctx.textBaseline = p.base;
    if ('letterSpacing' in ctx) ctx.letterSpacing = p.spacing + 'px';
    ctx.fillText(s, x, y);
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  }
  function line(ctx, x0, y0, x1, y1, color, width) {
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.strokeStyle = color; ctx.lineWidth = width || 1; ctx.stroke();
  }
  function box(ctx, x, y, w, h, r, fill, stroke, width) {
    ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width || 1; ctx.stroke(); }
  }
  function glow(ctx, x, y, r, color, alpha) {
    if (alpha <= 0) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(color, alpha)); g.addColorStop(0.45, rgba(color, alpha * 0.35)); g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fill();
  }
  /** A travelling wave packet: a short sine under a bell curve. */
  function packet(ctx, x, y, color, alpha, phase, length, height) {
    if (alpha <= 0.01) return;
    const L = length || 30, A = height || 9;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    glow(ctx, x, y, L * 0.9, color, 0.5 * alpha);
    ctx.beginPath();
    for (let d = -L; d <= L; d += 2) {
      const yy = y + A * Math.exp(-((d / (L * 0.45)) ** 2)) * Math.sin(d * 0.42 - phase);
      if (d === -L) ctx.moveTo(x + d, yy); else ctx.lineTo(x + d, yy);
    }
    ctx.strokeStyle = rgba(color, alpha); ctx.lineWidth = 2.4; ctx.lineJoin = 'round'; ctx.stroke();
    ctx.restore();
  }

  // ------------------------------------------------------------------ the model and its statistics
  let model, K, exactRates, exactOther, after;
  const stats = { runs: 0, clicks: new Array(T).fill(0), kept: 0, later: new Array(TAU).fill(0), recent: [] };
  function resetStats() {
    stats.runs = 0; stats.kept = 0; stats.clicks.fill(0); stats.later.fill(0); stats.recent = [];
  }
  function ratesOf(m) {
    const probs = E.historyProbabilities(m, T);
    return Array.from({ length: T }, (_, t) => probs.reduce((s, p, y) => s + ((y >> t) & 1 ? p : 0), 0));
  }
  function rebuildModel() {
    model = E.makeModel({ defect: state.defect, phi: state.phi });
    K = E.kraus(model);
    exactRates = ratesOf(model);
    exactOther = ratesOf(E.makeModel({ defect: !state.defect, phi: state.phi }));
    after = E.afterClick(model, T0, TAU);
    resetStats(); resetRun();
    document.body.classList.toggle('no-defect', !state.defect);
    $('toggle-defect').innerHTML = `Hidden defect: <b>${state.defect ? 'present' : 'absent'}</b>`;
    $('toggle-defect').setAttribute('aria-pressed', state.defect);
    computeAmp(); renderAnswerNumbers(); drawStatic();
  }
  function record(bits) {
    stats.runs++;
    for (let t = 0; t < T; t++) stats.clicks[t] += bits[t];
    const kept = bits[T0 - 1] === 1;
    if (kept) { stats.kept++; for (let j = 0; j < TAU; j++) stats.later[j] += bits[T0 + j]; }
    stats.recent.unshift({ bits, kept });
    if (stats.recent.length > 204) stats.recent.length = 204;
  }

  // ------------------------------------------------------------------ one animated run
  const STEP_MS = 1750, GAP = 0.55;
  const sim = { psi: null, t: 0, bits: [], u: 0, step: null, gap: 0, flash: 0, flashKind: 0 };
  function resetRun() { sim.psi = E.groundMemory(model); sim.t = 0; sim.bits = []; sim.u = 0; sim.step = null; sim.gap = 0; }
  function beginStep() {
    const before = E.populations(model, sim.psi), pre = E.preEmission(model, sim.psi);
    const r = E.sampleStep(model, K, sim.psi, random);
    sim.step = { before, drive: pre.afterDrive, exchange: pre.afterExchange, pClick: r.pClick, y: r.y,
                 after: E.populations(model, r.psi), next: r.psi, announced: false };
    sim.u = 0;
  }
  function advance(dt) {
    if (state.paused) return;
    let budget = dt * state.speed / STEP_MS;
    sim.flash = Math.max(0, sim.flash - dt / 420);
    let guard = 0;
    while (budget > 0 && guard++ < 400) {
      if (sim.gap > 0) { const used = Math.min(sim.gap, budget); sim.gap -= used; budget -= used; if (sim.gap <= 0) resetRun(); continue; }
      if (!sim.step) beginStep();
      const used = Math.min(1 - sim.u, budget);
      sim.u += used; budget -= used;
      if (!sim.step.announced && sim.u >= 0.86) {
        sim.step.announced = true;
        if (sim.step.y) { sim.flash = 1; tick(); }
      }
      if (sim.u >= 1) {
        sim.bits.push(sim.step.y); sim.psi = sim.step.next; sim.step = null; sim.t++;
        if (sim.t >= T) { record(sim.bits.slice()); sim.gap = GAP; }
      }
    }
  }
  function shownPopulations() {
    const s = sim.step;
    if (!s) return E.populations(model, sim.psi);
    const u = sim.u, out = [];
    for (let q = 0; q < model.nMemory; q++) {
      let v = lerp(s.before[q], s.drive[q], ease(span(u, 0.2, 0.32)));
      v = lerp(v, s.exchange[q], ease(span(u, 0.34, 0.5)));
      v = lerp(v, s.after[q], ease(span(u, 0.86, 0.97)));
      out.push(v);
    }
    return out;
  }
  const phaseOf = u => (u < 0.32 ? 'drive' : u < 0.5 ? 'exchange' : u < 0.86 ? 'emit' : 'read');

  // a soft tick on every click, only when asked for
  let audio = null;
  function tick() {
    if (!state.sound) return;
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const o = audio.createOscillator(), g = audio.createGain();
      o.type = 'triangle'; o.frequency.value = 1320;
      g.gain.setValueAtTime(0.16, audio.currentTime); g.gain.exponentialRampToValueAtTime(0.0008, audio.currentTime + 0.09);
      o.connect(g).connect(audio.destination); o.start(); o.stop(audio.currentTime + 0.1);
    } catch (e) { state.sound = false; }
  }

  // ------------------------------------------------------------------ the bench: laser, emitter, hidden defect, detector
  const bench = document.createElement('canvas');
  bench.id = 'bench'; bench.setAttribute('role', 'img');
  bench.setAttribute('aria-label', 'Animation: a drive laser excites an emitter, a hidden defect exchanges energy with it, and a detector records a click or no click each step');
  const BENCH_H = { large: 392, medium: 330, small: 330 };
  function mountBench() {
    const slot = document.querySelector(`#${state.scene} .bench-slot`);
    if (!slot) { bench.remove(); return; }
    bench.dataset.h = BENCH_H[slot.dataset.bench] || 360;
    if (bench.parentNode !== slot) slot.appendChild(bench);
  }
  function drawBench(now) {
    const slot = bench.parentNode;
    if (!slot) return;
    // The drawing is as wide as its slot is, so nothing is letterboxed: positions are fractions of the width.
    const area = slot.getBoundingClientRect(), H = +bench.dataset.h;
    const W = area.height > 40 ? clamp(Math.round(H * area.width / area.height / 20) * 20, 860, 1900) : 1200;
    if (+bench.dataset.w !== W || bench.height % H) { bench.dataset.w = W; bench.width = W; bench.height = H; }
    const { ctx } = fit(bench);
    const ts = clamp(W / Math.max(area.width, 1), 1, 1.55);             // keeps labels near 12 px on screen
    // element scale: as large as the width allows, but never so large that the record collides with the labels above it
    const m = clamp(Math.min(W / 1250, (H - 66 * ts - 40) / 180), 0.74, 1.3);
    const detail = area.width >= 900 && area.height >= 300;             // a short or narrow panel drops the second line of each label
    const cy = Math.round(H * (detail ? 0.42 : 0.4)), ex = Math.round(W * 0.46), er = 40 * m;
    const dOff = Math.min(112 * m + 14, cy - 34), dy = cy - dOff, dr = 23 * m;
    const lx0 = W * 0.05, lw = 156 * m, lx1 = lx0 + lw, detw = 126 * m, detx = W * 0.95 - detw;
    const s = sim.step, u = s ? sim.u : 0, pops = shownPopulations();
    const pe = pops[0], pd = model.k ? pops[1] : 0, phase = now / 90;
    const label = (str, x, y, o) => text(ctx, str, x, y, Object.assign({ size: 12 * ts, spacing: 2, weight: 600, align: 'center' }, o));
    const note = (str, x, y, o) => { if (detail) text(ctx, str, x, y, Object.assign({ size: 12 * ts, align: 'center' }, o)); };

    // faint guides: the drive beam and the output waveguide
    line(ctx, lx1 + 10, cy, ex - er - 8, cy, rgba(C.amber, 0.16), 2);
    line(ctx, ex + er + 8, cy - 9 * m, detx - 6, cy - 9 * m, rgba(C.cyan, 0.17), 1.5);
    line(ctx, ex + er + 8, cy + 9 * m, detx - 6, cy + 9 * m, rgba(C.cyan, 0.17), 1.5);

    // drive laser
    const driving = s ? 1 - span(u, 0.24, 0.34) : 0, lh = 34 * m;
    box(ctx, lx0, cy - lh, lw, 2 * lh, 14 * m, '#0b1a28', rgba(C.amber, 0.9), 1.6);
    box(ctx, lx1 - 4, cy - 12 * m, 14 * m, 24 * m, 4, rgba(C.amber, 0.25 + 0.5 * driving), rgba(C.amber, 0.9), 1.2);
    ctx.beginPath();
    for (let d = 0; d <= lw - 60 * m; d += 2) { const yy = cy + 11 * m * Math.sin(d * 0.2 / m - phase * (s ? 1 : 0.25)); d ? ctx.lineTo(lx0 + 26 * m + d, yy) : ctx.moveTo(lx0 + 26 * m, yy); }
    ctx.strokeStyle = rgba(C.amber, 0.85); ctx.lineWidth = 1.8; ctx.stroke();
    label('DRIVE LASER', lx0 + lw / 2, cy + lh + 22 * ts, { color: C.amber });
    note('one pulse per step', lx0 + lw / 2, cy + lh + 40 * ts);
    if (s && u < 0.27) packet(ctx, lerp(lx1 + 16, ex - er - 6, ease(u / 0.26)), cy, C.amber, 0.95, phase, 34 * m, 11 * m);

    // the hidden region: the defect and its link to the emitter
    const veilTop = Math.max(6, dy - dr - 12), veilBottom = cy - er - 5;
    if (state.reveal) {
      if (model.k) {
        ctx.beginPath();
        for (let yy = dy + dr; yy <= cy - er; yy += 2) { const xx = ex + 5 * Math.sin((yy - dy) * 0.5 + phase * 0.6); yy === dy + dr ? ctx.moveTo(xx, yy) : ctx.lineTo(xx, yy); }
        ctx.strokeStyle = rgba(C.violet, 0.75); ctx.lineWidth = 1.8; ctx.stroke();
        const swapping = s ? Math.sin(Math.PI * span(u, 0.33, 0.5)) : 0;
        if (swapping > 0.02) {
          const a = lerp(dy + dr, cy - er, span(u, 0.33, 0.5));
          ctx.save(); ctx.globalCompositeOperation = 'lighter';
          glow(ctx, ex, a, 13 * m, C.violet, 0.9 * swapping); glow(ctx, ex, dy + dr + cy - er - a, 13 * m, C.cyan, 0.9 * swapping);
          ctx.restore();
        }
        ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, ex, dy, dr * 2.3, C.violet, 0.12 + 0.88 * pd); ctx.restore();
        ctx.beginPath(); ctx.arc(ex, dy, dr, 0, 2 * Math.PI); ctx.fillStyle = '#0b1a28'; ctx.fill();
        ctx.strokeStyle = C.violet; ctx.lineWidth = 2; ctx.stroke();
        ctx.beginPath(); ctx.arc(ex, dy, (4 + 11 * Math.sqrt(pd)) * m, 0, 2 * Math.PI); ctx.fillStyle = rgba(C.violet, 0.35 + 0.65 * pd); ctx.fill();
        label('HIDDEN DEFECT', ex + dr + 16, dy - 2, { color: C.violet, align: 'left' });
        text(ctx, detail ? `a second qubit nobody measures · excited ${pct(pd, 0)}` : `excited ${pct(pd, 0)}`, ex + dr + 16, dy + 16 * ts, { size: 12 * ts });
      } else {
        ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.arc(ex, dy, dr, 0, 2 * Math.PI); ctx.strokeStyle = rgba(C.violet, 0.45); ctx.lineWidth = 1.5; ctx.stroke(); ctx.setLineDash([]);
        label('NOTHING HERE', ex + dr + 16, dy - 2, { color: C.muted, align: 'left' });
        text(ctx, 'this device has no hidden defect', ex + dr + 16, dy + 16 * ts, { size: 12 * ts });
      }
    } else {
      const vw = Math.max(236 * m, 215 * ts), vx = ex - vw / 2, vh = veilBottom - veilTop;
      ctx.save(); ctx.beginPath(); ctx.roundRect(vx, veilTop, vw, vh, 12); ctx.clip();
      ctx.fillStyle = '#0a1622'; ctx.fillRect(vx, veilTop, vw, vh);
      for (let d = -vh; d < vw; d += 11) line(ctx, vx + d, veilTop + vh, vx + d + vh, veilTop, rgba(C.violet, 0.16), 1);
      ctx.restore();
      ctx.setLineDash([6, 5]); box(ctx, vx, veilTop, vw, vh, 12, null, rgba(C.violet, 0.6), 1.3); ctx.setLineDash([]);
      label('HIDDEN FROM THE DETECTOR', ex, veilTop + vh / 2 + 1, { base: 'middle', color: C.violet, size: 11.5 * ts, spacing: 1.8 });
    }

    // emitter
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, ex, cy, er * 2.5, C.cyan, 0.1 + 0.9 * pe); ctx.restore();
    ctx.beginPath(); ctx.arc(ex, cy, er, 0, 2 * Math.PI); ctx.fillStyle = '#0b1a28'; ctx.fill();
    ctx.strokeStyle = rgba(C.cyan, 0.55); ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(ex, cy, er, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * pe); ctx.strokeStyle = C.cyan; ctx.lineWidth = 4.5; ctx.lineCap = 'round'; ctx.stroke(); ctx.lineCap = 'butt';
    ctx.beginPath(); ctx.arc(ex, cy, (6 + 20 * Math.sqrt(pe)) * m, 0, 2 * Math.PI); ctx.fillStyle = rgba(C.cyan, 0.3 + 0.7 * pe); ctx.fill();
    ctx.beginPath(); ctx.arc(ex, cy, 3.5 * m, 0, 2 * Math.PI); ctx.fillStyle = C.ink; ctx.fill();
    label('EMITTER', ex, cy + er + 22 * ts, { color: C.cyan });
    note(`a qubit · excited ${pct(pe, 0)}`, ex, cy + er + 40 * ts);

    // the light on its way out: one wave, whose detection is a matter of chance
    if (s && u >= 0.5 && u < 0.9) {
      const a = 0.3 + 0.7 * Math.sqrt(s.pClick), fade = s.y ? 1 : 1 - span(u, 0.8, 0.9);
      packet(ctx, lerp(ex + er + 10, detx - 16, ease(span(u, 0.5, 0.86))), cy, C.cyan, a * fade, phase, 30 * m, 9 * m);
    }

    // detector
    const f = sim.flash, dh = 40 * m;
    if (f > 0) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, detx + 18, cy, 150 * m * (1.25 - 0.4 * f), C.amber, 0.95 * f); ctx.restore(); }
    box(ctx, detx, cy - dh, detw, 2 * dh, 14 * m, f > 0 ? rgba(C.amber, 0.12 + 0.3 * f) : '#0b1a28', f > 0 ? C.amber : rgba(C.ink, 0.75), 1.6 + f);
    ctx.beginPath(); ctx.arc(detx + 6, cy, 22 * m, -Math.PI / 2, Math.PI / 2); ctx.strokeStyle = f > 0 ? C.amber : rgba(C.ink, 0.75); ctx.lineWidth = 2; ctx.stroke();
    if (f > 0.05) label('CLICK', detx + detw / 2 + 12 * m, cy + 7 * m, { size: 20 * m * Math.max(1, ts * 0.9), weight: 700, color: C.amber });
    else if (s && u >= 0.9 && !s.y) text(ctx, 'no click', detx + detw / 2 + 12 * m, cy + 5, { align: 'center', size: 13 * ts });
    label('DETECTOR', detx + detw / 2, cy + dh + 22 * ts, { color: C.ink });
    note('one bit per step', detx + detw / 2, cy + dh + 40 * ts);

    // the click record
    const cw = 58 * m * Math.max(1, ts * 0.85), gap = 10 * m, total = T * cw + (T - 1) * gap, tx = (W - total) / 2;
    const ch = 42 * m * Math.max(1, ts * 0.85), ty = H - ch - (detail ? 22 : 26) * ts;
    text(ctx, 'CLICK RECORD', tx - 18, ty + ch / 2 + 4, { align: 'right', size: 11.5 * ts, spacing: 2, weight: 600 });
    text(ctx, `run ${comma(stats.runs + (sim.gap > 0 ? 0 : 1))}`, tx + total + 18, ty + ch / 2 + 4, { size: 12 * ts, mono: true });
    const asking = state.scene !== 'signal' && state.scene !== 'machine';
    for (let t = 0; t < T; t++) {
      const x = tx + t * (cw + gap), done = t < sim.bits.length, live = !done && t === sim.t && sim.gap <= 0;
      const bit = done ? sim.bits[t] : null, key = asking && t === T0 - 1;
      box(ctx, x, ty, cw, ch, 9 * m, bit ? rgba(C.amber, 0.2) : '#0b1a28',
          bit ? C.amber : live ? C.cyan : key ? rgba(C.amber, 0.75) : C.line2, bit || live || key ? 1.8 : 1);
      text(ctx, `${t + 1}`, x + cw / 2, ty - 7, { align: 'center', size: 11 * ts, mono: true, color: key ? C.amber : C.muted });
      if (done) text(ctx, String(bit), x + cw / 2, ty + ch / 2 + 1, { align: 'center', base: 'middle', size: 22 * m * Math.max(1, ts * 0.85), mono: true, color: bit ? C.amber : C.muted, weight: bit ? 700 : 400 });
      else if (live) text(ctx, '·', x + cw / 2, ty + ch / 2, { align: 'center', base: 'middle', size: 26 * m, color: C.cyan });
    }
    if (asking) text(ctx, 'the click we ask about', tx + (T0 - 1) * (cw + gap) + cw / 2, ty + ch + 15 * ts, { align: 'center', size: 11 * ts, color: C.amber });
  }

  // ------------------------------------------------------------------ scene 1: click rate by step
  function drawRates() {
    const { ctx, w, h } = fit($('rate-chart'));
    const x0 = 44, x1 = w - 12, y0 = 12, y1 = h - 26, top = 0.16;
    for (const v of [0, 0.05, 0.1, 0.15]) {
      const y = y1 - v / top * (y1 - y0);
      line(ctx, x0, y, x1, y, C.line, 1); text(ctx, `${Math.round(v * 100)}%`, x0 - 8, y + 4, { align: 'right', size: 11, mono: true });
    }
    const bw = (x1 - x0) / T;
    for (let t = 0; t < T; t++) {
      const cx = x0 + (t + 0.5) * bw;
      if (stats.runs) {
        const v = stats.clicks[t] / stats.runs, hh = clamp(v / top, 0, 1) * (y1 - y0);
        box(ctx, cx - bw * 0.27, y1 - hh, bw * 0.54, hh, 4, rgba(C.ink, 0.3), null);
      }
      const mine = state.defect ? C.cyan : C.amber, other = state.defect ? C.amber : C.cyan;
      const yo = y1 - exactOther[t] / top * (y1 - y0), ym = y1 - exactRates[t] / top * (y1 - y0);
      line(ctx, cx - bw * 0.36, yo, cx + bw * 0.36, yo, rgba(other, state.reveal ? 0.35 : 0.9), 2);
      line(ctx, cx - bw * 0.36, ym, cx + bw * 0.36, ym, rgba(mine, 0.9), 2);
      text(ctx, `${t + 1}`, cx, h - 8, { align: 'center', size: 11, mono: true });
    }
    $('rate-note').textContent = `Bars: ${comma(stats.runs)} run${stats.runs === 1 ? '' : 's'} so far. Lines: exact, cyan with the defect and amber without.`
      + (state.reveal ? '' : ' Which device is this? Keep watching.');
  }

  // ------------------------------------------------------------------ scene 2: live meters and the circuit highlight
  let lastPhase = '';
  function updateMachine() {
    const pops = shownPopulations(), s = sim.step;
    const set = (id, v, on) => { $('m-' + id).style.width = pct(on ? v : 0, 1); $('v-' + id).textContent = on ? pct(v, 0) : '—'; };
    set('emitter', pops[0], true); set('defect', model.k ? pops[1] : 0, !!model.k);
    set('click', s ? s.pClick : 0, !!s);
    const phase = s ? phaseOf(sim.u) : '';
    if (phase !== lastPhase) {
      lastPhase = phase;
      document.querySelectorAll('#circuit .gate').forEach(g => g.classList.toggle('on', g.dataset.phase === phase));
    }
  }

  // ------------------------------------------------------------------ scene 3: the raster and the tally
  const RASTER_ROWS = 34;
  function drawRaster() {
    const { ctx, w, h } = fit($('raster'));
    const cols = 6, rows = RASTER_ROWS, cell = 19, cgap = 3, runW = T * (cell + cgap) - cgap, colGap = (w - 24 - cols * runW) / (cols - 1);
    const rh = (h - 26) / rows;
    for (let c = 0; c < cols; c++) {
      const x = 12 + c * (runW + colGap), kx = x + (T0 - 1) * (cell + cgap);
      box(ctx, kx - 2, 16, cell + 4, h - 22, 5, rgba(C.amber, 0.09), rgba(C.amber, 0.28), 1);
      for (let t = 0; t < T; t++) text(ctx, `${t + 1}`, x + t * (cell + cgap) + cell / 2, 11, { align: 'center', size: 10, mono: true, color: t === T0 - 1 ? C.amber : C.muted });
    }
    stats.recent.forEach((run, i) => {
      const c = Math.floor(i / rows), r = i % rows;
      if (c >= cols) return;
      const x = 12 + c * (runW + colGap), y = 20 + r * rh, hh = Math.max(4, rh - 5);
      if (run.kept) box(ctx, x - 4, y - 2, runW + 8, hh + 4, 4, rgba(C.amber, 0.13), null);
      for (let t = 0; t < T; t++) {
        const on = run.bits[t] === 1, key = t === T0 - 1;
        box(ctx, x + t * (cell + cgap), y, cell, hh, 3,
            on ? (key ? C.amber : run.kept ? C.cyan : rgba(C.ink, 0.75)) : rgba(C.blue, run.kept ? 0.22 : 0.1), null);
      }
    });
    if (!stats.recent.length) text(ctx, 'Runs appear here as the machine finishes them.', w / 2, h / 2, { align: 'center', size: 14 });
  }
  function updateTally() {
    $('t-runs').textContent = comma(stats.runs);
    $('t-kept').textContent = comma(stats.kept);
    $('t-kept-rate').textContent = stats.runs ? `${pct(stats.kept / stats.runs, 1)} of runs · exact ${pct(after.pClick)}` : `exact ${pct(after.pClick)}`;
    $('t-waste').textContent = comma(stats.runs - stats.kept);
    const exact = after.conditional[TAU - 1];
    if (stats.kept >= 1) {
      const p = stats.later[TAU - 1] / stats.kept, se = Math.sqrt(Math.max(p * (1 - p), 1 / (4 * stats.kept)) / stats.kept);
      $('t-est').textContent = pct(p, 1);
      $('t-est-note').textContent = `± ${(196 * se).toFixed(1)} points, from only ${comma(stats.kept)} kept run${stats.kept === 1 ? '' : 's'}`;
    } else { $('t-est').textContent = '—'; $('t-est-note').textContent = 'waiting for a run with the click'; }
    $('t-exact').textContent = `exact for this model: ${pct(exact)}`;
  }

  // ------------------------------------------------------------------ scene 4: rewind and amplify
  const STAGES = ['prepare', 'mark', 'rewind', 'reflect', 'replay'];
  const amp = { steer: true, reflection: 'memory+last-1', stage: 0, u: 1, playing: false, result: null, base: 0, rate: 1 };
  function computeAmp() {
    const steer = amp.steer ? E.steerFor(model, T0) : null;
    amp.result = E.amplifiedHistory(model, T0, { r: 1, reflection: amp.reflection, steer, stages: true });
    amp.base = E.clickProbability(model, T0);
    amp.gamma = steer;
  }
  function measuredFor() {
    // IBM ran the default defect model. Show its numbers only when that is the model on screen.
    if (!state.defect || Math.abs(state.phi - DEFAULT_PHI) > 1e-9) return null;
    const name = `click3-${amp.steer ? 'steered-' : ''}${amp.reflection}-r1`;
    const precise = Object.values(DATA.hero.precision).find(v => v && v.name === name);
    return precise ? Object.assign({ run: 'precision' }, precise) : (DATA.variants[name] ? Object.assign({ run: 'first' }, DATA.variants[name]) : null);
  }
  function setStage(k, animate) {
    amp.stage = clamp(k, 0, 4); amp.u = animate && !reduced ? 0 : 1;
    document.querySelectorAll('#stages button').forEach((b, i) => { b.classList.toggle('on', i === amp.stage); b.classList.toggle('done', i < amp.stage); });
    renderAmpText();
  }
  function playAmp() {
    amp.playing = true; setStage(0, true); $('amp-play').textContent = '❚❚ Playing';
  }
  function stopAmp() { amp.playing = false; amp.rate = 1; $('amp-play').textContent = '▶ Play one round'; }
  function advanceAmp(dt) {
    if (amp.u < 1) amp.u = Math.min(1, amp.u + dt * amp.rate / 1500);
    else if (amp.playing) {
      amp.hold = (amp.hold || 0) + dt * amp.rate;
      if (amp.hold > 1100) { amp.hold = 0; if (amp.stage < 4) setStage(amp.stage + 1, true); else stopAmp(); }
    }
  }
  function renderAmpText() {
    if (!amp.result) return;
    const r = amp.result, s = r.stages, n = r.watched.length, all = r.qubits, m = measuredFor();
    const p0 = s[0].hit, blank = s[2].blank, local = amp.reflection !== 'full';
    const plain = [
      `PREPARE. Run the reversible machine once. All eight possible 3-step records now exist together, each with a wave height of √probability. The click we want is ${pct(p0)} of the total.`,
      `MARK. One gate flips the sign of every record that has a click at step 3. Nothing you could measure has changed yet: the probabilities are the same.`,
      `REWIND. Run the machine backwards. Unmarked, everything would return to the blank start. Because of the mark, only ${pct(blank, 1)} does.`,
      `REFLECT. Flip the sign of the blank start${local ? `, checking just ${n} of the ${all} qubits` : `, checking all ${all} qubits`}.`,
      `REPLAY. Run forward again. The waves now add up on the records with the click: ${pct(r.hit)} instead of ${pct(amp.base)}.`,
    ];
    const tech = [
      `A|0⟩ = Σ |m_y⟩|y⟩ on ${all} qubits${amp.steer ? `, with the step-3 emission steered to γ′ = ${amp.gamma.toFixed(3)}` : ''}. p = ${p0.toFixed(4)}, θ = asin√p = ${(E.rotationAngle(p0) * 180 / Math.PI).toFixed(1)}°.`,
      `S_f = Z on light 3. It is a single-qubit gate because the predicate reads one bit. Amplitudes of marked histories change sign; |amplitude|² does not.`,
      `A† S_f A|0⟩. The overlap with ${local ? `the watched ${n}-qubit zero subspace` : '|0…0⟩'} is ${local ? blank.toFixed(4) : `(1 − 2p)² = ${blank.toFixed(4)}`}.`,
      `S_0 on ${n} qubit${n === 1 ? '' : 's'}: ${local ? 'the memory and the last light. Cheaper multi-controlled Z, but an approximation' : 'a multi-controlled Z over every qubit, built from relative-phase Toffolis with ancillas'}.`,
      `Q = A S_0 A† S_f gives P = ${r.hit.toFixed(4)}${local ? '' : ` = sin²(3θ)`}. Conditional-distribution error TV = ${r.tv.toFixed(4)}. Cost: 3 calls of the machine.`,
    ];
    $('stage-caption').textContent = (state.level === 'tech' ? tech : plain)[amp.stage];
    $('amp-hit').textContent = pct(r.hit);
    $('amp-hit-note').textContent = `ideal · was ${pct(amp.base)}` + (amp.steer ? `, steered to ${pct(p0)}` : ', not steered');
    $('amp-tv').textContent = r.tv < 5e-7 ? '0.000' : r.tv.toFixed(3);
    $('amp-tv').style.color = r.tv < 5e-7 ? C.cyan : C.amber;
    $('amp-gates').textContent = m ? String(m.two_qubit_gates) : '—';
    $('amp-gates-note').textContent = m ? `measured hit rate ${pct(m.probability, 1)} over ${comma(m.shots)} shots` : 'IBM ran the default defect model (φ = 0.45)';
    $('amp-full').innerHTML = `Full reflection<small>all ${all} qubits</small>`;
    $('amp-local').innerHTML = `Local reflection<small>${model.nMemory + 1} qubits</small>`;
    let a, b;
    if (!amp.steer) {
      a = `Without steering the click is too rare for one round: ${pct(r.hit, 1)}. Textbook Grover needs three, and on IBM Marrakesh three rounds cost ${DATA.variants['click3-full-r3'].two_qubit_gates} gates and reached ${pct(DATA.variants['click3-full-r3'].probability, 1)}.`;
      b = `Unsteered p = ${amp.base.toFixed(4)} gives sin²(3θ) = ${E.successProbability(amp.base, 1).toFixed(3)}; the peak is at r = 3 (${E.successProbability(amp.base, 3).toFixed(3)}), i.e. 7 machine calls and far more depth.`;
    } else if (local) {
      a = `Steering makes one round enough. The local reflection checks fewer qubits, so it needs about half the gates. The price is a small bias in the ideal answer (${r.tv.toFixed(3)}).`;
      b = `Steering is classical importance reweighting of one emission angle: it scales every marked history equally, so conditionals stay exact. The local S_0 leaks outside the 2-D Grover plane, hence TV = ${r.tv.toFixed(4)}.`;
    } else {
      a = `Exact in theory: the answer is untouched. But every extra gate is a chance for noise, and this build needs about twice as many.`;
      b = `Full S_0 keeps the state in span{|good⟩, |bad⟩}, so the conditional law is preserved to machine precision. The cost is the wide multi-controlled Z after transpilation.`;
    }
    $('amp-insight').textContent = a; $('amp-insight-tech').textContent = b;
  }
  function drawAmp() {
    const { ctx, w, h } = fit($('amp-canvas'));
    const r = amp.result, s = r.stages, k = amp.stage, u = ease(amp.u);
    const order = [0, 1, 2, 3, 4, 5, 6, 7], mid = 216, unit = 158, bw = 56, gap = 20, groupGap = 54, left = 46;
    const xOf = i => left + i * (bw + gap) + (i >= 4 ? groupGap : 0);
    const A = j => order.map(y => Math.sqrt(s[j].distribution[y]));
    // which picture: records (stages 0, 1, 4) or the rewound view (stages 2, 3)
    let recAlpha = 1, values = A(0), signs = order.map(() => 1), blankVal = 0;
    if (k === 0) values = A(0).map(v => v * u);
    else if (k === 1) { values = A(0); signs = order.map(y => ((y >> 2) & 1 ? 1 - 2 * u : 1)); }
    else if (k === 2) { values = A(0); signs = order.map(y => ((y >> 2) & 1 ? -1 : 1)); recAlpha = 1 - u; blankVal = Math.sqrt(s[2].blank); }
    else if (k === 3) { recAlpha = 0; blankVal = Math.sqrt(s[2].blank) * (1 - 2 * u); }
    else { values = A(4); recAlpha = u; blankVal = -Math.sqrt(s[2].blank); }

    line(ctx, left - 14, mid, xOf(7) + bw + 14, mid, C.line2, 1.2);
    text(ctx, 'WAVE HEIGHT = √PROBABILITY', left - 14, 22, { size: 13, spacing: 2, weight: 600 });
    if (recAlpha > 0.01) {
      ctx.save(); ctx.globalAlpha = recAlpha;
      text(ctx, 'NO CLICK AT STEP 3', (xOf(0) + xOf(3) + bw) / 2, h - 8, { align: 'center', size: 13, spacing: 1.6, weight: 600, color: C.blue });
      text(ctx, 'CLICK AT STEP 3 · WHAT WE ASKED FOR', (xOf(4) + xOf(7) + bw) / 2, h - 8, { align: 'center', size: 13, spacing: 1.6, weight: 600, color: C.amber });
      const dist = k === 4 ? s[4].distribution : s[0].distribution;
      order.forEach((y, i) => {
        const marked = (y >> 2) & 1, v = values[i] * signs[i], hh = v * unit, x = xOf(i), color = marked ? C.amber : C.blue;
        box(ctx, x, hh >= 0 ? mid - hh : mid, bw, Math.max(Math.abs(hh), 1.5), 5, rgba(color, marked ? 0.9 : 0.6), null);
        // the record as three dots in time order: filled means a click
        for (let t = 0; t < 3; t++) {
          const on = (y >> t) & 1, dx = x + bw / 2 + (t - 1) * 16, dyy = h - 54;
          ctx.beginPath(); ctx.arc(dx, dyy, 5.5, 0, 2 * Math.PI);
          if (on) { ctx.fillStyle = t === 2 ? C.amber : C.ink; ctx.fill(); } else { ctx.strokeStyle = C.line2; ctx.lineWidth = 1.4; ctx.stroke(); }
        }
        const p = dist[y] * (k === 0 ? u : 1);
        text(ctx, p >= 0.0995 ? pct(p, 1) : pct(p, 2), x + bw / 2, h - 31, { align: 'center', size: 13.5, mono: true, color: marked ? C.amber : C.soft });
      });
      ctx.restore();
    }
    if (recAlpha < 0.99) {
      ctx.save(); ctx.globalAlpha = 1 - recAlpha;
      const bx = left + 120, rx = bx + 250, big = 130, rest = Math.sqrt(1 - s[2].blank), hh = blankVal * unit, local = amp.reflection !== 'full';
      box(ctx, bx, hh >= 0 ? mid - hh : mid, big, Math.max(Math.abs(hh), 1.5), 6, rgba(C.cyan, 0.85), null);
      box(ctx, rx, mid - rest * unit, big, rest * unit, 6, rgba(C.amber, 0.5), null);
      text(ctx, local ? 'BLANK ON THE WATCHED QUBITS' : 'BACK AT THE BLANK START', bx + big / 2, h - 34, { align: 'center', size: 13, spacing: 1.6, weight: 600, color: C.cyan });
      text(ctx, pct(s[2].blank, 1), bx + big / 2, h - 10, { align: 'center', size: 17, mono: true, color: C.cyan });
      text(ctx, 'COULD NOT REWIND', rx + big / 2, h - 34, { align: 'center', size: 13, spacing: 1.6, weight: 600, color: C.amber });
      text(ctx, pct(1 - s[2].blank, 1), rx + big / 2, h - 10, { align: 'center', size: 17, mono: true, color: C.amber });
      ctx.restore();
    }

    // the geometry: a rotation in the plane of (everything else, runs with the click)
    const cx = 850, cyy = 262, R = 200;
    const p0 = s[0].hit, th = E.rotationAngle(p0), end = E.rotationAngle(r.hit) + (r.hit > 0.999999 ? 0 : 0);
    let ang = th;
    if (k === 0) ang = th; else if (k === 1) ang = lerp(th, -th, u); else if (k === 2 || k === 3) ang = -th; else ang = lerp(-th, Math.min(end, Math.PI / 2), u);
    ctx.beginPath(); ctx.arc(cx, cyy, R, -Math.PI / 2, 0.42); ctx.strokeStyle = C.line2; ctx.lineWidth = 1.2; ctx.stroke();
    line(ctx, cx, cyy, cx + R + 22, cyy, C.line2, 1.2); line(ctx, cx, cyy, cx, cyy - R - 18, C.line2, 1.2);
    text(ctx, 'EVERYTHING ELSE', cx + R + 22, cyy + 20, { align: 'right', size: 12.5, spacing: 1.4, weight: 600, color: C.blue });
    text(ctx, 'RUNS WITH THE CLICK', cx + 10, cyy - R - 8, { size: 12.5, spacing: 1.4, weight: 600, color: C.amber });
    ctx.setLineDash([5, 6]); line(ctx, cx, cyy, cx + (R + 12) * Math.cos(th), cyy - (R + 12) * Math.sin(th), rgba(C.ink, k >= 1 ? 0.55 : 0.2), 1.2); ctx.setLineDash([]);
    if (k >= 1) text(ctx, 'starting direction', cx + (R + 16) * Math.cos(th), cyy - (R + 16) * Math.sin(th) - 2, { size: 13, color: C.soft });
    const vx = cx + R * Math.cos(ang), vy = cyy - R * Math.sin(ang);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, vx, vy, 26, C.cyan, 0.8); ctx.restore();
    line(ctx, cx, cyy, vx, vy, C.cyan, 3.2);
    ctx.beginPath(); ctx.arc(vx, vy, 6.5, 0, 2 * Math.PI); ctx.fillStyle = C.ink; ctx.fill();
    line(ctx, vx, vy, vx, cyy, rgba(C.amber, 0.7), 1.4);
    const shown = Math.sin(ang) ** 2 * (k === 4 && u > 0.98 ? 0 : 1) + (k === 4 && u > 0.98 ? r.hit : 0);
    text(ctx, pct(shown, 1), cx - 18, cyy - 26, { size: 34, mono: true, color: C.amber, weight: 500, align: 'right' });
    text(ctx, 'chance of the click', cx - 18, cyy - 4, { size: 13, align: 'right' });
    text(ctx, '= height²', cx - 18, cyy + 14, { size: 13, align: 'right' });
  }

  // ------------------------------------------------------------------ scene 5: two futures
  const answer = { sampled: null, ibm: false };
  function refModels() { return { defect: E.makeModel({ phi: state.phi }), none: E.makeModel({ defect: false }) }; }
  function renderAnswerNumbers() {
    const m = refModels(), d = E.afterClick(m.defect, T0, TAU), n = E.afterClick(m.none, T0, TAU);
    answer.exact = { defect: d, none: n };
    $('ans-defect').textContent = pct(d.conditional[2]); $('ans-none').textContent = pct(n.conditional[2]);
    $('phi-out').textContent = state.phi.toFixed(2);
    $('answer-note').textContent = `Exact predictions. A click at step 3 happens in ${pct(d.pClick)} of runs with the defect and ${pct(n.pClick)} without.`
      + (answer.ibm ? ' Diamonds: IBM Marrakesh, steer + local build, raw counts with 95% intervals. Right order at step 6, visibly biased.' : '');
  }
  function sampleAnswer() {
    const m = refModels(), N = 20000, out = {};
    for (const key of ['defect', 'none']) {
      const Kk = E.kraus(m[key]); let kept = 0; const later = [0, 0, 0];
      for (let i = 0; i < N; i++) { const b = E.sampleRun(m[key], T, random, Kk).bits; if (b[2]) { kept++; later[0] += b[3]; later[1] += b[4]; later[2] += b[5]; } }
      out[key] = { kept, later, n: N };
    }
    answer.sampled = out;
    $('ans-sample-note').textContent = `Sampled ${comma(N)} runs of each model in your browser: kept ${comma(out.defect.kept)} with the defect and ${comma(out.none.kept)} without. Dots with bars are those samples.`;
  }
  function drawAnswer() {
    const { ctx, w, h } = fit($('answer-canvas'));
    const x0 = 70, x1 = w - 40, y0 = 30, y1 = h - 58, top = 0.14;
    const X = j => x0 + (j + 0.5) / 3 * (x1 - x0), Y = v => y1 - clamp(v / top, 0, 1.04) * (y1 - y0);
    for (let v = 0; v <= top + 1e-9; v += 0.02) { line(ctx, x0, Y(v), x1, Y(v), C.line, 1); text(ctx, `${Math.round(v * 100)}%`, x0 - 12, Y(v) + 5, { align: 'right', size: 13, mono: true }); }
    for (let j = 0; j < 3; j++) text(ctx, `step ${T0 + 1 + j}`, X(j), h - 22, { align: 'center', size: 15, color: C.ink });
    text(ctx, `${j3('after the click')}`, x1, h - 4, { align: 'right', size: 11.5 });
    const series = [['none', C.amber, 'emitter only'], ['defect', C.cyan, 'with the hidden defect']];
    for (const [key, color, name] of series) {
      const vals = answer.exact[key].conditional;
      ctx.beginPath(); vals.forEach((v, j) => (j ? ctx.lineTo(X(j), Y(v)) : ctx.moveTo(X(j), Y(v)))); ctx.strokeStyle = color; ctx.lineWidth = 3.2; ctx.lineJoin = 'round'; ctx.stroke();
      vals.forEach((v, j) => {
        ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, X(j), Y(v), 20, color, 0.5); ctx.restore();
        ctx.beginPath(); ctx.arc(X(j), Y(v), 7, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill();
        text(ctx, pct(v), X(j) + (key === 'none' ? -14 : 14), Y(v) + (key === 'none' ? -14 : 24), { align: key === 'none' ? 'right' : 'left', size: 17, mono: true, color });
      });
      text(ctx, name, X(2) + 16, Y(vals[2]) + (key === 'none' ? -34 : 44), { size: 12.5, color, align: 'right' });
      const smp = answer.sampled && answer.sampled[key];
      if (smp && smp.kept > 0) smp.later.forEach((c, j) => {
        const p = c / smp.kept, se = 1.96 * Math.sqrt(p * (1 - p) / smp.kept), x = X(j) + (key === 'none' ? 26 : -26);
        line(ctx, x, Y(p - se), x, Y(p + se), rgba(color, 0.9), 2); line(ctx, x - 5, Y(p - se), x + 5, Y(p - se), rgba(color, 0.9), 2); line(ctx, x - 5, Y(p + se), x + 5, Y(p + se), rgba(color, 0.9), 2);
        ctx.beginPath(); ctx.arc(x, Y(p), 4.5, 0, 2 * Math.PI); ctx.fillStyle = C.dark; ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
      });
      if (answer.ibm) {
        const rows = DATA.loops.precision.builds.local[key === 'none' ? 'no_defect' : 'defect'].future;
        rows.forEach((f, j) => {
          const x = X(j) + (key === 'none' ? 50 : -50), y = Y(f.probability);
          line(ctx, x, Y(f.wilson95[0]), x, Y(f.wilson95[1]), rgba(color, 0.75), 1.6);
          ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x + 7, y); ctx.lineTo(x, y + 8); ctx.lineTo(x - 7, y); ctx.closePath();
          ctx.fillStyle = C.dark; ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
          if (j === 2) text(ctx, `IBM ${pct(f.probability, 1)}`, x, y + (key === 'none' ? -14 : 24), { align: 'center', size: 11.5, mono: true, color });
        });
      }
    }
    function j3(s) { return s; }
  }

  // ------------------------------------------------------------------ scene 6: IBM hardware
  const hw = { run: 'precision', u: 1 };
  function renderHardware() {
    const h = DATA.hero[hw.run], L = h.local, F = h.full;
    const label = { precision: `Precision repeat · ${comma(h.shots)} shots per circuit`, first: `First run · ${comma(h.shots)} shots per circuit`,
                    suppressed: `Same circuits with dynamical decoupling and twirling · ${comma(h.shots)} shots` }[hw.run];
    $('hw-run-label').textContent = label;
    for (const [id, key] of [['hw-precision', 'precision'], ['hw-first', 'first'], ['hw-supp', 'suppressed']]) $(id).setAttribute('aria-pressed', hw.run === key);
    $('hw-local-rate').textContent = pct(L.probability); $('hw-full-rate').textContent = pct(F.probability);
    $('hw-local-count').textContent = `${comma(L.accepted)} of ${comma(L.shots)} shots hit the click`;
    $('hw-full-count').textContent = `${comma(F.accepted)} of ${comma(F.shots)} shots hit the click`;
    $('hw-local-gates').textContent = `${L.two_qubit_gates} two-qubit gates · depth ${L.depth}`;
    $('hw-full-gates').textContent = `${F.two_qubit_gates} two-qubit gates · depth ${F.depth}`;
    $('hw-tv-local').textContent = L.tv_to_exact.toFixed(3); $('hw-tv-full').textContent = F.tv_to_exact.toFixed(3);
    $('hw-ideal-local').textContent = pct(L.ideal_probability, 1); $('hw-ideal-full').textContent = pct(F.ideal_probability, 1);
    const nm = DATA.noise_model;
    $('hw-nm-local').textContent = pct(nm.local.echo_scaled.hit_rate, 1); $('hw-nm-full').textContent = pct(nm.full.echo_scaled.hit_rate, 1);
    $('hw-nm-note').textContent = hw.run === 'suppressed' ? 'fitted on echo circuits only · models no DD or twirling' : 'fitted on echo circuits only';
    $('hw-nm-scale').textContent = nm.gate_error_scale.toFixed(2);
    $('hw-meas-local').textContent = pct(L.probability, 1); $('hw-meas-full').textContent = pct(F.probability, 1);
    $('hw-gps-local').textContent = L.gates_per_accepted_shot.toFixed(0); $('hw-gps-full').textContent = F.gates_per_accepted_shot.toFixed(0);
    const plain = DATA.variants['click3-full-r0'];
    $('hw-plain-rate').textContent = pct(plain.probability);
    $('hw-plain-note').textContent = `${comma(plain.accepted)} of ${comma(plain.shots)} shots in the first run · ideal ${pct(plain.ideal_probability)}: on a rare event, noise adds false clicks`;
    const d = h.difference;
    $('hw-diff').textContent = d
      ? `Local minus full: ${(100 * d.probability).toFixed(2)} points (95% interval ${(100 * d.interval95[0]).toFixed(2)} to ${(100 * d.interval95[1]).toFixed(2)}, independent shots). `
        + (hw.run === 'suppressed' ? 'Suppression did not improve the answer error here.' : 'Routing, circuit width and drift differ, so gate count is not proven to be the only cause.') + ' Runs are never pooled.'
      : '';
    $('hw-job').textContent = `job ${h.job_id} · ${DATA.backend} · ${h.submitted_utc.slice(0, 10)}`;
    const c = DATA.campaign;
    $('hw-campaign').textContent = `campaign: ${c.jobs} jobs, ${comma(c.science_circuits)} circuits, ${comma(c.total_shots)} shots, ${c.qpu_seconds} s of QPU time`;
    const names = { plain: 'Plain sampling', local: 'Steer + local', full: 'Steer + full', memory: 'Memory-only control' };
    const body = document.querySelector('#hw-loop tbody'); body.replaceChildren();
    const loops = DATA.loops[hw.run].builds;
    for (const key of ['plain', 'local', 'full', 'memory']) {
      const dft = loops[key].defect.future[2].probability, non = loops[key].no_defect.future[2].probability, ok = dft < non && key !== 'memory';
      const tr = document.createElement('tr');
      const cells = [names[key], pct(dft), pct(non), key === 'memory' ? 'wrong answer' : ok ? 'right' : 'reversed'];
      cells.forEach((t, i) => { const td = document.createElement('td'); td.textContent = t; if (i === 3) td.className = ok ? 'ok' : 'bad'; tr.append(td); });
      body.append(tr);
    }
    hw.u = reduced ? 1 : 0;
  }
  function drawShots(id, row, color, predicted) {
    const { ctx, w, h } = fit($(id));
    const rows = row.shots > 4096 ? 32 : 16, cols = row.shots / rows, cw = w / cols, chh = h / rows, lit = Math.round(row.accepted * ease(hw.u));
    ctx.fillStyle = rgba(C.blue, 0.13);
    for (let i = 0; i < row.shots; i++) { const c = Math.floor(i / rows), r = i % rows; ctx.fillRect(c * cw + 0.3, r * chh + 0.3, cw - 0.6, chh - 0.6); }
    ctx.fillStyle = color;
    for (let i = 0; i < lit; i++) { const c = Math.floor(i / rows), r = i % rows; ctx.fillRect(c * cw + 0.3, r * chh + 0.3, cw - 0.6, chh - 0.6); }
    const ix = row.ideal_probability * w;
    line(ctx, ix, 0, ix, h, C.ink, 1.5);
    text(ctx, `ideal ${pct(row.ideal_probability, 1)}`, ix - 6, 13, { align: 'right', size: 11, color: C.ink, mono: true });
    if (predicted !== undefined) {
      const px = predicted * w;
      ctx.setLineDash([4, 4]); line(ctx, px, 0, px, h, C.ink, 1.5); ctx.setLineDash([]);
      text(ctx, `model ${pct(predicted, 1)}`, px + 6, h - 7, { size: 11, color: C.ink, mono: true });
    }
  }

  // ------------------------------------------------------------------ research tabs: shared pieces
  // The three research tabs animate the follow-up studies. Their numbers are saved results, copied into
  // DATA.research by lab/make_data.py; lab/research.js holds the small formulas the animations use.
  const RS = DATA.research, RM = window.LabResearch;
  /** A canvas drawn in screen pixels, whatever shape its slot has. Returns the context, its size and a scale. */
  function stage(canvas) {
    const r = canvas.getBoundingClientRect();
    const shape = (+canvas.dataset.w0 || (canvas.dataset.w0 = canvas.width)) / (+canvas.dataset.h0 || (canvas.dataset.h0 = canvas.height));
    const W = Math.round(clamp(r.width || 900, 300, 1800)), H = Math.round(r.height > 90 ? clamp(r.height, 200, 1100) : W / shape);
    if (+canvas.dataset.w !== W || +canvas.dataset.h !== H) { canvas.dataset.w = W; canvas.dataset.h = H; canvas.width = W; canvas.height = H; }
    const { ctx } = fit(canvas);
    return { ctx, W, H, m: clamp(Math.min(W / 900, H / 430), 0.36, 1.5), detail: W >= 720 && H >= 330 };
  }
  const caps = (ctx, s, x, y, o) => text(ctx, s, x, y, Object.assign({ size: 11.5, spacing: 1.8, weight: 600, align: 'center' }, o));
  function setPressed(ids, on) { for (const id of ids) $(id).setAttribute('aria-pressed', id === on); }

  // ------------------------------------------------------------------ scene 7: photons at a beam splitter
  const PAIR_MS = 1600, HUE = [C.cyan, '#f39a86'];          // a photon shifted to the blue, or to the red
  const ph = { mode: 'shared', u: 0, pair: null, pairs: 0, split: 0, a: 0, b: 0, recent: [], flashA: 0, flashB: 0, both: 0 };
  function resetPhotons() { Object.assign(ph, { u: 0, pair: null, pairs: 0, split: 0, a: 0, b: 0, recent: [], flashA: 0, flashB: 0, both: 0 }); }
  function setPhotonSource(mode) {
    ph.mode = mode; resetPhotons(); setPressed(['ph-shared', 'ph-indep'], mode === 'shared' ? 'ph-shared' : 'ph-indep'); renderPhotons();
  }
  function newPair() {
    // the environment sits in one of two states; between the two photons it switches with the study's probability
    const trap = RS.photons.trap, pSwitch = trap[ph.mode === 'shared' ? 0 : trap.length - 1].switch_probability;
    const first = random() < 0.5 ? 0 : 1, second = random() < pSwitch ? 1 - first : first;
    const overlap = first === second ? 1 : RM.overlap(RS.photons.detuning_in_linewidths, 0);
    ph.pair = { first, second, split: random() < RM.coincidence(overlap, 1), side: random() < 0.5 ? 0 : 1, counted: false };
    ph.u = 0;
  }
  function advancePhotons(dt) {
    if (state.paused) return;
    ph.flashA = Math.max(0, ph.flashA - dt / 420); ph.flashB = Math.max(0, ph.flashB - dt / 420); ph.both = Math.max(0, ph.both - dt / 700);
    let budget = dt * state.speed / PAIR_MS, guard = 0;
    while (budget > 0 && guard++ < 600) {
      if (!ph.pair) newPair();
      const used = Math.min(1 - ph.u, budget); ph.u += used; budget -= used;
      const p = ph.pair;
      if (!p.counted && ph.u >= 0.86) {
        p.counted = true; ph.pairs++;
        if (p.split) { ph.split++; ph.a++; ph.b++; ph.flashA = ph.flashB = 1; ph.both = 1; }
        else if (p.side === 0) { ph.a += 2; ph.flashA = 1; } else { ph.b += 2; ph.flashB = 1; }
        ph.recent.unshift(p.split ? 1 : 0); if (ph.recent.length > 48) ph.recent.length = 48;
        tick();
      }
      if (ph.u >= 1) ph.pair = null;
    }
  }
  function renderPhotons() {
    const P = RS.photons;
    $('ph-a').textContent = pct(P.coincidence_per_attempt.shared, 1); $('ph-b').textContent = pct(P.coincidence_per_attempt.independent, 1);
    $('ph-ma').textContent = `photon overlap ${P.overlap.shared.toFixed(2)}`; $('ph-mb').textContent = `photon overlap ${P.overlap.independent.toFixed(2)}`;
    $('ph-survival').textContent = pct(P.survival, 0);
    $('ph-ibm').innerHTML = `${P.on_ibm.shared.overlap.toFixed(2)} <i>vs</i> ${P.on_ibm.independent.overlap.toFixed(2)}`;
    $('ph-ibm-note').textContent = `measured overlap · ideal ${P.on_ibm.shared.ideal.toFixed(2)} and ${P.on_ibm.independent.ideal.toFixed(2)}`;
    const g = $('ph-gaas'); g.replaceChildren();
    for (const row of P.gaas) {
      const d = document.createElement('div');
      d.innerHTML = `<small>${row.separation_ns.toFixed(1)} ns apart</small><b>${row.visibility.toFixed(2)}</b><span>${row.interval95[0].toFixed(3)} to ${row.interval95[1].toFixed(3)}</span>`;
      g.append(d);
    }
    $('ph-dead0').textContent = P.dead_time.ignored.toFixed(3); $('ph-dead1').textContent = P.dead_time.modelled.toFixed(3);
    $('ph-truth').textContent = P.dead_time.truth.toFixed(2);
  }
  function drawPhotons(now) {
    const { ctx, W, H, m, detail } = stage($('photons-canvas'));
    const strip = detail ? 54 : 42, cy = (H - strip) * 0.53, arm = Math.min((H - strip) * 0.3, 150 * m);
    const sx = W * 0.085, rx = W * 0.2, ax = W * 0.33, bx = W * 0.58, dxx = W * 0.8, yT = cy - arm, yB = cy + arm;
    const p = ph.pair, u = p ? ph.u : 0, phase = now / 90, er = 34 * m;
    const fs = v => Math.max(10, v * clamp(m, 0.85, 1.2));
    // the paths: one photon takes the long way round so that both reach the beam splitter together
    const loopX = (rx + ax) / 2, loopR = Math.min(24 * m, arm * 0.28);
    ctx.strokeStyle = rgba(C.cyan, 0.17); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(sx + er, cy); ctx.lineTo(rx, cy); ctx.lineTo(ax, yT); ctx.lineTo(bx, cy); ctx.lineTo(dxx, yB);
    ctx.moveTo(rx, cy); ctx.lineTo(ax, yB); ctx.lineTo(bx, cy); ctx.lineTo(dxx, yT); ctx.stroke();
    ctx.beginPath(); ctx.arc(lerp(rx, ax, 0.5), lerp(cy, yT, 0.5) - loopR, loopR, 0, 2 * Math.PI); ctx.stroke();
    if (detail) text(ctx, 'delay', loopX + loopR + 8, lerp(cy, yT, 0.5) - loopR * 1.6, { size: fs(11) });
    // the hidden environment: a charge trap that tints each photon blue or red
    const tr = 20 * m, ty = cy - er - Math.max(34 * m, arm * 0.42) - tr;
    const flip = p && p.first !== p.second ? ease(span(u, 0.16, 0.26)) : 0;
    const side = p ? lerp(p.first, p.second, flip) : 0, trapX = sx + (side - 0.5) * tr * 0.9;
    ctx.beginPath();
    for (let yy = ty + tr; yy <= cy - er; yy += 2) { const xx = sx + 4 * Math.sin((yy - ty) * 0.5 + phase * 0.6); yy === ty + tr ? ctx.moveTo(xx, yy) : ctx.lineTo(xx, yy); }
    ctx.strokeStyle = rgba(C.violet, 0.7); ctx.lineWidth = 1.6; ctx.stroke();
    ctx.beginPath(); ctx.arc(sx, ty, tr, 0, 2 * Math.PI); ctx.fillStyle = '#0b1a28'; ctx.fill(); ctx.strokeStyle = C.violet; ctx.lineWidth = 1.8; ctx.stroke();
    ctx.beginPath(); ctx.arc(trapX, ty, 5.5 * m, 0, 2 * Math.PI); ctx.fillStyle = p ? (flip > 0.5 ? HUE[p.second] : HUE[p.first]) : C.violet; ctx.fill();
    const lx = Math.max(10, sx - er - 6), ly = ty - tr - (detail ? 26 : 10);
    caps(ctx, 'HIDDEN ENVIRONMENT', lx, ly, { color: C.violet, align: 'left', size: fs(11) });
    if (detail) text(ctx, ph.mode === 'shared' ? 'a charge trap · holds still for both photons' : 'a charge trap · may flip between the photons', lx, ly + 16, { size: fs(11.5) });
    // the source
    const glowing = p ? Math.max(1 - span(u, 0.02, 0.14), u > 0.24 ? 1 - span(u, 0.26, 0.38) : 0) : 0;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, sx, cy, er * 2.3, C.cyan, 0.1 + 0.6 * glowing); ctx.restore();
    ctx.beginPath(); ctx.arc(sx, cy, er, 0, 2 * Math.PI); ctx.fillStyle = '#0b1a28'; ctx.fill(); ctx.strokeStyle = rgba(C.cyan, 0.8); ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(sx, cy, (7 + 12 * glowing) * m, 0, 2 * Math.PI); ctx.fillStyle = rgba(C.cyan, 0.35 + 0.6 * glowing); ctx.fill();
    caps(ctx, 'QUANTUM DOT', sx, cy + er + 18, { color: C.cyan, size: fs(11) });
    if (detail) text(ctx, 'two photons per attempt', sx, cy + er + 34, { size: fs(11.5), align: 'center' });
    // the beam splitter
    const bh = Math.min(arm * 0.6, 72 * m);
    const meeting = p ? Math.sin(Math.PI * span(u, 0.58, 0.68)) : 0;
    if (meeting > 0.02) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, bx, cy, 46 * m, p.first === p.second ? HUE[p.first] : C.ink, 0.7 * meeting); ctx.restore(); }
    box(ctx, bx - 3.5, cy - bh, 7, 2 * bh, 3, rgba(C.ink, 0.5), rgba(C.ink, 0.85), 1);
    caps(ctx, 'BEAM SPLITTER', bx, cy + bh + 18, { color: C.ink, size: fs(11) });
    if (detail) text(ctx, 'half through, half reflected', bx, cy + bh + 34, { size: fs(11.5), align: 'center' });
    // detectors
    const dw = 112 * m, dh = 36 * m;
    const det = (y, f, name, n) => {
      if (f > 0) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, dxx + 14, y, 110 * m * (1.2 - 0.3 * f), C.amber, 0.85 * f); ctx.restore(); }
      box(ctx, dxx, y - dh, dw, 2 * dh, 12 * m, f > 0 ? rgba(C.amber, 0.12 + 0.3 * f) : '#0b1a28', f > 0 ? C.amber : rgba(C.ink, 0.75), 1.5 + f);
      ctx.beginPath(); ctx.arc(dxx + 5, y, 17 * m, -Math.PI / 2, Math.PI / 2); ctx.strokeStyle = f > 0 ? C.amber : rgba(C.ink, 0.75); ctx.lineWidth = 1.8; ctx.stroke();
      text(ctx, comma(n), dxx + dw / 2 + 8 * m, y + 1, { align: 'center', base: 'middle', size: fs(17), mono: true, color: f > 0.05 ? C.amber : C.soft });
      caps(ctx, name, dxx + dw + 10, y + 4, { align: 'left', color: C.ink, size: fs(11) });
    };
    det(yT, ph.flashA, 'A', ph.a); det(yB, ph.flashB, 'B', ph.b);
    if (ph.both > 0.02) caps(ctx, 'ONE IN EACH', dxx + dw / 2, cy + 4, { color: rgba(C.amber, clamp(ph.both * 1.6, 0, 1)), size: fs(12) });
    else if (p && p.counted && !p.split) caps(ctx, 'TOGETHER', dxx + dw / 2, cy + 4, { color: rgba(C.cyan, 0.8 * (1 - span(u, 0.94, 1))), size: fs(12) });
    // the photons
    if (p) {
      const along = (pts, v) => { const n = pts.length - 1, i = Math.min(n - 1, Math.floor(v * n)), w = v * n - i; return [lerp(pts[i][0], pts[i + 1][0], w), lerp(pts[i][1], pts[i + 1][1], w)]; };
      const top = [[sx + er, cy], [rx, cy], [ax, yT], [bx, cy]], low = [[sx + er, cy], [rx, cy], [ax, yB], [bx, cy]];
      const a1 = span(u, 0.04, 0.62), a2 = span(u, 0.3, 0.62);
      // the first photon idles in the delay loop while the second is emitted
      if (u >= 0.04 && u < 0.62) {
        const held = span(a1, 0.42, 0.72), v = a1 < 0.42 ? a1 / 0.42 * 0.5 : a1 < 0.72 ? 0.5 : 0.5 + (a1 - 0.72) / 0.28 * 0.5;
        let [x, y] = along(top, v);
        if (a1 >= 0.42 && a1 < 0.72) { const ang = Math.PI / 2 + 2 * Math.PI * held; x = lerp(rx, ax, 0.5) + loopR * Math.cos(ang); y = lerp(cy, yT, 0.5) - loopR + loopR * Math.sin(ang); }
        packet(ctx, x, y, HUE[p.first], 0.95, phase, 24 * m, 8 * m);
      }
      if (u >= 0.3 && u < 0.62) { const [x, y] = along(low, a2); packet(ctx, x, y, HUE[p.second], 0.95, phase + 1.3, 24 * m, 8 * m); }
      if (u >= 0.62 && u < 0.9) {
        const w = ease(span(u, 0.62, 0.86)), fade = 1 - span(u, 0.84, 0.9);
        const out = s => [lerp(bx, dxx - 12, w), lerp(cy, s === 0 ? yT : yB, w)];
        const s1 = p.side, s2 = p.split ? 1 - p.side : p.side, lag = p.split ? 0 : 20 * m;
        const [x1, y1] = out(s1), [x2, y2] = out(s2);
        packet(ctx, x1 + lag * 0.5, y1, HUE[p.first], 0.95 * fade, phase, 24 * m, 8 * m);
        packet(ctx, x2 - lag * 0.5, y2, HUE[p.second], 0.95 * fade, phase + 1.3, 24 * m, 8 * m);
      }
    }
    // the record of recent pairs
    const n = Math.min(48, Math.max(16, Math.floor((W * 0.6) / (15 * Math.max(m, 0.7))))), cw = Math.min(15, (W * 0.62) / n), x0 = (W - n * cw) / 2, y0 = H - (detail ? 30 : 22);
    for (let i = 0; i < n; i++) {
      const v = ph.recent[i];
      box(ctx, x0 + i * cw + 1.5, y0, cw - 3, 11, 2.5, v === undefined ? rgba(C.blue, 0.1) : v ? C.amber : rgba(C.cyan, 0.45), null);
    }
    caps(ctx, detail ? 'LATEST PAIRS · AMBER = ONE PHOTON IN EACH DETECTOR' : 'LATEST PAIRS', W / 2, y0 - 9, { size: fs(10.5) });
    $('ph-note').innerHTML = `Here every photon arrives: <b>${comma(ph.pairs)}</b> pairs so far, <b>${comma(ph.split)}</b> split`
      + (ph.pairs ? ` (${pct(ph.split / ph.pairs, 0)})` : '') + `. Either way each detector counts about the same. In the study only ${pct(RS.photons.survival, 0)} of photons survive, hence the smaller numbers on the right.`;
  }

  // ------------------------------------------------------------------ scene 8: catching a laser that steps at an unknown time
  // A replay of one stored record of the monitoring study for each scenario; the bars are its rates over 1,920 records.
  const RECORD_MS = 25000, LS_HOLD = 0.2, SCENARIOS = { 'ls-nominal': 'nominal', 'ls-short': 'short_coherence', 'ls-path': 'shared_path' };
  const MONITORS = [['classical', C.blue, 'Ordinary reference', 'c'], ['quantum', C.violet, 'Atoms alone', 'q'],
                    ['classical_quantum', C.cyan, 'Reference + atoms', 'cq'], ['two_classical', C.amber, 'Two references', 'cc']];
  const ls = { scenario: 'nominal', t: 0, hold: 0 };
  function setLaserScenario(key) {
    Object.assign(ls, { scenario: key, t: 0, hold: 0 });
    for (const id of Object.keys(SCENARIOS)) $(id).setAttribute('aria-pressed', SCENARIOS[id] === key);
    renderLasers();
  }
  function advanceLasers(dt) {
    if (state.paused) return;
    const T = RS.lasers.config.cycles, step = dt * state.speed / RECORD_MS;
    if (ls.t < T) ls.t = Math.min(T, ls.t + step * T);
    else { ls.hold += step; if (ls.hold > LS_HOLD) { ls.t = 0; ls.hold = 0; } }
  }
  /** What one monitor did on the stored record: caught in time, alarmed before the laser moved, alarmed late, or stayed silent. */
  function verdict(example, key) {
    const at = example.first_alarm_s[key], late = at - example.onset_s;
    if (at < 0) return { kind: 'silent', text: 'no alarm' };
    if (late < 0) return { kind: 'false', text: `alarm at ${at} s, before the laser moved` };
    return late <= RS.lasers.window_s ? { kind: 'caught', text: `alarm ${late} s after the step` } : { kind: 'late', text: `alarm ${late} s after: too late` };
  }
  function renderLasers() {
    const L = RS.lasers, S = L.scenarios[ls.scenario], nominal = L.scenarios.nominal.monitors;
    for (const [key, , , id] of MONITORS) { $('ls-m-' + id).style.width = pct(S.monitors[key].caught, 1); $('ls-v-' + id).textContent = pct(S.monitors[key].caught, 1); }
    const fa = MONITORS.map(([key]) => pct(S.monitors[key].false_alarm, 0)).join(', ');
    const note = $('ls-fa'); note.classList.toggle('alert', ls.scenario === 'shared_path');
    note.textContent = ls.scenario === 'nominal' ? `Of ${comma(S.records)} records with a ${L.step_hz} Hz step. False alarms on quiet records, in the same order: ${fa}.`
      : ls.scenario === 'short_coherence' ? `With atoms that lose coherence sooner, adding them hurt: ${pct(S.monitors.classical_quantum.caught, 1)} against ${pct(S.monitors.classical.caught, 1)} for the ordinary reference alone (${pct(nominal.classical_quantum.caught, 1)} when calibrated).`
      : `When only the shared path stepped and the laser was fine, the monitors still raised a laser alarm: ${fa} of quiet records.`;
    const body = document.querySelector('#ls-atomic tbody'); body.replaceChildren();
    for (const row of L.atomic_on_ibm) {
      const tr = document.createElement('tr');
      [`${row.detuning_hz > 0 ? '+' : row.detuning_hz < 0 ? '−' : ''}${Math.abs(row.detuning_hz)} Hz`, pct(row.model, 1), pct(row.measured, 1)].forEach(t => { const td = document.createElement('td'); td.textContent = t; tr.append(td); });
      body.append(tr);
    }
  }
  function drawLasers(now) {
    const { ctx, W, H, m, detail } = stage($('lasers-canvas'));
    const L = RS.lasers, E = L.scenarios[ls.scenario].example, T = L.config.cycles, t = ls.t, i = Math.min(T - 1, Math.floor(t));
    const fs = v => Math.max(10, v * clamp(m, 0.85, 1.2));
    const side = W >= 640, Lw = side ? clamp(W * 0.25, 170, 300) : 0;
    // ---- the apparatus: a laser feeding an ordinary receiver and a cloud of atoms
    if (side) {
      const lx = 18, lw = Lw * 0.56, lh = 21 * m, ly = 22 + lh, bx = lx + lw + 16, phase = now / 90;
      const ry = H * 0.44, ay = H * 0.76, ix = lx + Lw * 0.5, ra = Math.min(Lw * 0.27, H * 0.15);
      box(ctx, lx, ly - lh, lw, 2 * lh, 10 * m, '#0b1a28', rgba(C.amber, 0.9), 1.5);
      ctx.beginPath(); for (let d = 0; d <= lw - 26; d += 2) { const yy = ly + 7 * m * Math.sin(d * 0.26 - phase); d ? ctx.lineTo(lx + 13 + d, yy) : ctx.moveTo(lx + 13, yy); }
      ctx.strokeStyle = rgba(C.amber, 0.85); ctx.lineWidth = 1.6; ctx.stroke();
      caps(ctx, 'LASER', lx + lw + 12, ly - 2, { color: C.amber, align: 'left', size: fs(11) });
      if (detail) text(ctx, `${L.config.wavelength_nm.toFixed(0)} nm`, lx + lw + 12, ly + 13, { size: fs(11.5) });
      // the beam, split towards both instruments
      ctx.strokeStyle = rgba(C.amber, 0.3); ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(lx + 22, ly + lh); ctx.lineTo(lx + 22, ay); ctx.lineTo(ix - ra - 4, ay); ctx.moveTo(lx + 22, ry); ctx.lineTo(ix - 34 * m, ry); ctx.stroke();
      const beat = t % 1;
      if (t < T) { packet(ctx, lx + 22, lerp(ly + lh, ry, beat), C.amber, 0.7, phase, 10 * m, 4 * m); packet(ctx, lerp(lx + 22, ix - ra, beat), ay, C.amber, 0.7, phase, 12 * m, 5 * m); }
      // the ordinary receiver
      const rw = Math.min(Lw * 0.5, 120 * m), rh = 22 * m;
      box(ctx, ix - 34 * m, ry - rh, rw, 2 * rh, 9 * m, '#0b1a28', rgba(C.cyan, 0.9), 1.5);
      text(ctx, `${E.receiver_hz[i] >= 0 ? '+' : '−'}${Math.abs(E.receiver_hz[i]).toFixed(2)} Hz`, ix - 34 * m + rw / 2, ry + 1, { align: 'center', base: 'middle', size: fs(14), mono: true, color: C.cyan });
      caps(ctx, 'ORDINARY RECEIVER', ix - 34 * m, ry - rh - 9, { align: 'left', color: C.cyan, size: fs(10.5) });
      // the atoms: each second, some of the 64 are left excited
      const excited = E.atoms_excited[i], n = L.config.atoms;
      ctx.beginPath(); ctx.arc(ix, ay, ra, 0, 2 * Math.PI); ctx.fillStyle = '#0b1a28'; ctx.fill(); ctx.strokeStyle = rgba(C.violet, 0.8); ctx.lineWidth = 1.5; ctx.stroke();
      for (let k = 0; k < n; k++) {
        const rr = ra * 0.86 * Math.sqrt((k + 0.5) / n), a = k * 2.39996, lit = ((k * 37 + i * 11) % n) < excited;
        ctx.beginPath(); ctx.arc(ix + rr * Math.cos(a), ay + rr * Math.sin(a), Math.max(1.6, 2.5 * m), 0, 2 * Math.PI);
        ctx.fillStyle = lit ? C.violet : rgba(C.violet, 0.18); ctx.fill();
      }
      caps(ctx, `${n} ATOMS`, ix + ra + 10, ay - 4, { align: 'left', color: C.violet, size: fs(10.5) });
      text(ctx, `${excited} excited`, ix + ra + 10, ay + 12, { size: fs(12), mono: true, color: C.soft });
    }
    // ---- two charts on one time axis: what was read, and how close each monitor is to raising the alarm
    const x0 = Lw + (side ? 58 : 44), x1 = W - 14, yA0 = 22, yB1 = H - 24, gapY = detail ? 30 : 22;
    const hA = (yB1 - yA0 - gapY) * 0.58, yA1 = yA0 + hA, yB0 = yA1 + gapY, X = s => x0 + s / T * (x1 - x0);
    const span_hz = 2.9, YA = hz => (yA0 + yA1) / 2 - clamp(hz / span_hz, -1, 1) * hA / 2, top = 2.6, YB = v => yB1 - clamp(v / top, 0, 1) * (yB1 - yB0);
    const win0 = E.onset_s, win1 = Math.min(T, E.onset_s + L.window_s);
    for (const [ya, yb] of [[yA0, yA1], [yB0, yB1]]) { ctx.fillStyle = rgba(C.green, 0.07); ctx.fillRect(X(win0), ya, X(win1) - X(win0), yb - ya); }
    for (const hz of [-2, 0, 2]) { line(ctx, x0, YA(hz), x1, YA(hz), C.line, 1); text(ctx, `${hz > 0 ? '+' : hz < 0 ? '−' : ''}${Math.abs(hz)} Hz`, x0 - 8, YA(hz) + 4, { align: 'right', size: fs(10.5), mono: true }); }
    line(ctx, x0, yB1, x1, yB1, C.line2, 1);
    for (const s of [0, 32, 64, 96, 128]) text(ctx, `${s} s`, X(s), yB1 + 15, { align: 'center', size: fs(10.5), mono: true });
    ctx.setLineDash([5, 4]); line(ctx, X(win0), yA0, X(win0), yB1, rgba(C.green, 0.9), 1.4); ctx.setLineDash([]);
    text(ctx, detail ? `the laser steps by ${L.step_hz} Hz · ${L.window_s} s to catch it` : 'the laser steps', X(win0) + 6, yA0 + 11, { size: fs(11), color: C.green });
    if (ls.scenario === 'shared_path') {
      ctx.setLineDash([5, 4]); line(ctx, X(E.nuisance_onset_s), yA0, X(E.nuisance_onset_s), yB1, C.red, 1.4); ctx.setLineDash([]);
      text(ctx, 'the shared path steps', X(E.nuisance_onset_s) - 6, yA0 + 11, { size: fs(11), color: C.red, align: 'right' });
    }
    const upto = Math.floor(t);
    for (let k = 0; k < upto; k++) { ctx.beginPath(); ctx.arc(X(k + 0.5), YA(E.atoms_hz[k]), Math.max(1.6, 2.1 * m), 0, 2 * Math.PI); ctx.fillStyle = rgba(C.violet, 0.75); ctx.fill(); }
    const trace = (values, color, width, dash) => {
      if (upto < 2) return;
      ctx.beginPath(); for (let k = 0; k < upto; k++) (k ? ctx.lineTo(X(k + 0.5), YA(values[k])) : ctx.moveTo(X(k + 0.5), YA(values[k])));
      ctx.setLineDash(dash || []); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.stroke(); ctx.setLineDash([]);
    };
    trace(E.laser_hz, rgba(C.ink, 0.7), 1.4, [3, 3]); trace(E.receiver_hz, C.cyan, 2.2);
    caps(ctx, 'READINGS, EACH SECOND', x0, yA0 - 8, { align: 'left', size: fs(10.5) });
    if (detail) {
      const ly = yA1 - 8; let lx = x0 + 8;
      const key = (draw, label, color) => { draw(lx); text(ctx, label, lx + 20, ly + 4, { size: fs(11), color }); lx += 30 + ctx.measureText(label).width + 12; };
      ctx.font = `400 ${fs(11)}px ${SANS}`;
      key(x => { ctx.beginPath(); ctx.arc(x + 8, ly, 3, 0, 2 * Math.PI); ctx.fillStyle = C.violet; ctx.fill(); }, 'atoms', C.violet);
      key(x => line(ctx, x, ly, x + 16, ly, C.cyan, 2.2), 'ordinary receiver', C.cyan);
      key(x => { ctx.setLineDash([3, 3]); line(ctx, x, ly, x + 16, ly, rgba(C.ink, 0.8), 1.4); ctx.setLineDash([]); }, 'the laser itself, unseen', C.soft);
    }
    // alarm level of each monitor: it fires on first crossing the line
    caps(ctx, detail ? 'HOW CLOSE EACH MONITOR IS TO AN ALARM' : 'ALARM LEVEL', x0, yB0 - 8, { align: 'left', size: fs(10.5) });
    ctx.setLineDash([6, 4]); line(ctx, x0, YB(1), x1, YB(1), rgba(C.ink, 0.75), 1.2); ctx.setLineDash([]);
    text(ctx, 'alarm level', x1 - 4, YB(1) - 6, { align: 'right', size: fs(10.5), color: C.ink });
    const s0 = E.score_times_s[0];
    for (const [key, color] of MONITORS) {
      const scores = E.scores[key], last = Math.min(scores.length, Math.floor(t) - s0 + 1);
      if (last > 1) {
        ctx.beginPath(); for (let k = 0; k < last; k++) (k ? ctx.lineTo(X(s0 + k), YB(scores[k])) : ctx.moveTo(X(s0 + k), YB(scores[k])));
        ctx.strokeStyle = rgba(color, key === 'quantum' ? 0.75 : 0.95); ctx.lineWidth = key === 'quantum' ? 1.4 : 2; ctx.lineJoin = 'round'; ctx.stroke();
      }
      const at = E.first_alarm_s[key];
      if (at >= 0 && t >= at) {
        const v = verdict(E, key), good = v.kind === 'caught', x = X(at), y = YB(1);
        ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 7, y); ctx.lineTo(x, y + 9); ctx.lineTo(x - 7, y); ctx.closePath();
        ctx.fillStyle = color; ctx.fill(); ctx.strokeStyle = good ? C.green : C.red; ctx.lineWidth = 2; ctx.stroke();
      }
    }
    const done = t >= T, lines = MONITORS.map(([key, , name]) => { const v = verdict(E, key); return `<span class="${v.kind}">${name}: ${v.text}</span>`; });
    $('ls-note').innerHTML = done ? `One stored record of this scenario. ${lines.join(' · ')}.`
      : `Replaying one stored record of this scenario: second <b>${Math.floor(t)}</b> of ${T}. The step is ${L.step_hz} Hz; the atoms’ readings scatter by about a whole hertz.`;
  }

  // ------------------------------------------------------------------ scene 9: printing fine stripes on a resist
  // A live run of the exposure study's own model at its saved operating points: lab/test_research.cjs holds
  // RM.exposure and RM.printQuality to quantum_lithography_poc/exposure_followup/results.json.
  const EXPOSE_MS = 4400, HOLD = 0.36, LIGHTS = { 'cp-noon': 'noon', 'cp-cycled': 'phase_cycled', 'cp-duty': 'phase_cycled_burst' };
  const LIGHT_NAME = { noon: 'Entangled pairs', phase_cycled: 'Laser, two shifted exposures', phase_cycled_burst: 'Laser, short pulses' };
  const cp = { method: 'noon', u: 0, hold: 0, shot: null, shots: 0, right: 0, scored: 0, perfect: 0, means: [], guard: [], exact: null };
  const millions = v => `${(v / 1e6).toFixed(v >= 9.95e6 ? 1 : 2)} M`;
  function setChipLight(method) {
    const clocks = RS.chips.methods[method].photons / (2 * RM.EXPOSURE.arm);
    Object.assign(cp, { method, u: 0, hold: 0, shot: null, shots: 0, right: 0, scored: 0, perfect: 0 });
    cp.coefficients = RM.exposure(method);
    cp.means = RM.cellMeans(cp.coefficients, clocks, RM.EXPOSURE.cells);
    cp.guard = RM.guardCells(RM.EXPOSURE.cells);
    cp.exact = RM.printQuality(cp.means, RS.chips.threshold_events);
    for (const id of Object.keys(LIGHTS)) $(id).setAttribute('aria-pressed', LIGHTS[id] === method);
    renderChips();
  }
  function newExposure() {
    // each cell's events arrive at random moments of the exposure: draw how many, then when
    cp.shot = { arrivals: cp.means.map(mean => Array.from({ length: RM.poisson(mean, random) }, () => random()).sort((a, b) => a - b)), right: null };
    cp.u = 0; cp.hold = 0;
  }
  function scoreExposure() {
    const threshold = RS.chips.threshold_events; let ok = 0, n = 0;
    cp.shot.arrivals.forEach((a, j) => { if (!cp.guard[j]) return; n++; if ((a.length >= threshold) === (cp.guard[j] > 0)) ok++; });
    cp.shot.right = ok; cp.shots++; cp.right += ok; cp.scored += n; if (ok === n) cp.perfect++;
  }
  function advanceChips(dt) {
    if (state.paused) return;
    let budget = dt * state.speed / EXPOSE_MS, guard = 0;
    while (budget > 1e-9 && guard++ < 400) {
      if (!cp.shot) newExposure();
      if (cp.u < 1) { const used = Math.min(1 - cp.u, budget); cp.u += used; budget -= used; if (cp.u >= 1) scoreExposure(); }
      else { const used = Math.min(HOLD - cp.hold, budget); cp.hold += used; budget -= used; if (cp.hold >= HOLD - 1e-9) cp.shot = null; }
    }
  }
  function renderChips() {
    const D = RS.chips, body = document.querySelector('#cp-table tbody'); body.replaceChildren();
    for (const key of ['noon', 'phase_cycled', 'phase_cycled_burst']) {
      const d = D.methods[key], tr = document.createElement('tr');
      if (key === cp.method) tr.className = 'on';
      [LIGHT_NAME[key], pct(d.cell_accuracy, 1), pct(d.all_correct, 1), millions(d.photons)].forEach(t => { const td = document.createElement('td'); td.textContent = t; tr.append(td); });
      body.append(tr);
    }
    const q = D.full_query;
    $('cp-qubits').textContent = String(q.qubits); $('cp-device').textContent = `the chip we used has ${q.device_qubits}`;
    $('cp-gates').textContent = millions(Math.max(q.cx_upper_bound.floor, q.cx_upper_bound.ceil));
    $('cp-gates-note').textContent = `an upper bound · our best run used ${DATA.hero.precision.local.two_qubit_gates}`;
    $('cp-event').textContent = `The rare event: a contact fails to print in ${pct(q.event_probability.floor, 2)} of exposures of a ${q.cells}-cell model. `
      + `Amplifying it takes ${q.count_qubits} counting qubits, ${q.score_qubits} for the score and ${q.clean_qubits} spare. A classical computer already solves this model.`;
    $('cp-branch').textContent = pct(D.phase.noon.wrong_branch, 1);
    $('cp-phase').textContent = `Adding a 10% laser pilot fixes it: error ${D.phase.hybrid.rmse_rad.toFixed(4)} rad, against ${D.phase.coherent.rmse_rad.toFixed(4)} for laser light alone.`;
  }
  function drawChips() {
    const { ctx, W, H, m, detail } = stage($('chips-canvas'));
    const M = RM.EXPOSURE.cells, T = RS.chips.threshold_events, shot = cp.shot, u = shot ? cp.u : 0, done = shot && cp.u >= 1;
    const fs = v => Math.max(10, v * clamp(m, 0.85, 1.2));
    const mx = Math.max(54, W * 0.075), x0 = mx, cw = (W - 2 * mx) / M, gap = Math.min(3, cw * 0.14);
    const top = detail ? 46 : 30, lightH = clamp(H * 0.13, 30, 86), rows = detail ? 64 : 50;
    const yBase = H - rows - 8, yTop = top + lightH + (detail ? 40 : 24), full = 46;
    const yOf = n => yBase - Math.min(n, full) / full * (yBase - yTop);
    const peak = Math.max(...cp.means), [c0, , c2] = cp.coefficients;
    // the light on the resist: two fine stripes across one period of the crossed beams
    for (let j = 0; j < M; j++) {
      const v = cp.means[j] / peak, x = x0 + j * cw, g = ctx.createLinearGradient(0, top, 0, top + lightH);
      g.addColorStop(0, rgba(C.cyan, 0.04 + 0.7 * v * v * v)); g.addColorStop(1, rgba(C.cyan, 0.02 + 0.2 * v * v * v));
      ctx.fillStyle = g; ctx.fillRect(x + 0.5, top, cw - 1, lightH);
    }
    ctx.beginPath();
    for (let i = 0; i <= 240; i++) {
      const phi = 2 * Math.PI * (i / 240 * M - 0.5) / M, v = (c0 + c2 * Math.cos(2 * phi)) / (c0 + c2);
      const x = x0 + i / 240 * M * cw, y = top + lightH * (1 - 0.92 * v);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.strokeStyle = rgba(C.ink, 0.85); ctx.lineWidth = 1.6; ctx.stroke();
    caps(ctx, detail ? 'LIGHT ON THE RESIST · ONE 800 NM PERIOD OF THE CROSSED BEAMS' : 'LIGHT ON THE RESIST', x0, top - 10, { align: 'left', size: fs(11) });
    text(ctx, `stripe contrast ${pct(c2 / c0, 0)}`, x0 + M * cw, top - 10, { align: 'right', size: fs(12), color: C.cyan, mono: true });
    // the columns: events collected so far in each cell
    line(ctx, x0 - 6, yBase, x0 + M * cw + 6, yBase, C.line2, 1.2);
    for (const n of [0, 20, 40]) text(ctx, String(n), x0 - 12, yOf(n) + 4, { align: 'right', size: fs(11), mono: true });
    if (detail) { ctx.save(); ctx.translate(x0 - mx * 0.72, (yBase + yTop) / 2); ctx.rotate(-Math.PI / 2); caps(ctx, 'EVENTS IN EACH CELL', 0, 0, { size: fs(10.5) }); ctx.restore(); }
    for (let j = 0; j < M; j++) {
      const arrivals = shot ? shot.arrivals[j] : [], x = x0 + j * cw + gap / 2, w = cw - gap;
      let count = 0; while (count < arrivals.length && arrivals[count] <= u) count++;
      const printed = count >= T, g = cp.guard[j];
      if (shot && u < 1) for (let k = count; k < arrivals.length && arrivals[k] <= u + 0.05; k++) {      // events on their way down
        const f = 1 - (arrivals[k] - u) / 0.05;
        ctx.beginPath(); ctx.arc(x + w * (0.25 + 0.5 * ((k * 0.618) % 1)), lerp(top + lightH, yOf(count), f), 1.7, 0, 2 * Math.PI); ctx.fillStyle = rgba(C.cyan, 0.9); ctx.fill();
      }
      box(ctx, x, yOf(count), w, Math.max(yBase - yOf(count), 1), Math.min(3, w / 3), printed ? rgba(C.amber, 0.88) : rgba(g ? C.cyan : C.blue, g ? 0.5 : 0.24), null);
      // what was wanted, and what printed
      const r1 = yBase + 12, r2 = yBase + (detail ? 36 : 30), s = Math.min(w, 15), sx = x + (w - s) / 2;
      if (g > 0) box(ctx, sx, r1, s, s, 3, rgba(C.amber, 0.55), null); else if (g < 0) box(ctx, sx, r1, s, s, 3, null, C.line2, 1.2);
      else { ctx.beginPath(); ctx.arc(x + w / 2, r1 + s / 2, 1.6, 0, 2 * Math.PI); ctx.fillStyle = C.line2; ctx.fill(); }
      const wrong = done && g && printed !== (g > 0);
      box(ctx, sx, r2, s, s, 3, printed ? C.amber : null, wrong ? C.red : printed ? C.amber : C.line2, wrong ? 2.2 : 1.2);
      if (wrong) { line(ctx, sx - 2, r2 - 2, sx + s + 2, r2 + s + 2, C.red, 1.8); line(ctx, sx + s + 2, r2 - 2, sx - 2, r2 + s + 2, C.red, 1.8); }
    }
    ctx.setLineDash([6, 5]); line(ctx, x0 - 6, yOf(T), x0 + M * cw + 6, yOf(T), rgba(C.ink, 0.8), 1.4); ctx.setLineDash([]);
    text(ctx, `prints at ${T}`, x0 + M * cw + 10, yOf(T) + 4, { size: fs(11.5), color: C.ink });
    text(ctx, 'wanted', x0 - 12, yBase + 24, { align: 'right', size: fs(11) });
    text(ctx, 'printed', x0 - 12, yBase + (detail ? 48 : 42), { align: 'right', size: fs(11) });
    // the running cost, and the verdict on this exposure
    const photons = RS.chips.methods[cp.method].photons;
    text(ctx, `${millions(photons * u)} photons`, x0 + M * cw, top + lightH + (detail ? 26 : 18), { align: 'right', size: fs(15), mono: true, color: C.soft });
    if (done) {
      const n = cp.guard.filter(Boolean).length, perfect = shot.right === n;
      text(ctx, perfect ? `all ${n} scored cells right` : `${shot.right} of ${n} scored cells right`, x0, top + lightH + (detail ? 26 : 18), { size: fs(15), weight: 600, color: perfect ? C.green : C.red });
    } else text(ctx, `exposure ${comma(cp.shots + 1)}`, x0, top + lightH + (detail ? 26 : 18), { size: fs(13), mono: true });
    $('cp-note').innerHTML = cp.shots
      ? `<b>${comma(cp.shots)}</b> exposure${cp.shots === 1 ? '' : 's'} so far: <b>${pct(cp.right / cp.scored, 1)}</b> of scored cells right, <b>${comma(cp.perfect)}</b> perfect. `
        + `Exact for this light and dose: ${pct(cp.exact.accuracy, 1)} of cells, ${pct(cp.exact.allCorrect, 1)} perfect. The 12 cells on stripe edges are not scored.`
      : `Every exposure is a fresh random draw from the study’s model. Exact for this light and dose: ${pct(cp.exact.accuracy, 1)} of scored cells right, ${pct(cp.exact.allCorrect, 1)} of exposures perfect.`;
  }

  // ------------------------------------------------------------------ frame loop
  let last = performance.now(), manual = false, clock = 0;
  function frame(now) {
    if (manual) return;
    const dt = Math.min(now - last, 120); last = now;
    render(dt, now);
    requestAnimationFrame(frame);
  }
  function render(dt, now) {
    advanceTour(dt);
    advance(dt);
    if (bench.parentNode) drawBench(now);
    if (state.scene === 'signal') drawRates();
    else if (state.scene === 'machine') updateMachine();
    else if (state.scene === 'question') { drawRaster(); updateTally(); }
    else if (state.scene === 'rewind') { advanceAmp(dt); drawAmp(); }
    else if (state.scene === 'answer') drawAnswer();
    else if (state.scene === 'photons') { advancePhotons(dt); drawPhotons(now); }
    else if (state.scene === 'lasers') { advanceLasers(dt); drawLasers(now); }
    else if (state.scene === 'chips') { advanceChips(dt); drawChips(); }
    else if (state.scene === 'hardware') {
      if (hw.u < 1) hw.u = Math.min(1, hw.u + dt / 1100);
      drawShots('shots-local', DATA.hero[hw.run].local, C.cyan, DATA.noise_model.local.echo_scaled.hit_rate);
      drawShots('shots-full', DATA.hero[hw.run].full, C.amber, DATA.noise_model.full.echo_scaled.hit_rate);
    }
  }
  function drawStatic() { if (state.scene === 'rewind') { renderAmpText(); } }

  // ------------------------------------------------------------------ scenes, tour, controls
  function show(id, fromTour) {
    if (!SCENES.includes(id)) id = 'signal';
    if (!fromTour) stopTour();
    state.scene = id;
    document.querySelectorAll('.scene').forEach(s => { s.hidden = s.id !== id; });
    document.querySelectorAll('.scenes button').forEach(b => b.setAttribute('aria-current', b.dataset.scene === id));
    const i = SCENES.indexOf(id);
    $('prev').disabled = i === 0; $('next').textContent = i === SCENES.length - 1 ? 'Start over ↺' : 'Next →';
    $('scope-line').textContent = SCOPE[RESEARCH_TABS.includes(id) ? 1 : 0];
    mountBench();
    if (id === 'rewind') { computeAmp(); stopAmp(); setStage(0, false); if (fromTour) { playAmp(); amp.rate = 1.7; } }
    if (id === 'answer') renderAnswerNumbers();
    if (id === 'hardware') renderHardware();
    if (id === 'photons') setPhotonSource(fromTour ? 'shared' : ph.mode);
    if (id === 'lasers') setLaserScenario(fromTour ? 'nominal' : ls.scenario);
    if (id === 'chips') setChipLight(fromTour ? 'phase_cycled' : cp.method);
    try { history.replaceState(null, '', '#' + id); } catch (e) { /* file:// in some browsers */ }
    window.scrollTo({ top: 0 });
  }
  const step = d => { const i = SCENES.indexOf(state.scene) + d; show(SCENES[(i + SCENES.length) % SCENES.length]); };
  function fastForward(n) { for (let i = 0; i < n; i++) record(E.sampleRun(model, T, random, K).bits); }

  // The full tour adds the three research tabs. The core tour is the 45-second version for a tight talk.
  const TOURS = {
    full: [['signal', 6], ['machine', 6], ['question', 7], ['rewind', 9], ['answer', 6], ['hardware', 7],
           ['photons', 8], ['lasers', 8], ['chips', 9], ['impact', 4]],
    core: [['signal', 6], ['machine', 6], ['question', 7], ['rewind', 9], ['answer', 6], ['hardware', 7], ['impact', 4]],
  };
  let TOUR = TOURS.full;
  const tourSeconds = kind => (TOURS[kind] || TOURS.full).reduce((s, x) => s + x[1], 0);
  const tourLabel = on => (on ? '■ Stop tour' : `▶ <i class="long">${tourSeconds('full')} s tour</i><i class="short">Tour</i>`);
  // one beat per scene, at a time in seconds after the scene opens
  const BEATS = {
    signal: [[3.2, () => setReveal(true)]],
    question: [[2.4, () => fastForward(3000)]],
    photons: [[2.8, () => setPhotonSource('independent')]],
    chips: [[4.4, () => setChipLight('noon')]],
    answer: [[0, () => setPhi(0)], [1.0, t => setPhi(Math.min(DEFAULT_PHI, DEFAULT_PHI * (t - 1.0) / 2.6)), 3.7], [3.7, () => setPhi(DEFAULT_PHI)]],
  };
  function startTour(kind) {
    TOUR = TOURS[kind] || TOURS.full;
    state.tour = { i: 0, t: 0, done: 0 }; $('tour').innerHTML = tourLabel(true); $('tour').setAttribute('aria-pressed', 'true');
    if (!state.defect || state.phi !== DEFAULT_PHI) { state.defect = true; setPhi(DEFAULT_PHI); }
    setReveal(false); setSpeed(4); state.paused = false; show(TOUR[0][0], true);
  }
  function stopTour() {
    if (!state.tour) return;
    state.tour = null; $('tour').innerHTML = tourLabel(false); $('tour').setAttribute('aria-pressed', 'false'); $('progress-bar').style.width = '0';
  }
  function advanceTour(dt) {
    const tour = state.tour; if (!tour) return;
    tour.t += dt / 1000;
    const total = TOUR.reduce((s, x) => s + x[1], 0), before = TOUR.slice(0, tour.i).reduce((s, x) => s + x[1], 0);
    $('progress-bar').style.width = pct(Math.min(1, (before + tour.t) / total), 2);
    const beats = BEATS[TOUR[tour.i][0]] || [];
    beats.forEach((beat, n) => {
      const [at, run, until] = beat;
      if (until !== undefined) { if (tour.t >= at && tour.t < until) run(tour.t); }      // a continuous beat
      else if (tour.t >= at && !(tour.done & (1 << n))) { tour.done |= 1 << n; run(tour.t); }
    });
    if (tour.t >= TOUR[tour.i][1]) {
      tour.i++; tour.t = 0; tour.done = 0;
      if (tour.i >= TOUR.length) stopTour(); else show(TOUR[tour.i][0], true);
    }
  }
  function setPhi(v) {
    state.phi = v; $('phi').value = v; answer.sampled = null;
    const scene = state.scene; rebuildModel(); if (scene === 'answer') renderAnswerNumbers();
  }
  function setSpeed(v) {
    state.speed = v;
    document.querySelectorAll('.speed button[data-speed]').forEach(b => b.setAttribute('aria-pressed', +b.dataset.speed === v));
  }
  function setLevel(level) {
    state.level = level;
    document.body.classList.toggle('level-plain', level === 'plain'); document.body.classList.toggle('level-tech', level === 'tech');
    $('level-plain').setAttribute('aria-pressed', level === 'plain'); $('level-tech').setAttribute('aria-pressed', level === 'tech');
    renderAmpText();
  }
  function setReveal(v) {
    state.reveal = v; $('toggle-reveal').setAttribute('aria-pressed', v);
    $('toggle-reveal').textContent = v ? 'Hide it again' : 'Reveal what’s hidden';
  }

  document.querySelectorAll('.scenes button').forEach(b => b.addEventListener('click', () => show(b.dataset.scene)));
  $('prev').addEventListener('click', () => step(-1)); $('next').addEventListener('click', () => step(1));
  $('tour').addEventListener('click', () => (state.tour ? stopTour() : startTour()));
  $('level-plain').addEventListener('click', () => setLevel('plain')); $('level-tech').addEventListener('click', () => setLevel('tech'));
  $('toggle-defect').addEventListener('click', () => { state.defect = !state.defect; rebuildModel(); });
  $('toggle-reveal').addEventListener('click', () => setReveal(!state.reveal));
  document.querySelectorAll('.speed button[data-speed]').forEach(b => b.addEventListener('click', () => setSpeed(+b.dataset.speed)));
  $('pause').addEventListener('click', () => { state.paused = !state.paused; $('pause').setAttribute('aria-pressed', state.paused); $('pause').textContent = state.paused ? '▶' : '❚❚'; });
  $('sound').addEventListener('click', () => { state.sound = !state.sound; $('sound').setAttribute('aria-pressed', state.sound); $('sound').textContent = state.sound ? '♪ on' : '♪ off'; if (state.sound) tick(); });
  $('ff').addEventListener('click', () => fastForward(5000));
  $('reset-runs').addEventListener('click', () => { resetStats(); resetRun(); });
  document.querySelectorAll('#stages button').forEach(b => b.addEventListener('click', () => { stopAmp(); setStage(+b.dataset.stage, true); }));
  $('amp-play').addEventListener('click', () => (amp.playing ? stopAmp() : playAmp()));
  $('amp-steer').addEventListener('click', () => { amp.steer = !amp.steer; $('amp-steer').setAttribute('aria-checked', amp.steer); computeAmp(); stopAmp(); setStage(amp.stage, false); });
  const setReflection = kind => {
    amp.reflection = kind; $('amp-full').setAttribute('aria-pressed', kind === 'full'); $('amp-local').setAttribute('aria-pressed', kind !== 'full');
    computeAmp(); stopAmp(); setStage(amp.stage, false);
  };
  $('amp-full').addEventListener('click', () => setReflection('full')); $('amp-local').addEventListener('click', () => setReflection('memory+last-1'));
  $('phi').addEventListener('input', () => { state.defect = true; setPhi(+$('phi').value); });
  $('phi-reset').addEventListener('click', () => setPhi(DEFAULT_PHI));
  $('ans-sample').addEventListener('click', sampleAnswer);
  $('show-ibm').addEventListener('change', () => { answer.ibm = $('show-ibm').checked; renderAnswerNumbers(); });
  $('hw-precision').addEventListener('click', () => { hw.run = 'precision'; renderHardware(); });
  $('hw-first').addEventListener('click', () => { hw.run = 'first'; renderHardware(); });
  $('hw-supp').addEventListener('click', () => { hw.run = 'suppressed'; renderHardware(); });
  $('ph-shared').addEventListener('click', () => setPhotonSource('shared')); $('ph-indep').addEventListener('click', () => setPhotonSource('independent'));
  for (const id of Object.keys(SCENARIOS)) $(id).addEventListener('click', () => setLaserScenario(SCENARIOS[id]));
  for (const id of Object.keys(LIGHTS)) $(id).addEventListener('click', () => setChipLight(LIGHTS[id]));
  window.addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); step(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); step(-1); }
    else if (e.key >= '1' && e.key <= '9') show(SCENES[+e.key - 1]);
    else if (e.key === '0') show(SCENES[9]);
    else if (e.key === 't' || e.key === 'T') setLevel(state.level === 'plain' ? 'tech' : 'plain');
    else if (e.key === 'r' || e.key === 'R') setReveal(!state.reveal);
    else if (e.key === 'd' || e.key === 'D') { state.defect = !state.defect; rebuildModel(); }
    else if (e.key === ' ' && e.target.tagName !== 'BUTTON') { e.preventDefault(); $('pause').click(); }
  });
  window.addEventListener('hashchange', () => { const id = location.hash.slice(1); if (id && id !== state.scene) show(id); });
  // a scene id in the address would otherwise make the browser scroll past the header on a small screen
  window.addEventListener('load', () => setTimeout(() => window.scrollTo(0, 0), 0));

  // ------------------------------------------------------------------ go
  const query = new URLSearchParams(location.search);
  if (query.get('seed')) source = E.seeded(+query.get('seed'));
  if (query.get('capture') === '1') document.body.classList.add('capture');
  setLevel(query.get('level') === 'tech' ? 'tech' : 'plain');
  rebuildModel();
  if (query.get('reveal') === '1') setReveal(true);
  // deep links into the research tabs: ?source=independent, ?scenario=shared_path, ?light=phase_cycled
  if (query.get('source') === 'independent') ph.mode = 'independent';
  if (Object.values(SCENARIOS).includes(query.get('scenario'))) ls.scenario = query.get('scenario');
  if (Object.values(LIGHTS).includes(query.get('light'))) cp.method = query.get('light');
  if (query.get('speed')) setSpeed(clamp(+query.get('speed') || 1, 1, 20));
  show(location.hash.slice(1) || 'signal');
  if (query.get('runs')) fastForward(clamp(+query.get('runs') || 0, 0, 200000));
  if (query.get('stage')) setStage(+query.get('stage'), false);
  if (query.get('tour')) startTour(query.get('tour') === 'core' ? 'core' : 'full');
  window.LAB = {
    state, stats, sim, amp, hw, ph, ls, cp, show, fastForward, startTour, setReveal, setPhi, model: () => model,
    /** Stop the real-time loop; frames then advance only through tick(ms). Used to record the tour frame by frame. */
    manual() { manual = true; clock = 0; },
    tick(ms) { clock += ms; render(ms, clock); },
    tourLength: kind => tourSeconds(kind || 'full'),
  };
  requestAnimationFrame(frame);
})();
