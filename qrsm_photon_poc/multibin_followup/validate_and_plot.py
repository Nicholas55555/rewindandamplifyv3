"""Read-only numerical audit of saved branch matrices, then create figures."""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from qrsm_photon import Parameters, instruments, init_state


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def td(a, b):
    difference = a-b
    return float(np.linalg.svd(difference, compute_uv=False).sum()/2)


def run(path):
    manifest = json.loads((path/"provenance_start.json").read_text())
    checks = []
    for rel, value in manifest["source_sha256"].items():
        if sha(HERE.parent/rel) != value: raise AssertionError("Source changed:"+rel)
        checks.append({"source_hash": rel, "passed": True})
    status = json.loads((path/"suite_status.json").read_text())
    if not status["all_completed"]: raise AssertionError("Suite has unfinished/failed cases")
    ideal, noise = [], []
    for entry in status["cases"]:
        file = path/entry["file"]
        if sha(file) != entry["sha256"]: raise AssertionError("Case hash mismatch")
        result = json.loads(file.read_text())
        archive = path/result["branch_archive"]
        if sha(archive) != result["branch_archive_sha256"]: raise AssertionError("Branch archive mismatch")
        if not result["implementation_validation"]["passed"]: raise AssertionError("Implementation failed")
        with np.load(archive) as arrays:
            for key in arrays.files:
                rho = arrays[key]
                np.testing.assert_allclose(rho, rho.conj().T, atol=1e-10)
                if np.linalg.eigvalsh((rho+rho.conj().T)/2).min() < -1e-10: raise AssertionError("Nonpositive branch")
            if entry["kind"] == "ideal":
                maps = instruments(Parameters(n_cavity=2))[:2]
                for bits in itertools.product([0, 1], repeat=3):
                    name = "".join(map(str, bits)); state = init_state(Parameters(n_cavity=2))
                    for bit in bits: state = maps[bit]@state
                    np.testing.assert_allclose(arrays["original_"+name], state.reshape(8, 8, order="F"), atol=1e-12)
                    np.testing.assert_allclose(arrays["compiled_"+name], arrays["retained_"+name], atol=1e-9)
                for event in ["last", "all"]:
                    names = ["".join(map(str, b)) for b in itertools.product([0, 1], repeat=3) if (b[-1] == 1 if event == "last" else all(b))]
                    selected = sum((arrays["retained_"+name] for name in names), np.zeros((8, 8), complex))
                    amplified = sum((arrays[f"amplified_{event}_"+name] for name in names), np.zeros((8, 8), complex))
                    p, pa = np.trace(selected).real, np.trace(amplified).real
                    np.testing.assert_allclose(pa, np.sin(3*np.arcsin(np.sqrt(p)))**2, atol=1e-10)
                    if td(amplified/pa, selected/p) > 1e-9: raise AssertionError("Conditioned state changed")
                    total = sum(np.trace(arrays[key]).real for key in arrays.files if key.startswith("amplified_"+event+"_"))
                    np.testing.assert_allclose(total, 1, atol=1e-10)
                ideal.append(result)
            else:
                target = arrays["preparation_0.0_trueflag1"]
                target = target/np.trace(target)
                for row in result["cases"]:
                    prefix = f"{row['circuit']}_{row['depolarizing_strength_cx']}_"
                    no, yes = arrays[prefix+"trueflag0"], arrays[prefix+"trueflag1"]
                    mixed = .01*no+.98*yes
                    np.testing.assert_allclose(mixed, arrays[prefix+"recordedflag1"], atol=1e-14)
                    np.testing.assert_allclose(np.trace(no+yes).real, 1, atol=1e-10)
                    np.testing.assert_allclose(np.trace(mixed).real, row["recorded_acceptance"], atol=1e-12)
                    np.testing.assert_allclose(td(mixed/np.trace(mixed), target), row["conditional_trace_distance_after_readout_vs_retained"], atol=1e-10)
                noise.append(result)
        checks.append({"branch_matrix_audit": entry["file"], "passed": True, "matrices": len(np.load(archive).files)})
    # Figures distinguish exact implementation from approximation and noisy answers.
    ideal.sort(key=lambda d: -d["instrument"]["choi_absolute_cutoff"])
    noise.sort(key=lambda d: -d["instrument"]["choi_absolute_cutoff"])
    labels = ["Cutoff0.03\n15 qubits", "Cutoff0.003\n18 qubits"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.3), layout="constrained")
    for ax, event, title in zip(axes[:2], ["last", "all"], ["Last-bin click", "Three clicks"]):
        x = np.arange(2)
        ax.bar(x-.17, [100*d["events"][event]["retained_probability"] for d in ideal], .32, label="Before", color="#347f9d")
        ax.bar(x+.17, [100*d["events"][event]["amplified_probability"] for d in ideal], .32, label="One full round", color="#bd7926")
        ax.set_title(title); ax.set_ylabel("Selected event probability (%)"); ax.set_xticks(x, labels)
    axes[0].legend(fontsize=8)
    axes[2].bar(range(2), [d["events"]["all"]["compilation"]["cx_gates"] for d in ideal], color="#438369")
    axes[2].set_title("Whole three-click query"); axes[2].set_ylabel("Generic CX gates"); axes[2].set_xticks(range(2), labels)
    for event, label, marker in [("last", "Last click", "o"), ("all", "Three clicks", "s")]:
        axes[3].plot([d["events"][event]["retained_vs_original_selected_trace_distance"] for d in ideal], marker+"-", label=label)
    axes[3].set_title("Approximation error"); axes[3].set_ylabel("Selected-state trace distance"); axes[3].set_xticks(range(2), labels); axes[3].legend(fontsize=8)
    fig.suptitle("Ideal retained-model implementation passes; finer approximation costs more gates")
    fig.savefig(path/"three_bin_tradeoff.png", dpi=170); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for j, case in enumerate(noise):
        for circuit, style, label in [("preparation", "o--", "Preparation"), ("amplified", "s-", "One full round")]:
            rows = [r for r in case["cases"] if r["circuit"] == circuit]
            axes[0, j].plot([100*r["recorded_acceptance"] for r in rows], style, label=label)
            axes[1, j].plot([r["conditional_trace_distance_after_readout_vs_retained"] for r in rows], style, label=label)
        axes[0, j].set_title(f"{case['circuits']['preparation']['qubits']} qubits, cutoff{case['instrument']['choi_absolute_cutoff']}")
        axes[0, j].set_ylabel("Recorded click acceptance (%)"); axes[0, j].legend()
        axes[1, j].set_ylabel("Conditional-state trace distance")
        for ax in axes[:, j]: ax.set_xticks(range(4), ["0", "10⁻⁵", "10⁻⁴", "10⁻³"]); ax.set_xlabel("Two-qubit depolarizing strength (listed settings)")
    fig.suptitle("Exact one-bin noise: higher acceptance can accompany a wrong conditional state\n1% false-positive /2% false-negative flag readout included")
    fig.savefig(path/"one_bin_noise.png", dpi=170); plt.close(fig)
    report = {"all_checks_passed": True, "checks": checks,
              "method": "Independent saved-matrix positivity/trace, original channel recursion, SVD trace distance and readout mixture recount; source/archive hashes checked.",
              "validator_sha256": sha(__file__), "noisy_workers_above_8_qubits": False,
              "figure_files": ["three_bin_tradeoff.png", "one_bin_noise.png"]}
    (path/"validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"checks_passed": len(checks), "all_cases_completed": True}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--run", type=Path, required=True)
    run(p.parse_args().run)
