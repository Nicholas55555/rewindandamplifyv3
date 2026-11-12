"""Write and execute notebooks/walkthrough.ipynb: the whole idea, in about a dozen short cells.

    python tools/make_notebook.py
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]

CELLS = [
    ("md", """# Rewind & Amplify: a walkthrough

Grover's algorithm inside a quantum recurrent state machine (QRSM), in about a dozen cells. Every number here comes from a Qiskit circuit. It takes under a minute and needs no account.

**The problem.** A QRSM emits a click, or no click, at each step. To study a rare event you normally run it again and again and discard the runs that don't match.

**The plan.** Purify the machine so it can be rewound. Steer it so the event is common. Amplify locally. Verify by measuring."""),
    ("code", """import logging
import sys
sys.path.insert(0, "..")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import numpy as np
from qiskit.quantum_info import Statevector

from qrsm_grover import QRSM, any_click, click_at, conditional_distribution, success_probability, total_variation
from qrsm_grover.amplify import amplified, hardware_amplified, steered_gamma
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits

machine = QRSM()   # a driven emitter, one hidden defect, and a light that clicks
T = 6
print(machine)"""),
    ("md", """## 1. The dynamic machine: measured and reset every step

This is the QRSM as it runs on a device. One light qubit, measured mid-circuit and reset. Here are two steps of it. A reset throws information away, so this circuit has no inverse, and Grover can't use it."""),
    ("code", """machine.dynamic(2).draw("mpl", fold=-1, scale=0.6)"""),
    ("md", """## 2. Move 1: purify

Give every step a fresh light and measure nothing until the end. The click statistics can't change, and the whole run is now one reversible circuit A. Its state holds every click history at once:

$$A|0\\rangle = \\sum_y |m_y\\rangle |y\\rangle, \\qquad \\langle m_y | m_y \\rangle = P(y)$$

So it should equal the exact model's branches, amplitude by amplitude."""),
    ("code", """A = machine.purified(T)
n = machine.n_memory
state = Statevector(A).data.reshape(2 ** T, 2 ** n)
print("qubits:", A.num_qubits)
print("largest amplitude difference from the exact model:", np.abs(state - machine.branches(T)).max())"""),
    ("md", """## 3. Grover on the machine's histories

The question: a click at step 6. Qiskit's own `grover_operator` builds each iteration from A and an oracle, and the circuit follows the textbook curve $P_r = \\sin^2((2r+1)\\theta)$."""),
    ("code", """question = click_at(T)
mask = question.mask(T)
probs = machine.history_probabilities(T)
p = probs[mask].sum()
oracle = question.oracle(n + T, list(range(n, n + T)))
print(f"p = {p:.4f}")
for r in range(4):
    d = (np.abs(Statevector(amplified(A, oracle, r)).data) ** 2).reshape(2 ** T, 2 ** n).sum(axis=1)
    print(f"r = {r}: hit rate {d[mask].sum():.4f}   theory {success_probability(p, r):.4f}   "
          f"distance from the exact conditional {total_variation(conditional_distribution(d, mask), conditional_distribution(probs, mask)):.1e}")"""),
    ("md", """The last column is the important one. Amplification reweights without reshaping: inside the matching histories the relative odds never change. So an amplified shot is an exact conditional sample.

## 4. Move 2: steer

A click's Kraus operator is $\\sin\\alpha\\, |0\\rangle\\langle 1|$ on the emitter. So turning up the emission at that step scales every history that clicks there by the same constant. The conditional answer can't change, and the chance can be set to exactly 1/4, where one iteration gives certainty."""),
    ("code", """steer = steered_gamma(p, machine.gamma)
print(f"steered emission at step {T}: {machine.gamma} -> {steer:.3f}")
K1, K1_steered = machine.kraus()[1], machine.kraus(gamma=steer)[1]
print("K1 scales by a constant:", np.abs(K1_steered - np.sqrt(steer / machine.gamma) * K1).max() < 1e-12)

fast = FastPurified(machine, T, [None] * (T - 1) + [steer])
d = light_distribution(dict(fast.amplify(mask, 1, None))[1], T, fast.dim)
print(f"one iteration: hit rate {d[mask].sum():.6f}, distance from the exact conditional "
      f"{total_variation(conditional_distribution(d, mask), conditional_distribution(probs, mask)):.1e}")"""),
    ("md", """## 5. Move 3: amplify locally

The reflection in Grover checks every qubit, and that gate grows with the record. We watch only the memory and the one light the question reads: 3 qubits, at any length. `reflection_qubits` names the choices, and Qiskit's `grover_operator` accepts them directly."""),
    ("code", """for kind in ("full", "memory", "memory+last-1"):
    rq = reflection_qubits(machine, T, kind)
    d = light_distribution(dict(fast.amplify(mask, 1, rq))[1], T, fast.dim)
    print(f"{kind:14s} watches {len(rq):2d} qubits: hit rate {d[mask].sum():.3f}, distance {total_variation(conditional_distribution(d, mask), conditional_distribution(probs, mask)):.3f}")"""),
    ("md", """## 6. On an IBM device model

Now compile for a real device layout and simulate its noise. This is what the resilient build buys: far fewer two-qubit gates, so better answers. The textbook build at its best r is on the left, and the resilient build on the right. (T = 3 here, so this takes seconds.)"""),
    ("code", """from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import fake_provider
from qrsm_grover.hardware import compile_best, history_experiment

backend = fake_provider.FakeKingston()
sim = AerSimulator.from_backend(backend)
T3 = 3
q3 = click_at(T3)
m3 = q3.mask(T3)
p3 = machine.history_probabilities(T3)[m3].sum()
builds = [("textbook, r = 3", history_experiment("t", machine, T3, q3, "full", 3)),
          ("steer + local, r = 1", history_experiment("s", machine, T3, q3, "memory+last-1", 1, steered_gamma(p3, machine.gamma)))]
for name, exp in builds:
    isa, info = compile_best(exp.circuit, backend, seeds=3)
    counts = sim.run(isa, shots=8192, seed_simulator=7).result().get_counts()
    hit = sum(c for bits, c in counts.items() if (int(bits, 2) >> (n + T3 - 1)) & 1) / 8192
    print(f"{name:22s} {info['two_qubit_gates']:3d} two-qubit gates, hit rate {hit:.3f}")"""),
    ("md", """## Where to go next

- `demo/demo.py`: the one-minute demo, including the keyword search.
- `demo/index.html`: an interactive lab.
- `docs/REPORT.md`: every result, with what we got wrong.
- `experiments/run_ibm.py`: run this on real IBM hardware with your own account.

At this size a classical sampler beats all of this. The report says why it could still matter at larger memories, and what we don't claim."""),
]


def main() -> None:
    nb = new_notebook()
    for kind, text in CELLS:
        nb.cells.append(new_markdown_cell(text) if kind == "md" else new_code_cell(text))
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    folder = ROOT / "notebooks"
    folder.mkdir(exist_ok=True)
    NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(folder)}}).execute()
    nbformat.write(nb, folder / "walkthrough.ipynb")
    print("wrote notebooks/walkthrough.ipynb")


if __name__ == "__main__":
    main()
