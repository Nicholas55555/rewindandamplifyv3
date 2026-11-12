// Exercise the actual offline page script with a minimal DOM, without a server.
// Rendering and keyboard accessibility still require a real-browser check.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(id = '') { this.id = id; this.value = ''; this.textContent = ''; this.className = ''; this.style = {}; this.children = []; this.listeners = {}; }
  replaceChildren(...children) { this.children = children; }
  appendChild(child) { this.children.push(child); }
  addEventListener(event, callback) { this.listeners[event] = callback; }
  fire(event) { assert.ok(this.listeners[event], `${this.id} has ${event} listener`); this.listeners[event](); }
}
const elements = new Map();
const get = id => { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); };
get('p').value = '80';
get('rounds').value = '1';
const document = {getElementById: get, createElement: () => new Element()};
const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(script, 'page contains its local script');
for (const file of ['spatial_demo.png', 'dose_sweep.png', 'viability_cost_tradeoff.png']) {
  assert.ok(fs.existsSync(path.join(__dirname, file)), `local figure ${file} is present`);
  assert.ok(html.includes(`src="${file}"`), `local figure ${file} is referenced`);
}
vm.runInNewContext(script[1], {document, Math, Array, Number, String});

function exactFailure(p) {
  let total = 0;
  for (let mask = 0; mask < 32; mask++) {
    let k = 0;
    for (let i = 0; i < 5; i++) k += (mask >> i) & 1;
    if (k < 2) total += p ** k * (1 - p) ** (5 - k);
  }
  return total;
}
function readPercent(id) { return parseFloat(get(id).textContent) / 100; }
function check(p, rounds) {
  get('p').value = String(100 * p);
  get('rounds').value = String(rounds);
  get('rounds').fire('input');
  const failure = exactFailure(p);
  const amp = Math.sin((2 * rounds + 1) * Math.asin(Math.sqrt(failure))) ** 2;
  assert.ok(Math.abs(readPercent('direct') - failure) <= 0.00051, 'displayed direct probability');
  assert.ok(Math.abs(readPercent('amp') - amp) <= 0.00051, 'displayed ideal quantum probability');
  assert.ok(Math.abs(readPercent('proposal') - exactFailure(.3)) <= 0.00051, 'displayed fixed proposal probability');
  assert.equal(get('directDots').children.length, 96);
  assert.equal(get('ampDots').children.length, 96);
}
check(.8, 1);
assert.equal(get('direct').textContent, '0.672%');
assert.equal(get('amp').textContent, '5.94%');
check(.8, 9);
assert.equal(get('amp').textContent, '99.987%');
for (const p of [.6, .75, .8, .95]) for (const rounds of [0, 1, 3, 9, 12]) check(p, rounds);
get('resample').fire('click');
assert.equal(get('cells').children.length, 5);
console.log('Offline page logic passed: probability parity, rounding, controls, and local figure.');
