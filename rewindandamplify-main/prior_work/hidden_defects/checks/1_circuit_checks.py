"""Checks for experiment 1: does the Qiskit circuit make the clicks of v5's exact filter?

1. The circuit's step, as a matrix exported by experiments/1_qrsm_circuit.py, has exactly v5's Kraus operators: with
   the light starting in |0>, its "light reads 1" block is v5's emit @ U and its "light reads 0" block quiet @ U.
2. The perfect simulator's clicks against v5's exact filter, for 0 and 1 defects, with a perfect detector and with
   v5's good detector applied afterwards:
   - the click rate at every step, against the exact marginal probability (largest z over the 64 steps);
   - the distribution of gaps between consecutive clicks, against 40,000 records drawn from the exact filter
     (two-sample chi-square);
   - the mean log-likelihood at the true numbers, against its value on the exact filter's records (z).
3. The same statistics for the noisy device simulator's clicks, reported but not asserted: they are expected to
   differ, since there the emitter and the defect also relax and dephase.

Run with v1's environment (torch, and v5's code imported by path; -B writes nothing into v1 or v5):
  & "..\\Quantum research\\.venv\\Scripts\\python.exe" -B checks\\1_circuit_checks.py
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import torch
from scipy import stats

HERE = Path(__file__).resolve().parents[1]
V5 = HERE.parent / "Quantum research v5"
V1 = HERE.parent / "Quantum research"
_spec = importlib.util.spec_from_file_location("hidden_defects", V5 / "experiments" / "4_hidden_defects.py")
hd = importlib.util.module_from_spec(_spec)
sys.modules["hidden_defects"] = hd
_spec.loader.exec_module(hd)
torch.set_default_dtype(torch.float64)

OUT = HERE / "results" / "1_qrsm_circuit"
N_EXACT = 40_000  # records drawn from v5's exact filter for the gap and likelihood references
GAP_BINS = list(range(1, 21)) + [21, 31, 64]  # gap of 1..20 steps, then 21-30 and 31+
Z_STEP, P_GAP, Z_NLL = 3.5, 1e-3, 3.0  # pass marks: 3.5 is about a 3% chance over 64 steps by Bonferroni


def load(name: str) -> tuple:
    d = np.load(OUT / "data" / f"{name}.npz")
    meta = json.loads((OUT / "data" / f"{name}.json").read_text(encoding="utf-8"))
    X = np.concatenate([d["train"], d["val"], d["count"]])
    return torch.from_numpy(X.astype(np.int64)), meta


def true_unitary(k: int) -> tuple:
    ops = hd.register_ops(k)
    return ops, hd.step_unitary(ops, hd.THETA, hd.PHI[:k], hd.ZETA[:k])


def check_operator(k: int) -> float:
    M = np.load(OUT / f"step_operator_k{k}.npy")
    assert np.allclose(M.conj().T @ M, np.eye(len(M)), atol=1e-12), "the step is not unitary"
    ops, U = true_unitary(k)
    want = {1: (ops["emit"] @ U).numpy(), 0: (ops["quiet"] @ U).numpy()}
    err = max(np.abs(M[x::2, 0::2] - want[x]).max() for x in (0, 1))
    assert err < 1e-12, f"k={k}: the circuit's Kraus operators differ from v5's by {err:.2e}"
    return float(err)


def marginal_rates(k: int, eta: float, p_dark: float, T: int) -> np.ndarray:
    """The exact probability of a click at each step, averaged over all histories: the unconditional state."""
    ops, U = true_unitary(k)
    S1, S0 = hd.superops(ops, U, eta, p_dark)
    d = ops["d"]
    diag = torch.arange(d) * (d + 1)
    ell1 = S1[diag].sum(0)
    v = torch.zeros(d * d, dtype=hd.CD)
    v[0] = 1
    out = []
    for _ in range(T):
        out.append(float((v @ ell1).real))
        v = v @ (S1 + S0).T
    return np.array(out)


def exact_records(k: int, eta: float, p_dark: float, T: int, seed: int) -> torch.Tensor:
    _, U = true_unitary(k)
    gen = torch.Generator().manual_seed(seed)
    return hd.run_filter(U[None], torch.zeros(N_EXACT, T), eta, p_dark, sample=gen)[2]


def gaps(X: torch.Tensor) -> np.ndarray:
    """Histogram of the gaps between consecutive clicks in each record, in GAP_BINS."""
    out = []
    for row in X.numpy():
        idx = np.flatnonzero(row)
        out.append(np.diff(idx))
    g = np.concatenate(out) if out else np.array([])
    return np.histogram(g, bins=GAP_BINS)[0]


def two_sample_chi2(a: np.ndarray, b: np.ndarray) -> tuple:
    keep = (a + b) > 0
    a, b = a[keep], b[keep]
    na, nb = a.sum(), b.sum()
    chi2 = float((((math.sqrt(nb / na) * a - math.sqrt(na / nb) * b) ** 2) / (a + b)).sum())
    dof = len(a) - 1
    return chi2, dof, float(stats.chi2.sf(chi2, dof))


def nll_per_record(k: int, X: torch.Tensor, eta: float, p_dark: float) -> np.ndarray:
    _, U = true_unitary(k)
    with torch.no_grad():
        return torch.cat([hd.run_filter(U[None], x, eta, p_dark)[0][0] for x in X.split(2048)]).numpy()


def compare(name: str, seed: int) -> dict:
    X, meta = load(name)
    k, det = meta["k_true"], meta["detector"]
    eta, p_dark = det["eta"], det["p_dark"]
    S, T = X.shape
    p = marginal_rates(k, eta, p_dark, T)
    counts = X.sum(0).numpy()
    z_steps = (counts - S * p) / np.sqrt(S * p * (1 - p))
    E = exact_records(k, eta, p_dark, T, seed)
    chi2, dof, p_gap = two_sample_chi2(gaps(X), gaps(E))
    nll_x, nll_e = nll_per_record(k, X, eta, p_dark), nll_per_record(k, E, eta, p_dark)
    se = math.sqrt(nll_x.var(ddof=1) / len(nll_x) + nll_e.var(ddof=1) / len(nll_e))
    z_nll = float((nll_x.mean() - nll_e.mean()) / se)
    return {"name": name, "source": meta["source"], "k": k, "eta": eta, "p_dark": p_dark, "records": S,
            "click_rate": float(X.float().mean()), "exact_click_rate": float(p.mean()),
            "rate_per_step": (counts / S).tolist(), "exact_rate_per_step": p.tolist(),
            "max_abs_z_step": float(np.abs(z_steps).max()), "gap_hist": gaps(X).tolist(),
            "exact_gap_hist": gaps(E).tolist(), "gap_chi2": chi2, "gap_dof": dof, "gap_p": p_gap,
            "nll_per_step": float(nll_x.mean() / T), "exact_nll_per_step": float(nll_e.mean() / T),
            "nll_se_per_step": se / T, "z_nll": z_nll}


def make_figure(rows: dict) -> None:
    spec = importlib.util.spec_from_file_location("qlab_style", V1 / "qlab" / "style.py")
    style = importlib.util.module_from_spec(spec)
    sys.modules["qlab_style"] = style
    spec.loader.exec_module(style)
    plt = style.plt
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2), gridspec_kw={"width_ratios": [1.2, 1.1, 1], "wspace": 0.42})
    ideal, device = rows["ideal-k1-perfect"], rows["device-k1"]
    steps = np.arange(1, len(ideal["rate_per_step"]) + 1)
    ax = axes[0]
    ax.plot(steps, ideal["exact_rate_per_step"], color=style.INK, linewidth=1.4, label="v5's exact filter")
    ax.scatter(steps, ideal["rate_per_step"], s=16, color=style.BLUE, zorder=3,
               label="Qiskit circuit, perfect simulator")
    ax.scatter(steps, device["rate_per_step"], s=16, marker="s", color=style.ORANGE, zorder=3,
               label=f"Qiskit circuit, noisy {device_name(device)} simulator")
    ax.set_xlabel("step")
    ax.set_ylabel("chance of a click")
    ax.set_title("Click rate at each step (1 hidden defect)")
    ax.legend(loc="lower right")
    ax = axes[1]
    centers = [1 + i for i in range(20)] + [25.5, 47]
    for row, color, marker, label in ((ideal, style.BLUE, "o", "perfect simulator"),
                                      (device, style.ORANGE, "s", "noisy device simulator")):
        h = np.array(row["gap_hist"], float)
        ax.scatter(centers[:20], h[:20] / h.sum(), s=16, color=color, marker=marker, zorder=3, label=label)
    he = np.array(ideal["exact_gap_hist"], float)
    ax.plot(centers[:20], he[:20] / he.sum(), color=style.INK, linewidth=1.4, label="v5's exact filter")
    ax.set_xlabel("steps between consecutive clicks")
    ax.set_ylabel("share of gaps")
    ax.set_title("Gaps between clicks (1 hidden defect)")
    ax.legend(loc="upper right")
    ax = axes[2]
    names = list(rows)
    zs = [rows[n]["z_nll"] for n in names]
    colors = [style.ORANGE if rows[n]["source"] != "ideal" else style.BLUE for n in names]
    ax.axvspan(-2, 2, color=style.NEUTRAL, zorder=0)
    ax.scatter(zs, range(len(names)), s=40, color=colors, zorder=3)
    for i, z in enumerate(zs):
        ax.annotate(f"{z:+.1f}", (z, i), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8,
                    color=style.INK_2)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlim(-4, max(zs) * 1.25)
    ax.set_xticks([-2, 0, 2, 10, 20, 30])
    ax.set_xlabel("log-likelihood at the truth: difference from v5's exact records, in standard errors")
    ax.set_title("Likelihood under the exact model (grey band: within 2)")
    style.figure_note(fig, "The Qiskit circuit (an emitter, one hidden defect and a light qubit read mid-circuit "
                           "and reset every step) against v5's exact density-matrix filter, 8,704 records of 64 "
                           "steps. Left and middle: perfect detector. Right: every dataset, with its own detector; "
                           "positive means the records are less likely under the ideal model than its own records "
                           "are. The noisy device's emitter and defect also relax and dephase while the light is "
                           "read out, which the ideal model leaves out.")
    style.savefig(fig, OUT / "1_circuit_checks.png")


def device_name(row: dict) -> str:
    meta = json.loads((OUT / "data" / f"{row['name']}.json").read_text(encoding="utf-8"))
    return meta.get("device", "device").replace("Fake", "")


def main() -> None:
    out = {"operator_error": {k: check_operator(k) for k in (0, 1)}}
    print(f"1. the circuit's Kraus operators match v5's: largest difference {max(out['operator_error'].values()):.1e}")
    names = ["ideal-k1-perfect", "ideal-k1-good", "ideal-k0-perfect", "ideal-k0-good", "device-k1", "device-k0"]
    rows = {n: compare(n, seed=1000 + i) for i, n in enumerate(names)}
    print("2-3. clicks against v5's exact filter")
    print("| data | click rate (exact) | largest step z | gaps chi2 / dof, p | NLL per step (exact) | z | pass |")
    print("|---|---|---|---|---|---|---|")
    for n, r in rows.items():
        ok = r["max_abs_z_step"] < Z_STEP and r["gap_p"] > P_GAP and abs(r["z_nll"]) < Z_NLL
        r["pass"] = ok
        print(f"| {n} | {r['click_rate']:.4f} ({r['exact_click_rate']:.4f}) | {r['max_abs_z_step']:.1f} | "
              f"{r['gap_chi2']:.1f} / {r['gap_dof']}, {r['gap_p']:.3f} | {r['nll_per_step']:.5f} "
              f"({r['exact_nll_per_step']:.5f}) | {r['z_nll']:+.1f} | {'yes' if ok else 'no'} |")
    for n, r in rows.items():
        if r["source"] == "ideal":
            assert r["pass"], f"{n}: the perfect simulator's clicks differ from v5's exact filter"
    out["rows"] = rows
    (OUT / "checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    make_figure(rows)
    print("all asserted checks pass (the device rows are reported, not asserted)")


if __name__ == "__main__":
    main()
