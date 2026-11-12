"""Run each fixed circuit case in a bounded worker, preserving all outcomes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import scipy
import qiskit
import qiskit_aer

HERE = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def worker(kind, cutoff, out):
    sys.path.insert(0, str(HERE.parent))
    from dilation_synthesis import enforce_memory_limit
    memory_handle = enforce_memory_limit(2048)
    from model import ideal_case, noise_case
    begin = time.perf_counter()
    try:
        result, arrays = ideal_case(cutoff) if kind == "ideal" else noise_case(cutoff)
        archive = out.with_suffix(".npz")
        np.savez_compressed(archive, **arrays)
        result.update(status="completed" if result["implementation_validation"]["passed"] else "failed_validation",
                      branch_archive=archive.name, branch_archive_sha256=sha(archive), memory_limit_mib=2048)
    except Exception as exc:
        result = {"status": "failed", "kind": kind, "cutoff": cutoff, "error": repr(exc), "elapsed_seconds": time.perf_counter()-begin}
    write(out, result)
    print(f"Worker {kind} cutoff{cutoff}: {result['status']} in{time.perf_counter()-begin:.2f}s", flush=True)
    _ = memory_handle


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    if (out/"provenance_start.json").exists(): raise FileExistsError("Choose a new output directory; all prior runs are retained.")
    paths = [HERE/"PROTOCOL.md", HERE/"model.py", HERE/"run_suite.py",
             HERE.parent/"qrsm_photon.py", HERE.parent/"dilation_feasibility.py", HERE.parent/"dilation_synthesis.py"]
    manifest = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_sha256": {str(p.relative_to(HERE.parent)): sha(p) for p in paths},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                     "qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__},
        "worker_timeout_seconds": 240, "worker_memory_limit_mib": 2048,
        "matrix": [{"kind": kind, "cutoff": cutoff} for kind in ["ideal", "noise"] for cutoff in [.03, .003]]}
    write(out/"provenance_start.json", manifest)
    summaries = []
    for case in manifest["matrix"]:
        name = case["kind"]+"_"+str(case["cutoff"]).replace(".", "p")
        path = out/(name+".json")
        command = [sys.executable, "-u", str(Path(__file__).resolve()), "--worker", case["kind"],
                   "--cutoff", str(case["cutoff"]), "--out", str(path.resolve())]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        begin = time.monotonic(); next_update = begin+30
        process = subprocess.Popen(command, creationflags=flags)
        print(f"Started {name}, pid{process.pid}, hard limit240s/2048MiB", flush=True)
        timeout = False
        while process.poll() is None:
            try: process.wait(timeout=1)
            except subprocess.TimeoutExpired: pass
            now = time.monotonic()
            if now-begin >= 240 and process.poll() is None:
                timeout = True; process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            if now >= next_update and process.poll() is None:
                print(f"Still running {name}: {now-begin:.0f}s", flush=True); next_update += 30
        if not path.exists():
            write(path, {"status": "timeout" if timeout else "process_failed", "exitcode": process.returncode,
                         "case": case, "pid": process.pid, "elapsed_seconds": time.monotonic()-begin})
        result = json.loads(path.read_text(encoding="utf-8"))
        summaries.append({**case, "file": path.name, "status": result["status"], "sha256": sha(path)})
        write(out/"suite_status.json", {"cases": summaries, "all_completed": len(summaries) == 4 and all(x["status"] == "completed" for x in summaries)})
    print("Suite complete; every worker exited, completed or failed cases preserved.", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--worker", choices=["ideal", "noise"])
    p.add_argument("--cutoff", type=float)
    args = p.parse_args()
    if args.worker: worker(args.worker, args.cutoff, args.out)
    else: run(args.out)
