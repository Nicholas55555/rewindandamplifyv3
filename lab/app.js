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
  const SCENES = ['signal', 'machine', 'question', 'rewind', 'answer', 'hardware', 'impact'];
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
    const m = clamp(W / 1250, 0.74, 1.3);                               // element scale
    const ts = clamp(W / Math.max(area.width, 1), 1, 1.55);             // keeps labels near 12 px on screen
    const detail = area.width >= 900;
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
  function drawShots(id, row, color) {
    const { ctx, w, h } = fit($(id));
    const rows = row.shots > 4096 ? 32 : 16, cols = row.shots / rows, cw = w / cols, chh = h / rows, lit = Math.round(row.accepted * ease(hw.u));
    ctx.fillStyle = rgba(C.blue, 0.13);
    for (let i = 0; i < row.shots; i++) { const c = Math.floor(i / rows), r = i % rows; ctx.fillRect(c * cw + 0.3, r * chh + 0.3, cw - 0.6, chh - 0.6); }
    ctx.fillStyle = color;
    for (let i = 0; i < lit; i++) { const c = Math.floor(i / rows), r = i % rows; ctx.fillRect(c * cw + 0.3, r * chh + 0.3, cw - 0.6, chh - 0.6); }
    const ix = row.ideal_probability * w;
    line(ctx, ix, 0, ix, h, C.ink, 1.5);
    text(ctx, `ideal ${pct(row.ideal_probability, 1)}`, ix - 6, 13, { align: 'right', size: 11, color: C.ink, mono: true });
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
    advance(dt);
    if (bench.parentNode) drawBench(now);
    if (state.scene === 'signal') drawRates();
    else if (state.scene === 'machine') updateMachine();
    else if (state.scene === 'question') { drawRaster(); updateTally(); }
    else if (state.scene === 'rewind') { advanceAmp(dt); drawAmp(); }
    else if (state.scene === 'answer') drawAnswer();
    else if (state.scene === 'hardware') {
      if (hw.u < 1) hw.u = Math.min(1, hw.u + dt / 1100);
      drawShots('shots-local', DATA.hero[hw.run].local, C.cyan); drawShots('shots-full', DATA.hero[hw.run].full, C.amber);
    }
    advanceTour(dt);
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
    mountBench();
    if (id === 'rewind') { computeAmp(); stopAmp(); setStage(0, false); if (fromTour) { playAmp(); amp.rate = 1.7; } }
    if (id === 'answer') renderAnswerNumbers();
    if (id === 'hardware') renderHardware();
    try { history.replaceState(null, '', '#' + id); } catch (e) { /* file:// in some browsers */ }
    window.scrollTo({ top: 0 });
  }
  const step = d => { const i = SCENES.indexOf(state.scene) + d; show(SCENES[(i + SCENES.length) % SCENES.length]); };
  function fastForward(n) { for (let i = 0; i < n; i++) record(E.sampleRun(model, T, random, K).bits); }

  const TOUR = [['signal', 6], ['machine', 6], ['question', 7], ['rewind', 9], ['answer', 6], ['hardware', 7], ['impact', 4]];
  // one beat per scene, at a time in seconds after the scene opens
  const BEATS = {
    signal: [[3.2, () => setReveal(true)]],
    question: [[2.4, () => fastForward(3000)]],
    answer: [[0, () => setPhi(0)], [1.0, t => setPhi(Math.min(DEFAULT_PHI, DEFAULT_PHI * (t - 1.0) / 2.6)), 3.7], [3.7, () => setPhi(DEFAULT_PHI)]],
  };
  function startTour() {
    state.tour = { i: 0, t: 0, done: 0 }; $('tour').textContent = '■ Stop tour'; $('tour').setAttribute('aria-pressed', 'true');
    if (!state.defect || state.phi !== DEFAULT_PHI) { state.defect = true; setPhi(DEFAULT_PHI); }
    setReveal(false); setSpeed(4); state.paused = false; show(TOUR[0][0], true);
  }
  function stopTour() {
    if (!state.tour) return;
    state.tour = null; $('tour').textContent = '▶ 45 s tour'; $('tour').setAttribute('aria-pressed', 'false'); $('progress-bar').style.width = '0';
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
  window.addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); step(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); step(-1); }
    else if (e.key >= '1' && e.key <= '7') show(SCENES[+e.key - 1]);
    else if (e.key === 't' || e.key === 'T') setLevel(state.level === 'plain' ? 'tech' : 'plain');
    else if (e.key === 'r' || e.key === 'R') setReveal(!state.reveal);
    else if (e.key === 'd' || e.key === 'D') { state.defect = !state.defect; rebuildModel(); }
    else if (e.key === ' ' && e.target.tagName !== 'BUTTON') { e.preventDefault(); $('pause').click(); }
  });
  window.addEventListener('hashchange', () => { const id = location.hash.slice(1); if (id && id !== state.scene) show(id); });

  // ------------------------------------------------------------------ go
  const query = new URLSearchParams(location.search);
  if (query.get('seed')) source = E.seeded(+query.get('seed'));
  if (query.get('capture') === '1') document.body.classList.add('capture');
  setLevel(query.get('level') === 'tech' ? 'tech' : 'plain');
  rebuildModel();
  if (query.get('reveal') === '1') setReveal(true);
  if (query.get('speed')) setSpeed(clamp(+query.get('speed') || 1, 1, 20));
  show(location.hash.slice(1) || 'signal');
  if (query.get('runs')) fastForward(clamp(+query.get('runs') || 0, 0, 200000));
  if (query.get('stage')) setStage(+query.get('stage'), false);
  if (query.get('tour') === '1') startTour();
  window.LAB = {
    state, stats, sim, amp, hw, show, fastForward, startTour, setReveal, setPhi, model: () => model,
    /** Stop the real-time loop; frames then advance only through tick(ms). Used to record the tour frame by frame. */
    manual() { manual = true; clock = 0; },
    tick(ms) { clock += ms; render(ms, clock); },
    tourLength: () => TOUR.reduce((s, x) => s + x[1], 0),
  };
  requestAnimationFrame(frame);
})();
