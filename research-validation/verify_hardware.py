"""Reproduce the finals hardware comparison without modifying archived results.

Requires the original project's Qiskit/NumPy/SciPy dependencies. Rebuilds the
logical circuits and recomputes readout correction using the archived calibration.
This verifies internal reproducibility, not independent provenance from IBM.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "rewindandamplify-main"
sys.path[:0] = [str(PROJECT), str(PROJECT / "experiments")]

import numpy as np
from qiskit.quantum_info import Statevector
from analyse_hardware import device_flip_rates, score_history, to_distribution
from qrsm_grover.hardware import ONE, readout_correct, suite


def main():
    names = ("click3-steered-memory+last-1-r1", "click3-steered-full-r1")
    circuits = {e.name: e.circuit for e in suite(quick=True) if e.name in names}
    records = []
    for suffix in ("plain", "plain2"):
        path = PROJECT / "results" / "hardware" / f"raw_{suffix}.json"
        raw = json.loads(path.read_text(encoding="utf8"))
        saved = json.loads(path.with_name(f"summary_{suffix}.json").read_text(encoding="utf8"))
        rows = {r["name"]: r for r in saved["rows"]}
        rates = device_flip_rates(raw["calibration"])
        for item in raw["experiments"]:
            if item["name"] not in names:
                continue
            name = item["name"]
            # Qiskit strings are little-endian in qubit indexing; work qubits
            # can appear to the left of the event bit in the full reflection.
            event_bit = ONE.n_memory + item["meta"]["T"] - 1
            hits = sum(n for bits, n in item["counts"].items()
                       if (int(bits.replace(" ", ""), 2) >> event_bit) & 1)
            shots = sum(item["counts"].values())
            ideal = Statevector(circuits[name].remove_final_measurements(inplace=False)).probabilities()
            measured = to_distribution(item["counts"], item["logical_qubits"])
            corrected = readout_correct(measured, [rates[q] for q in item["physical_qubits"]])
            scores = {"raw": score_history(item["meta"], measured, ideal),
                      "corrected": score_history(item["meta"], corrected, ideal)}
            assert abs(scores["raw"]["hit"] - hits / shots) < 1e-14
            for kind in scores:
                for metric in ("hit", "ideal_hit", "tvd", "ideal_tvd"):
                    if not np.isclose(scores[kind][metric], rows[name][kind][metric], atol=1e-11, rtol=1e-10):
                        raise AssertionError((suffix, name, kind, metric))
            records.append({"source": path.relative_to(ROOT).as_posix(),
                            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "job_id": raw["meta"]["job_id"], "name": name,
                            "event_qubit_index": event_bit, "hits": hits, "shots": shots,
                            "two_qubit_gates": item["two_qubit_gates"],
                            "physical_qubits": item["physical_qubits"], **scores})
    result = {"status": "pass", "records": records,
              "scope": "Archived counts, calibration correction and exact logical circuit reproduced. Layouts differ. No IBM API call or new hardware run."}
    destination = Path(__file__).with_name("hardware_verification.json")
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
