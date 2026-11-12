"""All the charts for the deck and the reports, from the saved results.

Each method keeps its colour on every chart: plain sampling is grey, textbook Grover is blue, the question-local
reflection is aqua, and the resilient build (steer, then amplify locally) is orange. Any chart whose data is not there
yet is skipped with a note, so this can be run at any time.

    python experiments/make_figures.py
"""

import glob
import json

from common import RESULTS, load

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

OUT = RESULTS / "figures"
OUT.mkdir(parents=True, exist_ok=True)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"  # textbook Grover
ORANGE = "#eb6834"  # the resilient build
AQUA = "#1baf7a"  # question-local reflection
GREY = "#898781"  # plain sampling
VIOLET = "#6250d6"
YELLOW = "#eda100"

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 16, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 1, "xtick.major.size": 0, "ytick.major.size": 0, "xtick.minor.size": 0,
    "ytick.minor.size": 0, "legend.frameon": False, "legend.fontsize": 15, "lines.linewidth": 2.4, "lines.solid_capstyle": "round",
    "axes.labelsize": 16, "xtick.labelsize": 15, "ytick.labelsize": 15,
})


def done(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(f"  wrote {name}.png", flush=True)


def compact(x, _=None) -> str:
    if x >= 1e6:
        return f"{x / 1e6:g}M"
    if x >= 1e3:
        return f"{x / 1e3:g}K"
    return f"{x:g}"


def power10(x, _=None) -> str:
    return f"$10^{{{int(round(np.log10(x)))}}}$" if x < 1 else compact(x)


def noisy_rows(pattern: str) -> list:
    rows = []
    for f in sorted(glob.glob(str(RESULTS / pattern))):
        d = json.load(open(f, encoding="utf-8"))
        for row in d["rows"]:
            rows.append({**row, "backend": d["backend"]})
    return rows


# ---------------------------------------------------------------------------- E2


def fig_curve() -> None:
    data = load("e2_amplify")
    fig, ax = plt.subplots(figsize=(10, 6))
    picks = [("click at step 6", BLUE, "a click at step 6 (p = 0.080)"), ("at least 2 clicks", ORANGE, "at least 2 clicks (p = 0.015)"),
             ("contains 11", AQUA, "two clicks in a row (p = 0.004)")]
    r_fine = np.linspace(0, 15, 600)
    for name, colour, label in picks:
        c = next(x for x in data["curves"] if x["name"] == name)
        theta = np.arcsin(np.sqrt(c["p"]))
        ax.plot(r_fine, np.sin((2 * r_fine + 1) * theta) ** 2, color=colour, alpha=0.45, lw=2)
        rows = [x for x in c["rows"] if x["r"] <= 15]
        ax.plot([x["r"] for x in rows], [x["hit"] for x in rows], "o", color=colour, ms=9, mec=SURFACE, mew=2, label=label)
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel("chance of a matching history")
    ax.set_xlim(-0.4, 15.4)
    ax.set_ylim(-0.03, 1.06)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=3, handletextpad=0.1, columnspacing=1.2)
    ax.text(15.3, 0.03, "dots: real Qiskit circuits   lines: sin²((2r+1)θ)", ha="right", color=MUTED, fontsize=14)
    done(fig, "fig_curve")


def fig_conditional() -> None:
    demo = load("e2_amplify")["shots_demo"]
    labels = demo["histories"][:7]
    exact = np.array(demo["exact"])[:7]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    x = np.arange(len(labels))
    titles = {0: GREY, 2: ORANGE}
    for ax, r in zip(axes, (0, 2)):
        run = next(q for q in demo["runs"] if q["r"] == r)
        est = np.array(run["estimate"])[:7]
        ax.bar(x, est, width=0.56, color=titles[r], label="sampled")
        ax.plot(x, exact, "_", color=INK, ms=30, mew=2.5, label="exact")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=12.5, family="monospace", rotation=35)
        name = "no amplification" if r == 0 else f"{r} Grover iterations"
        ax.set_title(f"{name}: {int(run['accepted']):,} of {demo['shots']:,} shots usable", fontsize=16, color=INK2, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("share of usable shots")
    axes[1].legend(loc="upper right")
    done(fig, "fig_conditional")


# ---------------------------------------------------------------------------- E3


def fig_wall() -> None:
    data = load("e3_scaling")
    rows = data["sweep"]["rows"]
    p = np.array([x["p"] for x in rows])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.loglog(p, [x["rejection_calls"] for x in rows], "o-", color=GREY, ms=8, mec=SURFACE, mew=2, label="plain sampling: 1/p")
    ax.loglog(p, [x["bbht_calls"] for x in rows], "o-", color=AQUA, ms=8, mec=SURFACE, mew=2, label="Grover, p unknown (BBHT)")
    ax.loglog(p, [x["amplified_calls"] for x in rows], "o-", color=BLUE, ms=8, mec=SURFACE, mew=2, label="Grover, p known")
    ax.invert_xaxis()
    ax.set_xlabel("how rare the event is (p)")
    ax.set_ylabel("machine calls per conditioned sample")
    ax.xaxis.set_major_locator(LogLocator(base=10, numticks=8))
    ax.xaxis.set_major_formatter(FuncFormatter(power10))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_locator(LogLocator(base=10, numticks=8))
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left")
    ax.grid(True, which="major")
    last = rows[-1]
    x_mark = p[-1] * 0.9
    ax.plot([x_mark, x_mark], [last["amplified_calls"] * 1.5, last["rejection_calls"] / 1.5], color=INK2, lw=1.2)
    ax.text(x_mark * 1.25, 1.2e4, f"{last['rejection_calls'] / last['amplified_calls']:,.0f}× fewer\ncalls", ha="right", va="center", color=INK2, fontsize=15)
    done(fig, "fig_wall")


def fig_wall_prefix() -> None:
    wall = load("e3_scaling")["wall"]
    t = np.array(wall["prefix_steps"])
    log_p = np.array(wall["prefix_log_p_median"])
    p = np.exp(log_p)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.semilogy(t, 1 / p, color=GREY, label="plain sampling")
    ax.semilogy(t, 0.79 / np.sqrt(p), color=BLUE, label="Grover: about (π/4)/√p iterations")
    ax.set_xlabel("steps of a real click record to match")
    ax.set_ylabel("runs or iterations")
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left")
    done(fig, "fig_wall_prefix")


def fig_classical() -> None:
    rows = load("e3_scaling")["classical"]
    n = np.array([x["n_memory"] for x in rows])
    build = np.array([x["build_seconds"] for x in rows])
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.semilogy(n, build, "o-", color=VIOLET, ms=8, mec=SURFACE, mew=2)
    ax.set_xlabel("hidden qubits")
    ax.set_ylabel("exact classical sampler: set-up time (s)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    done(fig, "fig_classical")


# ---------------------------------------------------------------------------- E4, E7


def fig_resilience() -> None:
    """The hero chart: gates, hit rate and distortion for textbook against the resilient build, across five devices."""
    rows = noisy_rows("e7_resilience/noisy_*.json")
    if not rows:
        print("  skipped fig_resilience: no E7 noisy data yet")
        return
    Ts = sorted({r["T"] for r in rows})
    builds = [("plain", GREY, "plain sampling"), ("textbook", BLUE, "textbook Grover"), ("local", AQUA, "local reflection"),
              ("steered+local", ORANGE, "steer + local")]
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2))
    offs = np.linspace(-0.18, 0.18, len(builds))
    for (name, colour, label), off in zip(builds, offs):
        cz, hit, tvd = [], [], []
        for T in Ts:
            sel = [r for r in rows if r["T"] == T and r["build"] == name]
            cz.append(np.median([r["cz"] for r in sel]))
            hit.append([r["hit"] for r in sel])
            tvd.append([r["tvd"] for r in sel])
        x = np.array(Ts, dtype=float)
        axes[0].plot(x, cz, "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=label)
        for ax, vals in ((axes[1], hit), (axes[2], tvd)):
            med = [np.median(v) for v in vals]
            lo = [np.min(v) for v in vals]
            hi = [np.max(v) for v in vals]
            ax.vlines(x + off, lo, hi, color=colour, lw=2, alpha=0.5)
            ax.plot(x + off, med, "o", color=colour, ms=9, mec=SURFACE, mew=2)
    axes[0].set_ylabel("two-qubit gates (compiled)")
    axes[1].set_ylabel("chance of the event, noisy")
    axes[2].set_ylabel("distribution error (TVD), noisy")
    axes[1].set_ylim(0, 1.0)
    axes[2].set_ylim(0, None)
    for ax in axes:
        ax.set_xlabel("record length T")
        ax.set_xticks(Ts)
        ax.grid(axis="x", visible=False)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout()
    done(fig, "fig_resilience")


def fig_steer_exact() -> None:
    """Exact hit rate against iterations, textbook against steered, for a typical length."""
    rows = load("e7_resilience", "noiseless.json")["rows"]
    Ts = sorted({r["T"] for r in rows})
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for name, colour, label in (("plain", GREY, "plain sampling"), ("textbook", BLUE, "textbook Grover"), ("steered", ORANGE, "steer, then 1 iteration")):
        ax.plot(Ts, [next(r["hit"] for r in rows if r["T"] == T and r["build"] == name) for T in Ts], "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=label)
    ax.set_xlabel("record length T")
    ax.set_ylabel("chance of the event (no noise)")
    ax.set_ylim(0, 1.06)
    ax.legend(loc="center right")
    done(fig, "fig_steer_exact")


def fig_device_trend() -> None:
    """What better hardware does: T = 5 on five devices, ordered by two-qubit error."""
    devices = load(".", "numbers.json").get("devices", {})
    if len(devices) < 3:
        print("  skipped fig_device_trend: not enough devices yet")
        return
    d = sorted(devices.items(), key=lambda kv: kv[1]["two_qubit_error"])
    x = [100 * v["two_qubit_error"] for _, v in d]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, key, label in ((axes[0], "hit", "chance of the event, T = 5"), (axes[1], "tvd", "distribution error (TVD), T = 5")):
        ax.plot(x, [v[f"textbook_{key}"] for _, v in d], "o-", color=BLUE, ms=8, mec=SURFACE, mew=2, label="textbook Grover")
        ax.plot(x, [v[f"resilient_{key}"] for _, v in d], "o-", color=ORANGE, ms=8, mec=SURFACE, mew=2, label="steer + local")
        ax.set_xlabel("device's median two-qubit error (%)")
        ax.set_ylabel(label)
    axes[0].set_ylim(0.4, 1.0)
    axes[1].set_ylim(0, None)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout()
    done(fig, "fig_device_trend")


def fig_reflection_map() -> None:
    """What each reflection keeps: hit rate and hidden-state fidelity, against T, at r = 2."""
    rows = load("e4_reflection", "local_noiseless.json")["rows"]
    Ts = sorted({r["T"] for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    specs = [("full", BLUE, "every qubit (textbook)"), ("memory+last-1", AQUA, "memory + the question's light"), ("memory", YELLOW, "memory only")]
    for name, colour, label in specs:
        hit = [next(x for x in rows if x["T"] == T and x["reflection"] == name)["series"][2]["hit"] for T in Ts]
        fid = [next(x for x in rows if x["T"] == T and x["reflection"] == name)["series"][2]["memory_fidelity"] for T in Ts]
        axes[0].plot(Ts, hit, "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=label)
        axes[1].plot(Ts, fid, "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=label)
    axes[0].set_ylabel("chance of the event at r = 2")
    axes[1].set_ylabel("hidden-state fidelity at r = 2")
    axes[0].set_ylim(0.3, 1.04)
    axes[1].set_ylim(0.5, 1.03)
    for ax in axes:
        ax.set_xlabel("record length T")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout()
    done(fig, "fig_reflection_map")


def fig_horizon() -> None:
    rows = load("e7_resilience", "horizon.json")["rows"]
    rows = [r for r in rows if r["r"] == 2]
    Ts = sorted({r["T"] for r in rows})
    fig, ax = plt.subplots(figsize=(10, 5.4))
    shades = {4: "#9ec5f4", 6: "#5598e7", 8: "#256abf", 10: "#0d366b"}
    for w, colour in shades.items():
        sel = [r for r in rows if r["w"] == w]
        ax.plot([r["T"] for r in sel], [r["hit"] for r in sel], "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=f"rewind {w} steps")
    ax.plot(Ts, [next(r["exact_hit"] for r in rows if r["T"] == T) for T in Ts], color=INK, lw=1.6, label="rewind everything")
    ax.set_xlabel("record length T")
    ax.set_ylabel("chance of the event at r = 2")
    ax.set_ylim(0.15, 1.04)
    ax.set_xticks(Ts)
    ax.legend(loc="lower center", ncol=3)
    done(fig, "fig_horizon")


def fig_future() -> None:
    rows = load("e7_resilience", "future.json")["rows"]
    T = [r["T"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.loglog(T, [r["textbook_cz"] for r in rows], "o-", color=BLUE, ms=8, mec=SURFACE, mew=2, label="textbook Grover")
    ax.loglog(T, [r["steered_local_cz"] for r in rows], "o-", color=ORANGE, ms=8, mec=SURFACE, mew=2, label="steer + local reflection")
    ax.loglog(T, [r["bounded_rewind_cz"] for r in rows], "o-", color=VIOLET, ms=8, mec=SURFACE, mew=2, label="+ bounded rewind")
    for err, label in ((1 / 2e-3, "today: ~1 error per 500 gates"), (1 / 1e-4, "20× better gates: 1 error per 10,000")):
        ax.axhline(err, color=MUTED, lw=1.2)
        ax.text(T[0], err * 1.1, label, color=INK2, fontsize=14, va="bottom")
    ax.set_xlabel("record length T (steps)")
    ax.set_ylabel("two-qubit gates per conditioned sample")
    ax.set_xticks(T)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(10, 2.5e4)
    ax.legend(loc="lower right")
    done(fig, "fig_future")


# ---------------------------------------------------------------------------- E5


def fig_fingerprint() -> None:
    data = load("e5_inside_loop", "noiseless.json")
    curves = data["curves"]
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    tau = np.arange(1, 11)
    for name, colour, label in (("one defect", ORANGE, "hidden defect"), ("no defect", BLUE, "no defect")):
        c = curves[name]["6"]
        ax.plot(tau, c["g2"], "o-", color=colour, ms=8, mec=SURFACE, mew=2, label=label)
    ax.axhline(1, color=MUTED, lw=1.2)
    ax.text(1.012, 1.0, "1.0 = no memory\nof the click", color=INK2, fontsize=14, ha="left", va="center",
            transform=ax.get_yaxis_transform())
    ax.set_xlabel("steps after a click (τ)")
    ax.set_ylabel("g²(τ): click rate after a click ÷ plain rate")
    ax.set_xticks(tau)
    ax.set_ylim(0, None)
    ax.legend(loc="lower right")
    done(fig, "fig_fingerprint")


def fig_after_click() -> None:
    rows = noisy_rows("e5_inside_loop/noisy_*.json")
    if not rows:
        print("  skipped fig_after_click: no E5 noisy data yet")
        return
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, model in zip(axes, ("one defect", "no defect")):
        sel = [r for r in rows if r["model"] == model]
        exact = np.array(sel[0]["exact"])
        tau = np.arange(1, len(exact) + 1)
        ax.plot(tau, exact, "_", color=INK, ms=34, mew=2.6, label="exact")
        for (reflection, r), colour, off, label in ((("full", 0), GREY, -0.1, "plain sampling"), (("memory+last-1", 1), ORANGE, 0.1, "steer + local, r = 1")):
            pick = [x for x in sel if x["reflection"] == reflection and x["r"] == r and (r == 0 or x.get("steer") is not None)]
            if not pick:
                continue
            est = np.array([x["conditional"] for x in pick])
            rmse = np.array([x["rmse_at_chunk"] for x in pick]).mean(axis=0)
            ax.errorbar(tau + off, est.mean(axis=0), yerr=rmse, fmt="o", color=colour, ms=9, mec=SURFACE, mew=2, capsize=0, lw=2, label=label)
        ax.set_xticks(tau)
        ax.set_xlabel("steps after the click (τ)")
        ax.set_title(model, loc="left", fontsize=16, color=INK2)
    axes[0].set_ylabel("P(click at t + τ | click at t)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout()
    done(fig, "fig_after_click")


# ---------------------------------------------------------------------------- E6


def fig_catalog() -> None:

    from qrsm_grover.search import amplified_probabilities, classical_scores, demo_catalog, phases, tokenise, tokens_of

    catalog = demo_catalog(16)
    vocabulary = set().union(*(tokens_of(name) for name in catalog))
    query = tokenise("how much did we sell in each area", vocabulary)
    scores = classical_scores(catalog, query)
    ph = phases(catalog, query)
    order = np.argsort(-scores, kind="stable")[:6]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.1), sharey=True, sharex=True)
    for ax, r in zip(axes, (0, 1, 3)):
        probs = amplified_probabilities(ph, r)
        y = np.arange(len(order))[::-1]
        ax.barh(y, probs[order], height=0.56, color=[ORANGE if scores[i] == 1 else (AQUA if scores[i] > 0 else GREY) for i in order])
        ax.set_title(f"r = {r}", loc="left", color=INK2, fontsize=16)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, 0.95)
        ax.set_xlabel("probability")
        top = order[0]
        ax.text(probs[top] + 0.02, y[0], f"{probs[top]:.0%}", va="center", color=INK, fontsize=15)
    axes[0].set_yticks(np.arange(len(order))[::-1])
    axes[0].set_yticklabels([catalog[i].replace("_", " ") for i in order], fontsize=15)
    done(fig, "fig_catalog")


def fig_reader() -> None:
    rows = load("e6_catalog", "reader.json")["rows"]
    T = [r["T"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.semilogy(T, [r["lookup_cz"] for r in rows], "o-", color=GREY, ms=8, mec=SURFACE, mew=2, label="lookup table of all histories")
    ax.semilogy(T, [r["reader_cz"] for r in rows], "o-", color=ORANGE, ms=8, mec=SURFACE, mew=2, label="recurrent reader")
    ax.set_xlabel("record length T")
    ax.set_ylabel("two-qubit gates in the oracle")
    ax.set_xticks(T)
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left")
    done(fig, "fig_reader")


def fig_catalog_cost() -> None:
    rows = load("e6_catalog")["costs"]
    N = [r["N"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.loglog(N, [r["classical_scan_steps"] for r in rows], "o-", color=GREY, ms=8, mec=SURFACE, mew=2, label="classical scan (steps)")
    ax.loglog(N, [r["grover_queries"] for r in rows], "o-", color=BLUE, ms=8, mec=SURFACE, mew=2, label="Grover (oracle queries)")
    ax.loglog(N, [r["total_cz"] for r in rows], "o-", color=ORANGE, ms=8, mec=SURFACE, mew=2, label="Grover (two-qubit gates)")
    ax.set_xlabel("catalogue size N")
    ax.set_ylabel("count")
    ax.set_xticks(N)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left")
    done(fig, "fig_catalog_cost")


# ---------------------------------------------------------------------------- hardware


BUILD_COLOUR = {"plain sampling": GREY, "textbook Grover, r = 3": BLUE, "local reflection, r = 3": AQUA,
                "steer + textbook reflection": VIOLET, "steer + local (resilient)": ORANGE}


def comparison() -> dict:
    return json.load(open(RESULTS / "hardware" / "comparison.json", encoding="utf-8"))


def fig_hardware() -> None:
    """Textbook Grover's hit rate against r: noiseless, the device's noise model, and the real device."""
    c = comparison()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
    r = np.arange(4)
    for ax, (title, curve) in zip(axes, c["curves"].items()):
        ax.plot(r, curve["ideal"], color=INK, lw=2, label="noiseless")
        ax.plot(r, curve["model"], "s--", color=MUTED, ms=8, mec=SURFACE, mew=2, label="noise model")
        ax.plot(r, curve["plain"], "o-", color=VIOLET, ms=10, mec=SURFACE, mew=2, label="real device")
        if "suppressed" in curve:
            ax.plot(r, curve["suppressed"], "D-", color=YELLOW, ms=9, mec=SURFACE, mew=2, label="real device, DD + twirling")
        ax.set_title(title, loc="left", color=INK2, fontsize=16)
        ax.set_xlabel("Grover iterations r")
        ax.set_xticks(r)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("chance of the event")
    axes[0].set_ylim(0, 1.05)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout()
    done(fig, "fig_hardware")


def fig_hw_builds() -> None:
    """The real chip's answer to the same rare question, build by build."""
    c = comparison()
    fig, axes = plt.subplots(1, 2, figsize=(17.5, 6.2), sharex=True)
    for ax, question in zip(axes, ("T = 3", "T = 5")):
        rows = [r for r in c["hero"] if r["question"] == question]
        y = np.arange(len(rows), dtype=float)[::-1]
        for yi, row in zip(y, rows):
            colour = BUILD_COLOUR[row["build"]]
            ax.barh(yi + 0.19, row["plain"]["hit"], height=0.34, color=colour, edgecolor=SURFACE, linewidth=2)
            ax.barh(yi - 0.19, row["suppressed"]["hit"], height=0.34, color=colour, alpha=0.45, edgecolor=SURFACE, linewidth=2)
            for dy, value, ink in ((0.19, row["plain"]["hit"], "white"), (-0.19, row["suppressed"]["hit"], INK)):
                if value > 0.2:  # inside the bar, clear of the markers near its end
                    ax.text(value - 0.012, yi + dy, f"{value:.2f}", va="center", ha="right", fontsize=13, color=ink, fontweight="semibold")
                else:
                    ax.text(value + 0.03, yi + dy, f"{value:.2f}", va="center", ha="left", fontsize=13, color=INK2)
            ax.plot([row["ideal_hit"]] * 2, [yi - 0.42, yi + 0.42], color=INK, lw=2.4, solid_capstyle="butt", zorder=4)
            ax.plot(row["model"]["hit"], yi, "D", color=SURFACE, mec=INK, mew=1.8, ms=9, zorder=5)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{r['build']}\n{r['cz']} two-qubit gates" for r in rows], fontsize=14)
        ax.set_title(f"a click at the last of {question.split()[-1]} steps", loc="left", color=INK2, fontsize=16)
        ax.set_xlabel("chance of the event")
        ax.set_xlim(0, 1.08)
        ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=INK2), plt.Rectangle((0, 0), 1, 1, color=INK2, alpha=0.45),
               plt.Line2D([], [], marker="D", color=SURFACE, mec=INK, mew=1.8, ms=9, lw=0), plt.Line2D([], [], color=INK, lw=2.4)]
    fig.legend(handles, ["real device", "real device, DD + twirling", "noise model", "noiseless"], loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.06))
    fig.tight_layout()
    done(fig, "fig_hw_builds")


def fig_hw_noise() -> None:
    """Noise analysis: what depth costs on the chip, and how well the device's own noise model predicts it."""
    c = comparison()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    series = (("model", "s", MUTED, "noise model"), ("plain", "o", VIOLET, "real device"), ("suppressed", "D", YELLOW, "real device, DD + twirling"))
    for tag, marker, colour, label in series:
        if tag not in c["decay"]:
            continue
        points = np.array(c["decay"][tag]["points"])
        axes[0].plot(points[:, 0], points[:, 1], marker, color=colour, ms=9, mec=SURFACE, mew=1.5, lw=0, label=label)
    axes[0].set_xlabel("two-qubit gates in the circuit")
    axes[0].set_ylabel("fidelity with the noiseless answer")
    axes[0].set_ylim(0, 1.03)
    rows = c["scatter"]
    axes[1].plot([0, 1], [0, 1], color=AXIS, lw=2)
    axes[1].plot(rows["model"], rows["plain"], "o", color=VIOLET, ms=9, mec=SURFACE, mew=1.5, lw=0)
    if "suppressed" in rows:
        axes[1].plot(rows["model"], rows["suppressed"], "D", color=YELLOW, ms=8, mec=SURFACE, mew=1.5, lw=0)
    axes[1].set_xlabel("chance of the event, predicted by the noise model")
    axes[1].set_ylabel("chance of the event, real device")
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(0, 1)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout()
    done(fig, "fig_hw_noise")


RUN_LABELS = {"plain": "Kingston, plain", "plain2": "Kingston, plain, repeat", "dd": "Kingston, DD alone", "twirl": "Kingston, twirling alone",
              "suppressed": "Kingston, DD + twirling", "plain_marrakesh": "Marrakesh, plain", "plain_marrakesh2": "Marrakesh, off the bad qubits"}


def fig_hw_runs() -> None:
    """Every real job side by side: does the result repeat, and does it survive a second chip?"""
    runs = comparison()["runs"]
    order = [tag for tag in RUN_LABELS if tag in runs]
    y = np.arange(len(order), dtype=float)[::-1]
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.6), sharey=True, gridspec_kw={"width_ratios": [1, 1, 0.9]})
    for ax, resilient, rival, title, rival_label in ((axes[0], "t3_resilient", "t3_textbook", "T = 3 hit rate", "textbook Grover, r = 3"),
                                                     (axes[1], "t5_resilient", "t5_textbook", "T = 5 hit rate", "same steer, textbook reflection")):
        for yi, tag in zip(y, order):
            a, b = runs[tag][rival]["hit"], runs[tag][resilient]["hit"]
            ax.plot([a, b], [yi, yi], color=AXIS, lw=3, zorder=1)
        ax.plot([runs[t][rival]["hit"] for t in order], y, "s", color=BLUE, ms=11, mec=SURFACE, mew=2, label=rival_label, zorder=2)
        ax.plot([runs[t][resilient]["hit"] for t in order], y, "o", color=ORANGE, ms=12, mec=SURFACE, mew=2, label="steer + local", zorder=3)
        ax.set_xlim(0.3, 1)
        ax.set_title(title, loc="left", color=INK2, fontsize=16)
        ax.set_xlabel("chance of the event")
        ax.grid(axis="y", visible=False)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.09), ncol=1, fontsize=13)
    signed = [runs[t]["after_click"]["separation"][2] * np.sign(runs[t]["after_click"]["signed_tau3"]) for t in order]
    axes[2].axvline(0, color=AXIS, lw=2)
    axes[2].axvline(3, color=MUTED, lw=1.6, ls=(0, (4, 3)))
    axes[2].plot(signed, y, "o", color=VIOLET, ms=12, mec=SURFACE, mew=2)
    for value, yi in zip(signed, y):
        axes[2].text(value + 0.35, yi, f"{value:.1f}", va="center", fontsize=13, color=INK2, zorder=3,
                     bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5})
    axes[2].set_title("after-click separation, τ = 3", loc="left", color=INK2, fontsize=16)
    axes[2].set_xlabel("standard errors, no defect above defect")
    axes[2].grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([RUN_LABELS[t] for t in order])
    fig.tight_layout()
    done(fig, "fig_hw_runs")


def fig_hw_after_click() -> None:
    """The physics question on real chips: what follows a click, with and without a hidden defect."""
    c = comparison()
    runs = c["runs"]
    exact = c["fingerprint"]["plain"]["amplified"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    tau = np.arange(1, 4)
    series = (("plain", "o", ORANGE, -0.14, "Kingston, plain"), ("plain2", "s", ORANGE, -0.05, "Kingston, plain, repeat"),
              ("plain_marrakesh2", "D", VIOLET, 0.05, "Marrakesh, off the bad qubits"), ("dd", "^", GREY, 0.14, "Kingston, DD alone"))
    for ax, key, exact_key, title in ((axes[0], "defect", "exact_defect", "one defect"), (axes[1], "no_defect", "exact_no_defect", "no defect")):
        ax.plot(tau, exact[exact_key], "_", color=INK, ms=38, mew=2.6, label="exact")
        for tag, marker, colour, off, label in series:
            if tag in runs:
                ax.plot(tau + off, runs[tag]["after_click"][key], marker, color=colour, ms=10, mec=SURFACE, mew=1.5, lw=0, label=label)
        ax.set_xticks(tau)
        ax.set_xlabel("steps after the click (τ)")
        ax.set_title(title, loc="left", fontsize=16, color=INK2)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("P(click at t + τ | click at t)")
    axes[0].set_ylim(0, 0.14)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=5, fontsize=13, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout()
    done(fig, "fig_hw_after_click")


def main() -> None:
    from qiskit import __version__  # noqa: F401  (the figures need the package importable)

    for fn in (fig_curve, fig_conditional, fig_wall, fig_wall_prefix, fig_classical, fig_resilience, fig_steer_exact, fig_reflection_map,
               fig_device_trend, fig_horizon, fig_future, fig_fingerprint, fig_after_click, fig_catalog, fig_catalog_cost, fig_reader, fig_hardware, fig_hw_builds, fig_hw_noise,
               fig_hw_runs, fig_hw_after_click):
        try:
            fn()
        except FileNotFoundError as e:
            print(f"  skipped {fn.__name__}: {e.filename} not found", flush=True)


if __name__ == "__main__":
    main()
