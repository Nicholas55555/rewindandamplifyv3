"""3 - The QRSM circuit on real IBM hardware, with the user's own IBM Quantum account.

The same circuits as experiment 1 (1 hidden defect, no defect, and the readout calibration), transpiled for a real
device and run as one job with Qiskit Runtime's SamplerV2. The clicks are saved in experiment 1's format as
hardware-k1 and hardware-k0, so experiment 2 fits them like the simulators' records.

The account: the user saves it once, in their own terminal, and keeps the key; this script never sees it except
through Qiskit's saved-account file:
    from qiskit_ibm_runtime import QiskitRuntimeService
    QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token="<API key>", instance="<instance CRN>",
                                      set_as_default=True)

Run with v6's Qiskit environment:
  & "..\\Quantum research v6\\.venv-qiskit\\Scripts\\python.exe" -B experiments\\3_hardware.py --plan
      lists the devices the account can use, transpiles for the least busy one (or --backend NAME), and prints the
      chosen qubits, the gates per step and an estimate of the QPU time. Uses no QPU time.
  ... --submit      submits the job (uses QPU time from the account's allowance) and saves its id
  ... --fetch       waits for the saved job and writes the records
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from qiskit import transpile

HERE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("qrsm_circuit", HERE / "experiments" / "1_qrsm_circuit.py")
c1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c1)
OUT = HERE / "results" / "3_hardware"
DATA = c1.OUT / "data"
SHOTS = c1.N_TRAIN + c1.N_VAL + c1.N_COUNT  # 8,704 records per circuit, as the simulators'
REP_DELAY_GUESS = 250e-6  # seconds between shots, for the time estimate only


def service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService()  # the account the user saved; raises if there is none


def pick_backend(svc, name: str = None):
    if name:
        return svc.backend(name)
    return svc.least_busy(operational=True, simulator=False, dynamic_circuits=True)


def build(backend) -> dict:
    """The three circuits, transpiled and scheduled for the device; the no-defect circuit and the calibration use
    the emitter's and the light's qubits from the 1-defect circuit's layout."""
    qc1 = c1.qrsm_circuit(1, c1.T)
    isa1 = transpile(qc1, backend=backend, optimization_level=3, seed_transpiler=c1.SEED_TRANSPILE)
    layout = c1.device_qubits(isa1)
    pair = [layout[0], layout[-1]]
    qc0 = c1.qrsm_circuit(0, c1.T)
    isa0 = transpile(qc0, backend=backend, optimization_level=3, seed_transpiler=c1.SEED_TRANSPILE,
                     initial_layout=pair)
    cal, pattern = c1.calibration_circuit(qc0, c1.T)
    isa_cal = transpile(cal, backend=backend, optimization_level=3, seed_transpiler=c1.SEED_TRANSPILE,
                        initial_layout=pair)
    return {"k1": isa1, "k0": isa0, "cal": isa_cal, "pattern": pattern.tolist()}


def describe(backend, circuits: dict) -> dict:
    out = {"backend": backend.name, "circuits": {}}
    total = 0.0
    for key in ("k1", "k0", "cal"):
        isa = circuits[key]
        try:
            dur = isa.estimate_duration(backend.target, unit="s")
        except Exception:  # some targets lack a duration for an instruction; the estimate is then skipped
            dur = float("nan")
        shots = c1.CAL_SHOTS if key == "cal" else SHOTS
        qubits = c1.device_qubits(isa)
        step = dur / c1.T
        out["circuits"][key] = {"physical_qubits": qubits, "ops_per_step": c1.counts_per_step(isa, c1.T),
                                "record_seconds": dur, "step_seconds": step, "shots": shots,
                                "qubits": c1.qubit_info(backend, qubits, step) if np.isfinite(step) else None}
        total += shots * ((dur if np.isfinite(dur) else 0.0) + REP_DELAY_GUESS)
    out["estimated_qpu_seconds"] = total
    return out


def save_records(name: str, X: np.ndarray, info: dict, calibration: dict, k: int) -> None:
    truth = {"theta": c1.THETA, "gamma": c1.GAMMA, "phi": [c1.PHI], "zeta": [c1.ZETA]}
    meta = {"source": "IBM hardware", "device": info["backend"], "k_true": k,
            "truth": truth if k else {"theta": c1.THETA, "gamma": c1.GAMMA},
            "detector": {"eta": calibration["eta"], "p_dark": calibration["p_dark"],
                         "how": "the device's own readout, calibrated in the same job"},
            "calibration": calibration, "job_id": info["job_id"], **info["circuits"][f"k{k}"]}
    c1.save(name, X, (c1.N_TRAIN, c1.N_VAL, c1.N_COUNT), meta, DATA)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--backend", help="a device name; default: the least busy one with dynamic circuits")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    svc = service()
    if args.plan or args.submit:
        names = [b.name for b in svc.backends(operational=True, simulator=False)]
        print(f"devices this account can use: {', '.join(names)}", flush=True)
        backend = pick_backend(svc, args.backend)
        circuits = build(backend)
        info = describe(backend, circuits)
        print(json.dumps(info, indent=1), flush=True)
        print(f"estimated QPU time: about {info['estimated_qpu_seconds']:.0f} s plus the device's fixed overheads",
              flush=True)
        (OUT / "plan.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
        if args.submit:
            from qiskit_ibm_runtime import SamplerV2
            sampler = SamplerV2(mode=backend)
            job = sampler.run([(circuits["k1"], None, SHOTS), (circuits["k0"], None, SHOTS),
                               (circuits["cal"], None, c1.CAL_SHOTS)])
            info.update({"job_id": job.job_id(), "submitted": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "pattern": circuits["pattern"]})
            (OUT / "job.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            print(f"submitted job {job.job_id()} to {backend.name}", flush=True)
    if args.fetch:
        info = json.loads((OUT / "job.json").read_text(encoding="utf-8"))
        job = svc.job(info["job_id"])
        print(f"job {info['job_id']}: {job.status()}", flush=True)
        result = job.result()  # waits for the job
        arrays = [c1.to_array(pub.data.click.get_bitstrings()) for pub in result]
        Xc, sent = arrays[2], np.broadcast_to(np.array(info["pattern"]), arrays[2].shape)
        p10, p01 = float(Xc[sent == 0].mean()), float(1 - Xc[sent == 1].mean())
        calibration = {"P(1|0)": p10, "P(0|1)": p01, "eta": 1 - p01 / (1 - p10), "p_dark": p10,
                       "shots": int(len(Xc)), "measurements_each": int((sent == 0).sum()),
                       "how": "fitted from a calibration circuit with the experiment's timing, in the same job"}
        print(f"readout calibration: P(1|0) = {p10:.4f}, P(0|1) = {p01:.4f}", flush=True)
        save_records("hardware-k1", arrays[0], info, calibration, 1)
        save_records("hardware-k0", arrays[1], info, calibration, 0)
        try:
            usage = job.usage()
            (OUT / "usage.json").write_text(json.dumps({"qpu_seconds": usage}, indent=1), encoding="utf-8")
            print(f"QPU time used: {usage} s", flush=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
