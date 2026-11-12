"""Fill demo/template.html with the machine's numbers, and write demo/index.html: one page, no server needed.

The page runs its own small simulator. It takes the step's memory part W from the Python model here, so that the two
cannot drift apart, and tests/test_page.py checks that the page's maths matches the package.

    python demo/build_page.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from qrsm_grover.model import QRSM, exchange
from qrsm_grover.search import CATALOG, STOP_WORDS, SYNONYMS


def memory_unitary(model: QRSM) -> np.ndarray:
    """The step's gates on the memory alone: drive, detune, exchange. Index: defect is bit 1, emitter bit 0."""
    qc = QuantumCircuit(2)
    qc.ry(model.theta, 0)
    qc.rz(model.zeta[0], 1)
    exchange(qc, model.phi[0], src=1, dst=0)
    return Operator(qc).data


def page_data() -> dict:
    model = QRSM()
    W = memory_unitary(model)
    return {"gamma": model.gamma, "W": [[[float(v.real), float(v.imag)] for v in row] for row in W], "catalog": CATALOG,
            "synonyms": SYNONYMS, "stop": sorted(STOP_WORDS)}


def main() -> None:
    template = (ROOT / "demo" / "template.html").read_text(encoding="utf-8")
    page = template.replace("/*DATA*/null", json.dumps(page_data()))
    (ROOT / "demo" / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote demo/index.html, {len(page) // 1024} KB")


if __name__ == "__main__":
    main()
