"""Run the experiment on real IBM Quantum hardware, with your own account.

Save your account once, in your own terminal; the key is typed at a hidden prompt and never appears here:

    python tools/save_ibm_account.py

Then:

    python experiments/run_ibm.py --plan            pick a device, compile everything, estimate QPU time. Uses no QPU time.
    python experiments/run_ibm.py --predict         simulate those same circuits with the device's own noise model
    python experiments/run_ibm.py --submit          submit the jobs (this uses QPU time from your allowance)
    python experiments/run_ibm.py --fetch           wait for the jobs and save the raw counts
    python experiments/analyse_hardware.py          turn the counts into tables and figures

Two jobs are submitted by default, the same circuits in both, so that the effect of error suppression can be measured:
    plain        no suppression at all
    suppressed   dynamical decoupling (XY4) and Pauli twirling of gates and measurements

--jobs picks others: dd and twirl run each half of the suppression alone. A job's name sets its mode by what comes before
any digits or underscore, so plain2 repeats the plain job, and plain_marrakesh is a plain job with its own name.

--avoid compiles away from named physical qubits, and --label keeps those circuits apart from the device's main plan.

--submit reuses the exact circuits --plan compiled for that device, so a prediction and a job are always the same circuits.

Everything can be rehearsed without an account. This runs the same code path on a local device snapshot:

    python experiments/run_ibm.py --dry-run FakeFez
"""

import argparse
import json
import re
import time

from common import RESULTS, save


from qrsm_grover.hardware import compile_best, readout_calibration, suite

# SamplerV2 is deprecated from qiskit-ibm-runtime 0.50, with at least three months' notice, in favour of a client-side
# sampler. It is still the documented way to set these options in 0.51, so this stays on it for now.

OUT = "hardware"
SHOTS = 4096
CAL_SHOTS = 4096
SECONDS_PER_SHOT_GUESS = 300e-6  # the device's repetition delay dominates; for the estimate only
MAX_SIMULATED_QUBITS = 13  # a density matrix on 13 qubits is 1 GB
SIMULATOR_THREADS = 4
SIMULATOR_MEMORY_MB = 4096


def service():
    from qiskit_ibm_runtime import QiskitRuntimeService

    return QiskitRuntimeService()  # the account you saved; raises if there is none


def pick_backend(svc, name: str | None):
    if name:
        return svc.backend(name)
    return svc.least_busy(operational=True, simulator=False, min_num_qubits=20)


def build(backend, quick: bool, seeds: int, avoid: tuple = ()) -> tuple:
    """Compile every experiment, and add one readout calibration pair covering every physical qubit they use."""
    experiments = suite(quick)
    compiled, info = [], []
    for i, exp in enumerate(experiments):
        t0 = time.time()
        isa, stats = compile_best(exp.circuit, backend, seeds=seeds, avoid=avoid)
        compiled.append(isa)
        info.append({"name": exp.name, "meta": exp.meta, "logical_qubits": exp.circuit.num_qubits, **stats})
        print(f"  {i + 1:2d}/{len(experiments)} {exp.name:34s} {stats['two_qubit_gates']:3d} two-qubit gates, depth "
              f"{stats['depth']:4d}, predicted survival {stats['estimated_success']:.2f}, qubits {stats['physical_qubits']}  "
              f"[{time.time() - t0:.0f}s]", flush=True)
    from qiskit import transpile

    used = sorted({q for item in info for q in item["physical_qubits"]})
    device_qubits = backend.num_qubits
    calibration = [transpile(qc, backend=backend, optimization_level=0, initial_layout=list(range(device_qubits)))
                   for qc in readout_calibration(used, device_qubits)]
    return compiled, info, calibration, used


def device_calibration(backend) -> dict:
    """The device's reported medians at compile time."""
    import numpy as np

    target = backend.target
    two = next(name for name in ("cz", "ecr", "cx") if name in target.operation_names)

    def errors(name: str) -> list:
        return [p.error for p in target[name].values() if p is not None and p.error is not None and p.error < 0.5]

    def times(field: str) -> list:
        return [getattr(q, field) for q in target.qubit_properties if getattr(q, field, None)]

    return {"median_two_qubit_error": float(np.median(errors(two))), "median_readout_error": float(np.median(errors("measure"))),
            "median_sx_error": float(np.median(errors("sx"))), "median_t1_us": float(np.median(times("t1")) * 1e6),
            "median_t2_us": float(np.median(times("t2")) * 1e6)}


def plan_summary(backend, info: list, calibration: list) -> dict:
    shots = len(info) * SHOTS + len(calibration) * CAL_SHOTS
    return {"backend": backend.name, "experiments": len(info), "calibration_circuits": len(calibration),
            "calibration": device_calibration(backend),
            "shots_per_job": shots, "estimated_qpu_seconds_per_job": shots * SECONDS_PER_SHOT_GUESS,
            "most_two_qubit_gates": max(x["two_qubit_gates"] for x in info), "time": time.strftime("%Y-%m-%d %H:%M:%S")}


def save_compiled(name: str, compiled: list, calibration: list) -> None:
    from qiskit import qpy

    with open(RESULTS / OUT / f"compiled_{name}.qpy", "wb") as f:
        qpy.dump(compiled + calibration, f)


def load_compiled(backend, name: str, quick: bool) -> tuple | None:
    """The circuits --plan compiled for this device, if they match this run. Otherwise None, and they are compiled again."""
    from qiskit import qpy

    plan_file, cache = RESULTS / OUT / f"plan_{name}.json", RESULTS / OUT / f"compiled_{name}.qpy"
    if not plan_file.exists() or not cache.exists():
        return None
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    info = plan["experiments"]
    if plan["backend"] != backend.name or [x["name"] for x in info] != [e.name for e in suite(quick)]:
        return None
    with open(cache, "rb") as f:
        circuits = qpy.load(f)
    return circuits[:len(info)], info, circuits[len(info):], plan["calibrated_qubits"]


def compact(isa) -> tuple:
    """The same circuit on only the qubits it touches, and which physical qubits those are.

    A simulator must never be handed all 156 qubits of a compiled circuit: on a laptop that can use up the whole machine.
    """
    from qiskit import QuantumCircuit

    index = {q: i for i, q in enumerate(isa.qubits)}
    active = sorted({index[q] for inst in isa.data if inst.operation.name != "barrier" for q in inst.qubits})
    new = {physical: i for i, physical in enumerate(active)}
    small = QuantumCircuit(len(active))
    for register in isa.cregs:
        small.add_register(register)
    for inst in isa.data:
        if inst.operation.name != "barrier":
            small.append(inst.operation, [new[index[q]] for q in inst.qubits], inst.clbits)
    return small, active


def predict(backend, name: str, compiled: list, info: list, used: list) -> None:
    """Simulate the compiled circuits with the device's own reported errors, one small circuit at a time.

    This is the noise model of `AerSimulator.from_backend`, restricted to the qubits each circuit touches. It holds gate
    errors, relaxation during gates and readout errors. It has no crosstalk and no decay on idle qubits, which a real
    device does have.
    """
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel
    from qiskit_aer.noise.device.models import basic_device_gate_errors, basic_device_readout_errors

    t0 = time.time()
    gate_errors = basic_device_gate_errors(target=backend.target)
    readout = {qubits[0]: error for qubits, error in basic_device_readout_errors(target=backend.target)}
    rows = []
    for i, (isa, item) in enumerate(zip(compiled, info)):
        small, active = compact(isa)
        if len(active) > MAX_SIMULATED_QUBITS:
            raise ValueError(f"{item['name']} touches {len(active)} qubits; refusing to simulate more than {MAX_SIMULATED_QUBITS}")
        new = {physical: j for j, physical in enumerate(active)}
        noise = NoiseModel(basis_gates=["cz", "sx", "x", "rz", "id"])
        for gate, qubits, error in gate_errors:
            if all(q in new for q in qubits):
                noise.add_quantum_error(error, gate, [new[q] for q in qubits], warnings=False)
        for q, error in readout.items():
            if q in new:
                noise.add_readout_error(error, [new[q]], warnings=False)
        simulator = AerSimulator(method="density_matrix", noise_model=noise, max_parallel_threads=SIMULATOR_THREADS,
                                 max_memory_mb=SIMULATOR_MEMORY_MB, seed_simulator=1000 + i)
        rows.append({**item, "counts": simulator.run(small, shots=SHOTS).result().get_counts()})
        print(f"  {i + 1:2d}/{len(info)} {item['name']:34s} {len(active):2d} qubits  [{time.time() - t0:.0f}s]", flush=True)
    flips = [[float(readout[q].probabilities[0][1]), float(readout[q].probabilities[1][0])] for q in used]
    save(OUT, {"meta": {"backend": backend.name, "mode": "local simulation with the device's own noise model, not real hardware",
                        "job_id": None, "suppression": "none", "shots": SHOTS, "time": time.strftime("%Y-%m-%d %H:%M:%S")},
               "experiments": rows, "calibration": {"qubits": used, "flip_rates": flips}}, f"raw_noisemodel_{name}.json")
    print(f"noise-model prediction finished in {time.time() - t0:.0f} s", flush=True)


def sampler_for(mode, job: str = "plain"):
    from qiskit_ibm_runtime import SamplerV2

    kind = re.sub(r"\d+$", "", job.split("_")[0])
    if kind not in ("plain", "suppressed", "dd", "twirl"):
        raise ValueError(f"unknown job kind {kind!r}")
    sampler = SamplerV2(mode=mode)
    if kind in ("suppressed", "dd"):
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = "XY4"
    if kind in ("suppressed", "twirl"):
        sampler.options.twirling.enable_gates = True
        sampler.options.twirling.enable_measure = True
        sampler.options.twirling.num_randomizations = 32
        sampler.options.twirling.shots_per_randomization = SHOTS // 32
    return sampler


def pubs_for(compiled: list, calibration: list) -> list:
    return [(qc, None, SHOTS) for qc in compiled] + [(qc, None, CAL_SHOTS) for qc in calibration]


def counts_from(pub_result) -> dict:
    """The counts of whichever classical register a result used."""
    data = pub_result.data
    name = "meas" if hasattr(data, "meas") else [k for k in data.keys()][0]
    return getattr(data, name).get_counts()


def save_raw(tag: str, info: list, used: list, n_exp: int, results, meta: dict) -> None:
    counts = [counts_from(r) for r in results]
    save(OUT, {"meta": meta, "experiments": [{**x, "counts": c} for x, c in zip(info, counts[:n_exp])],
               "calibration": {"qubits": used, "counts": counts[n_exp:]}}, f"raw_{tag}.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--predict", action="store_true", help="also simulate the compiled circuits with the device's noise model")
    ap.add_argument("--dry-run", metavar="FAKE_BACKEND", help="run everything locally on a device snapshot")
    ap.add_argument("--backend", help="a device name; default: the least busy one")
    ap.add_argument("--quick", action="store_true", help="only the first few circuits")
    ap.add_argument("--jobs", nargs="+", default=["plain", "suppressed"], help="which jobs to submit: plain, suppressed, dd, twirl")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--avoid", type=int, nargs="*", default=[], help="physical qubits to keep off, with --plan")
    ap.add_argument("--label", help="a name for this plan, so that it doesn't replace the device's main one")
    args = ap.parse_args()
    (RESULTS / OUT).mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        from qiskit_ibm_runtime import fake_provider

        backend = getattr(fake_provider, args.dry_run)()
        compiled, info, calibration, used = build(backend, args.quick, args.seeds)
        print(json.dumps(plan_summary(backend, info, calibration), indent=1), flush=True)
        t0 = time.time()
        job = sampler_for(backend).run(pubs_for(compiled, calibration))
        result = job.result()
        save_raw(f"dryrun_{args.dry_run}", info, used, len(compiled), result,
                 {"backend": backend.name, "mode": "local dry run on a device snapshot, not real hardware", "job_id": None,
                  "suppression": "none", "shots": SHOTS, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"dry run finished in {time.time() - t0:.0f} s", flush=True)
        return

    svc = service()
    if args.plan or args.submit or args.predict:
        names = [b.name for b in svc.backends(operational=True, simulator=False)]
        print(f"devices this account can use: {', '.join(names)}", flush=True)
        backend = pick_backend(svc, args.backend)
        name = f"{backend.name}_{args.label}" if args.label else backend.name
        cached = None if args.plan else load_compiled(backend, name, args.quick)
        if cached:
            print(f"reusing the circuits --plan compiled as {name}", flush=True)
            compiled, info, calibration, used = cached
        else:
            print(f"compiling for {name}", flush=True)
            compiled, info, calibration, used = build(backend, args.quick, args.seeds, tuple(args.avoid))
            summary = plan_summary(backend, info, calibration)
            print(json.dumps(summary, indent=1), flush=True)
            save(OUT, {**summary, "avoided_qubits": args.avoid, "experiments": info, "calibrated_qubits": used}, f"plan_{name}.json")
            save_compiled(name, compiled, calibration)
        if args.predict:
            predict(backend, name, compiled, info, used)
        if args.submit:
            jobs = {}
            for tag in args.jobs:
                job = sampler_for(backend, tag).run(pubs_for(compiled, calibration))
                jobs[tag] = job.job_id()
                print(f"submitted {tag}: job {job.job_id()} on {backend.name}", flush=True)
            save(OUT, {"backend": backend.name, "jobs": jobs, "submitted": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "experiments": info, "calibrated_qubits": used, "shots": SHOTS}, f"jobs_{'_'.join(args.jobs)}.json")
    if args.fetch:
        for path in sorted((RESULTS / OUT).glob("jobs_*.json")):
            info_file = json.loads(path.read_text(encoding="utf-8"))
            info, used = info_file["experiments"], info_file["calibrated_qubits"]
            for tag, job_id in info_file["jobs"].items():
                job = svc.job(job_id)
                print(f"{tag}: job {job_id} is {job.status()}", flush=True)
                result = job.result()  # waits for the job
                usage = job.metrics().get("usage", {}).get("qpu_charge_time_seconds")  # job.usage() can read 0 on this plan
                save_raw(tag, info, used, len(info), result,
                         {"backend": info_file["backend"], "mode": "real IBM Quantum hardware", "job_id": job_id,
                          "suppression": tag, "shots": info_file["shots"], "qpu_seconds": usage,
                          "submitted": info_file["submitted"], "fetched": time.strftime("%Y-%m-%d %H:%M:%S")})
                print(f"{tag}: saved. QPU time used: {usage} s", flush=True)


if __name__ == "__main__":
    main()
