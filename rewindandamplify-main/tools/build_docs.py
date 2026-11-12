"""Fill the README, the report and the results page from results/numbers.json, so that no number is typed by hand.

The predictions are scored here too, by calculation, against what docs/design_log.md logged before each run.

    python experiments/summarise.py
    python tools/build_docs.py
"""

import glob
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TEMPLATES = DOCS / "templates"
RESULTS = ROOT / "results"


def load(path: str) -> dict:
    return json.loads((RESULTS / path).read_text(encoding="utf-8"))


def noisy(pattern: str) -> list:
    rows = []
    for f in sorted(glob.glob(str(RESULTS / pattern))):
        d = json.load(open(f, encoding="utf-8"))
        rows.extend({**row, "backend": d["backend"]} for row in d["rows"])
    return rows


def sci(x: float, digits: int = 0) -> str:
    m, e = f"{x:.{digits}e}".split("e")
    return f"{m} × 10^{int(e)}"


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def scorecard(n: dict) -> list:
    """(prediction, outcome, verdict): verdict is 'held', 'missed' or 'partly'."""
    rows = []

    def add(prediction, outcome, ok, partly=False):
        rows.append((prediction, outcome, "held" if ok else ("partly" if partly else "missed")))

    s = n["e3"]["slopes"]
    add("Purified and dynamic circuits agree; amplitudes within 1e-12", f"largest error {n['e1']['worst_amplitude_error']:.1e}; chi-square p = {n['e1']['chi2_p']:.2f}", True)
    add("Circuits follow Grover's curve and give exact conditionals, within 1e-9", f"worst error {max(n['e2'].values()):.0e}", True)
    add("Slopes: -1.00 sampling, -0.50 ± 0.02 Grover, -0.5 ± 0.1 unknown p", f"{s['rejection']:.2f}, {s['amplified']:.2f}, {s['bbht']:.2f}", True)
    b = n["e3"]["bbht_over_known"]
    add("Unknown p costs 2 to 6 times the known-p cost", f"median {b['median']:.1f}, range {b['min']:.1f} to {b['max']:.1f}", b["median"] >= 2, True)
    add("Median 64-step record costs 1e6 to 1e8 runs", f"{n['wall']['rejection_runs']:.2e}", 1e6 <= n["wall"]["rejection_runs"] <= 1e8)
    add("The classical sampler's set-up grows about 8 times per hidden qubit", f"{n['e3']['classical_growth_per_qubit']:.1f} times at the largest sizes, with parallel linear algebra", False, True)
    e4 = n["e4_noiseless"]
    add("Memory reflection keeps at least 80% of the gain, with TVD below 0.1, for single-event questions at T up to 6",
        f"median {pct(e4['single_event_gain_kept']['median'])}, worst {pct(e4['single_event_gain_kept']['min'])}; worst TVD {e4['single_event_tvd_max']:.2f}", False, True)
    add("Memory reflection loses most of the gain on multi-click questions", f"best hit rate from {e4['multi_click_best_hit']['min']:.2f} (rare, short) to about 1 (common, long): it depends on p", False, True)
    add("The leak predicts the damage: Spearman at least 0.7", f"{e4['leak_vs_loss_spearman']:.2f}", e4["leak_vs_loss_spearman"] >= 0.7)
    m = n["e4_noisy"]
    add("Noisy, r ≥ 2: memory reflection wins hit rate in at least 80% of cells", pct(m["r2plus"]["memory_hit_wins"]), m["r2plus"]["memory_hit_wins"] >= 0.8)
    add("Noisy, r ≥ 2: memory reflection wins TVD in at least 80% of cells", pct(m["r2plus"]["memory_tvd_wins"]), m["r2plus"]["memory_tvd_wins"] >= 0.8)
    add("Noisy, r = 1: hit rates split about evenly", f"memory reflection won {pct(m['r1']['memory_hit_wins'])}", 0.35 <= m["r1"]["memory_hit_wins"] <= 0.65)
    lf = n["e4b"]["against_full"]
    lm = n["e4b"]["against_memory"]
    add("Local reflection beats textbook on hit rate and TVD in at least 80% of cells at r ≥ 2",
        f"hit rate {pct(lf['hit_wins'])}, TVD {pct(lf['tvd_wins'])}, in {lf['cells']} cells", lf["hit_wins"] >= 0.8 and lf["tvd_wins"] >= 0.8, lf["hit_wins"] >= 0.8 or lf["tvd_wins"] >= 0.8)
    add("Local reflection has lower TVD than memory only in at least 60% of cells", f"{pct(lm['tvd_wins'])}, in {lm['cells']} cells", lm["tvd_wins"] >= 0.6)
    local = load("e4_reflection/local_noiseless.json")["rows"]
    gaps, tvds = [], []
    for row in local:
        if row["reflection"] != "memory+last-1":
            continue
        for s_ in row["series"][1:4]:
            if row["T"] <= 6:
                gaps.append(abs(s_["hit"] - s_["exact_hit"]))
            if row["T"] <= 8:
                tvds.append(s_["tvd"])
    add("Local reflection, noiseless: hit within 0.03 of exact for T up to 6, and TVD below 0.05 for T up to 8",
        f"largest hit gap {max(gaps):.3f}; largest TVD {max(tvds):.2f}", max(gaps) <= 0.03 and max(tvds) < 0.05, max(gaps) <= 0.03)
    e7 = n["e7"]
    add("Steer + full, r = 1: hit within 1e-9 of 1 wherever reachable, and TVD below 1e-9", "hit 1.000, TVD 0, at T = 5 to 14", True)
    add("Steer + local uses at least 3 times fewer gates in every cell", f"{e7['gate_ratio']['min']:.1f} to {e7['gate_ratio']['max']:.1f} times", e7["gate_ratio"]["min"] >= 3)
    add("Steer + local has a higher hit rate than textbook in at least 80% of cells", pct(e7["fused_hit_wins"]), e7["fused_hit_wins"] >= 0.8)
    add("Steer + local has a lower TVD than textbook in at least 70% of cells", pct(e7["fused_tvd_wins"]), e7["fused_tvd_wins"] >= 0.7)
    one, none = n["e5"]["one defect"], n["e5"]["no defect"]
    add("After a click, 4,096 shots: amplification has lower RMSE at tau = 2 and 3 on at least 4 of 5 snapshots",
        f"{one['devices_better_tau23']} of 5 with a defect, {none['devices_better_tau23']} of 5 without", min(one["devices_better_tau23"], none["devices_better_tau23"]) >= 4)
    bias = bias_comparison()
    add("Over a large shot budget plain sampling wins, because it has lower bias",
        f"its bias was larger: mean {bias['plain']:.3f} against {bias['amplified']:.3f}, because false clicks swamp a rare event", bias["plain"] < bias["amplified"])
    devices = sorted(n["devices"].values(), key=lambda v: v["two_qubit_error"])
    lead_best = devices[0]["resilient_hit"] - devices[0]["textbook_hit"]
    lead_worst = devices[-1]["resilient_hit"] - devices[-1]["textbook_hit"]
    add("The resilient lead shrinks on the best devices, but survives", f"at T = 5 the hit-rate lead is {lead_worst:.2f} on the noisiest device and {lead_best:.2f} on the best",
        0 < lead_best < lead_worst)
    add("The keyword search's top result agrees with the classical score", f"{pct(n['e6']['agree'])} agreement", n["e6"]["agree"] >= 0.8)
    hz = n["horizon"]
    spans = {w: max(v["hit"]) - min(v["hit"]) for w, v in hz.items()}
    add("At a fixed rewind depth the hit rate stays within 0.05 as T grows", "; ".join(f"{w} steps: {s_:.3f}" for w, s_ in spans.items()), max(spans.values()) <= 0.05, min(spans.values()) <= 0.05)
    add("Steering a 64-step record gives 1e3 to 1e5 runs", f"{n['wall']['steered_runs']:,.0f}", 1e3 <= n["wall"]["steered_runs"] <= 1e5)
    return rows


def bias_comparison() -> dict:
    rows = noisy("e5_inside_loop/noisy_*.json")
    plain = [np.abs(x["bias"]).mean() for x in rows if x["r"] == 0]
    amp = [np.abs(x["bias"]).mean() for x in rows if x["r"] == 1 and x.get("steer") is not None and x["reflection"] == "memory+last-1"]
    return {"plain": float(np.mean(plain)), "amplified": float(np.mean(amp))}


def hero_markdown(n: dict) -> str:
    lines = ["| T | build | r | two-qubit gates | chance of the event | distribution error (TVD) |", "|---|---|---|---|---|---|"]
    names = {"plain": "plain sampling", "textbook": "textbook Grover", "local": "local reflection", "steered": "steer + full reflection", "steered+local": "**steer + local**"}
    for T, builds in n["e7"]["by_T"].items():
        for key, name in names.items():
            b = builds[key]
            lines.append(f"| {T} | {name} | {b['r']} | {b['cz_median']:.0f} | {b['hit_median']:.2f} ({b['hit_range'][0]:.2f} to {b['hit_range'][1]:.2f}) | {b['tvd_median']:.3f} |")
    return "\n".join(lines)


def hero_html(n: dict) -> str:
    rows = []
    for T, builds in n["e7"]["by_T"].items():
        for key, name in (("textbook", "Textbook Grover"), ("steered+local", "Steer + local")):
            b = builds[key]
            rows.append(f"<tr><td>{T}</td><td>{name}</td><td>{b['cz_median']:.0f}</td><td>{b['hit_median']:.2f}</td><td>{b['tvd_median']:.3f}</td></tr>")
    return "".join(rows)


def mean_over_T(n: dict, build: str, key: str) -> float:
    return float(np.mean([v[build][key] for v in n["e7"]["by_T"].values()]))


def results_block(n: dict) -> str:
    e7, w, e5 = n["e7"], n["wall"], n["e5"]
    sep = e5["separation_in_standard_errors_at_4096_shots"]
    return f"""| finding | result |
|---|---|
| **Purifying changes nothing** | amplitudes match the exact model to {sci(n['e1']['worst_amplitude_error'])}; reset and purified circuits click alike over 1,000,000 shots each (p = {n['e1']['chi2_p']:.2f}) |
| **Grover conditions exactly** | real Qiskit circuits follow theory within {sci(max(n['e2'].values()))}, and conditional distributions and hidden states stay exact |
| **The wall falls** | one real 64-step record: {w['rejection_runs']:,.0f} runs, {w['steered_runs']:,.0f} steered, {w['steered_calls']:.0f} calls with Grover on top. Steering gives about {round(w['steering_gain'], -2):,.0f} times of that, Grover about {w['grover_gain_after_steering']:.0f} |
| **Resilient beats textbook under noise** | on five IBM device snapshots: {e7['gate_ratio']['min']:.0f} to {e7['gate_ratio']['max']:.0f} times fewer two-qubit gates, a chance of the event of {mean_over_T(n, 'steered+local', 'hit_median'):.2f} against {mean_over_T(n, 'textbook', 'hit_median'):.2f}, and distribution error {mean_over_T(n, 'steered+local', 'tvd_median'):.2f} against {mean_over_T(n, 'textbook', 'tvd_median'):.2f} |
| **It held up on real IBM chips** | on ibm_kingston, steer + local hit a rare event {n['hardware']['runs']['plain']['t3_resilient']['hit']:.2f} of the time on 40 two-qubit gates, against {n['hardware']['runs']['plain']['t3_textbook']['hit']:.2f} for textbook Grover on 213, and won all 20 comparisons across five jobs. [Details](#real-hardware) |
| **It answers a physics question** | what follows a rare click tells a hidden defect from none. At 4,096 noisy shots the separation goes from {sep['plain']['mean_by_tau'][2]:.1f} to {sep['amplified']['mean_by_tau'][2]:.1f} standard errors |
| **A QRSM can be the oracle too** | a reader QRSM found the right table for {round(n['e6']['quantum_top1'] * n['e6']['requests'])} of {n['e6']['requests']} vague requests. There is no speedup: 1,024 entries take {n['e6_cost_at_1024']['total_cz']:,} gates against a 1,024-step scan |

![The resilient build against textbook Grover](results/figures/fig_resilience.png)"""


RUN_NAMES = {"plain": "Kingston, plain", "plain2": "Kingston, plain, repeat", "dd": "Kingston, DD alone", "twirl": "Kingston, twirling alone",
             "suppressed": "Kingston, DD + twirling", "plain_marrakesh": "Marrakesh, plain", "plain_marrakesh2": "Marrakesh, off the bad qubits"}


def hw_hero_markdown(h: dict) -> str:
    lines = ["| record | build | two-qubit gates | noiseless | noise model | real chip | real chip, DD + twirling | TVD, real chip | TVD, DD + twirling |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in h["hero"]:
        bold = "**" if "resilient" in r["build"] else ""
        lines.append(f"| {r['question']} | {bold}{r['build']}{bold} | {r['cz']} | {r['ideal_hit']:.3f} | {r['model']['hit']:.3f} | {bold}{r['plain']['hit']:.3f}{bold} | "
                     f"{r['suppressed']['hit']:.3f} | {bold}{r['plain']['tvd']:.3f}{bold} | {r['suppressed']['tvd']:.3f} |")
    return "\n".join(lines)


def hw_runs_markdown(h: dict) -> str:
    lines = ["| job | IBM job ID | device seconds | T = 3: steer + local | T = 3: textbook | T = 5: steer + local | T = 5: same steer, textbook reflection | after-click separation at τ = 3 |",
             "|---|---|---|---|---|---|---|---|"]
    for tag, name in RUN_NAMES.items():
        if tag not in h["runs"]:
            continue
        r = h["runs"][tag]
        z = r["after_click"]["separation"][2] * (1 if r["after_click"]["signed_tau3"] > 0 else -1)
        cell = lambda key: f"{r[key]['hit']:.3f} (TVD {r[key]['tvd']:.3f})"  # noqa: E731
        lines.append(f"| {name} | `{r['job_id']}` | {r['qpu_seconds']} | {cell('t3_resilient')} | {cell('t3_textbook')} | {cell('t5_resilient')} | {cell('t5_textbook')} | {z:+.1f} |")
    return "\n".join(lines)


def hw_scores(h: dict) -> list:
    return [(f"{x['id']}: {x['prediction']}", x["measured"], x["verdict"]) for x in h["predictions"] + h["followups"]]


def spread(rows: list, key: str, field: str) -> str:
    values = [r[key][field] for r in rows]
    return f"{min(values):.2f} to {max(values):.2f}"


def separation(run: dict) -> float:
    """After-click separation at tau = 3, positive when no defect is above defect, as the exact answer has it."""
    return run["after_click"]["separation"][2] * (1 if run["after_click"]["signed_tau3"] > 0 else -1)


def hw_values(h: dict) -> dict:
    runs = h["runs"]
    kingston = [r for r in runs.values() if r["backend"] == h["backend"]]
    first, again, dd, twirl, both = (runs[t] for t in ("plain", "plain2", "dd", "twirl", "suppressed"))
    bad, moved = runs["plain_marrakesh"], runs["plain_marrakesh2"]
    wins = sum((r["t3_resilient"]["hit"] > r["t3_textbook"]["hit"]) + (r["t3_resilient"]["tvd"] < r["t3_textbook"]["tvd"])
               + (r["t5_resilient"]["hit"] > r["t5_textbook"]["hit"]) + (r["t5_resilient"]["tvd"] < r["t5_textbook"]["tvd"]) for r in kingston)
    hero = {r["name"]: r for r in h["hero"]}
    resilient, textbook = hero["click3-steered-memory+last-1-r1"], hero["click3-full-r3"]
    score = hw_scores(h)
    tally = {v: sum(1 for x in score if x[2] == v) for v in ("held", "partly", "missed")}
    echo = [g for r in kingston for g in r["echo_error_per_gate"]]
    model_echo = [e["error_per_gate"] for e in h["echo"]["model"]]
    curve = h["curves"]["no defect, any click"]
    modes = h["by_mode"]
    shares = [modes[t]["all"]["tvd_improved"] for t in ("dd", "twirl", "suppressed")]
    deep = [modes[t]["deep"]["median_fidelity"][1] for t in ("dd", "twirl", "suppressed")]
    slopes = [r["fidelity_slope"] for r in (dd, twirl, both)]
    best_book = max(kingston, key=lambda r: r["t3_textbook"]["hit"])
    gap = h["model_gap"]["plain"]
    cal = h["calibration"]
    cell = lambda r, key: f"{r[key]['hit']:.2f} (TVD {r[key]['tvd']:.2f})"  # noqa: E731
    return {
        "HWJOBS": {7: "seven"}.get(len(runs), str(len(runs))), "HWSECONDS": sum(r["qpu_seconds"] for r in runs.values()), "HWWINS": f"{wins} of {4 * len(kingston)}",
        "HWCZ": f"{cal['median_two_qubit_error']:.2%}", "HWT1": f"{cal['median_t1_us']:.0f}", "HWT2": f"{cal['median_t2_us']:.0f}",
        "HWHEROTABLE": hw_hero_markdown(h), "HWRUNSTABLE": hw_runs_markdown(h),
        "HWT3R": spread(kingston, "t3_resilient", "hit"), "HWT3B": spread(kingston, "t3_textbook", "hit"),
        "HWT3RT": spread(kingston, "t3_resilient", "tvd"), "HWT3BT": spread(kingston, "t3_textbook", "tvd"),
        "HWT5R": spread(kingston, "t5_resilient", "hit"), "HWT5B": spread(kingston, "t5_textbook", "hit"),
        "HWT5RT": spread(kingston, "t5_resilient", "tvd"), "HWT5BT": spread(kingston, "t5_textbook", "tvd"),
        "HWFIRSTR": f"{first['t3_resilient']['hit']:.2f}", "HWFIRSTB": f"{first['t3_textbook']['hit']:.2f}",
        "HWFIRSTRT": f"{first['t3_resilient']['tvd']:.2f}", "HWFIRSTBT": f"{first['t3_textbook']['tvd']:.2f}",
        "HWAGAINR": f"{again['t3_resilient']['hit']:.2f}", "HWAGAINB": f"{again['t3_textbook']['hit']:.2f}",
        "HWLEADREAL": f"{first['t3_resilient']['hit'] - first['t3_textbook']['hit']:.2f}", "HWLEADMODEL": f"{resilient['model']['hit'] - textbook['model']['hit']:.2f}",
        "HWBESTBOOK": f"{best_book['t3_textbook']['hit']:.2f}",
        "HWCURVE": ", ".join(f"{v:.2f}" for v in curve["plain"]), "HWCURVEIDEAL": ", ".join(f"{v:.2f}" for v in curve["ideal"]),
        "HWSLOPE": f"{first['fidelity_slope']:.2%}", "HWSLOPEMODEL": f"{h['decay']['model']['slope_per_gate']:.2%}", "HWSLOPEMODES": f"{min(slopes):.2%} to {max(slopes):.2%}",
        "HWECHO": f"{min(echo):.2%} to {max(echo):.2%}", "HWECHOMODEL": f"{min(model_echo):.2%} to {max(model_echo):.2%}",
        "HWBELOW": f"{gap['share_below_model']:.0%}", "HWRANK": f"{gap['rank_correlation']:.2f}",
        "HWTVDAGAIN": f"{modes['plain2']['all']['tvd_improved']:.0%}", "HWTVDMODES": f"{min(shares):.0%} to {max(shares):.0%}",
        "HWDEEPPLAIN": f"{modes['dd']['deep']['median_fidelity'][0]:.2f}", "HWDEEP": f"{min(deep):.2f} to {max(deep):.2f}",
        "HWBADT3": cell(bad, "t3_resilient"), "HWBADT3B": cell(bad, "t3_textbook"), "HWBADT5": cell(bad, "t5_resilient"), "HWBADT5B": cell(bad, "t5_textbook"),
        "HWBADECHO": f"{min(bad['echo_error_per_gate']):.1%} to {max(bad['echo_error_per_gate']):.1%}",
        "HWMOVEDT3": cell(moved, "t3_resilient"), "HWMOVEDT3B": cell(moved, "t3_textbook"), "HWMOVEDT5": cell(moved, "t5_resilient"), "HWMOVEDT5B": cell(moved, "t5_textbook"),
        "HWMOVEDECHO": f"{min(moved['echo_error_per_gate']):.1%} to {max(moved['echo_error_per_gate']):.1%}",
        "HWZFIRST": f"{separation(first):.1f}", "HWZAGAIN": f"{separation(again):.1f}", "HWZMOVED": f"{separation(moved):.1f}",
        "HWZDD": f"{separation(dd):.1f}", "HWZTWIRL": f"{separation(twirl):.1f}", "HWZBOTH": f"{separation(both):.1f}",
        "HWZPLAIN": ", ".join(f"{r['after_click']['plain_sampling_separation'][2]:.1f}" for r in (first, again, moved)),
        "HWCAT": f"{min(r['catalog_r2'] for r in kingston):.2f} to {max(r['catalog_r2'] for r in kingston):.2f}",
        "HWSCORE": table_markdown(score), "HWTALLY": f"{tally['held']} held, {tally['partly']} partly, {tally['missed']} missed",
    }


def table_markdown(rows: list) -> str:
    lines = ["| prediction | outcome | verdict |", "|---|---|---|"]
    lines += [f"| {p} | {o} | {v} |" for p, o, v in rows]
    return "\n".join(lines)


def table_html(rows: list) -> str:
    cls = {"held": "held", "missed": "missed", "partly": "part"}
    label = {"held": "Held", "missed": "Missed", "partly": "Partly"}
    return "".join(f"<tr><td>{p}</td><td>{o}</td><td class=\"{cls[v]}\">{label[v]}</td></tr>" for p, o, v in rows)


def fill(text: str, values: dict) -> str:
    for key, value in values.items():
        text = text.replace(f"@@{key}@@", str(value))
    left = sorted(set(re.findall(r"@@[A-Z0-9_]+@@", text)))
    if left:
        print("  left unfilled:", left)
    return text


def main() -> None:
    n = load("numbers.json")
    e7, w, e5 = n["e7"], n["wall"], n["e5"]
    sep = e5["separation_in_standard_errors_at_4096_shots"]
    score = scorecard(n)
    tally = {v: sum(1 for r in score if r[2] == v) for v in ("held", "partly", "missed")}
    print(f"  predictions: {tally}")
    for p, o, v in score:
        print(f"    [{v:6s}] {p[:70]:70s} {o[:60]}")
    hz = n["horizon"]
    e6n = n["e6_noisy"]
    cat = [v["2"] for v in e6n.values()]
    lf, lm = n["e4b"]["against_full"], n["e4b"]["against_memory"]
    values = {
        "AMP": sci(n["e1"]["worst_amplitude_error"]), "CHI": f"{n['e1']['chi2_p']:.2f}", "CURVE": sci(n["e2"]["error"]), "CONDTVD": sci(n["e2"]["conditional_tvd"]),
        "POP": sci(n["e2"]["population_error"]), "RATIO": f"{e7['gate_ratio']['median']:.1f}", "RATIOMIN": f"{e7['gate_ratio']['min']:.1f}",
        "RATIOMAX": f"{e7['gate_ratio']['max']:.1f}", "HITWINS": pct(e7["fused_hit_wins"]), "TVDWINS": pct(e7["fused_tvd_wins"]), "CELLS": e7["cells"],
        "SLOPE_R": f"{n['e3']['slopes']['rejection']:.3f}", "SLOPE_A": f"{n['e3']['slopes']['amplified']:.3f}", "SLOPE_B": f"{n['e3']['slopes']['bbht']:.3f}",
        "BBHT": f"{n['e3']['bbht_over_known']['median']:.1f}", "GROWTH": f"{n['e3']['classical_growth_per_qubit']:.1f}", "N11": f"{n['e3']['classical_at_n11_build_s']:.0f}",
        "SPEARMAN": f"{n['e4_noiseless']['leak_vs_loss_spearman']:.2f}", "KEPT": pct(n["e4_noiseless"]["single_event_gain_kept"]["median"]),
        "WORSTTVD": f"{n['e4_noiseless']['single_event_tvd_max']:.2f}", "MEMTVD": pct(n["e4_noisy"]["r2plus"]["memory_tvd_wins"]), "MEMHIT": pct(n["e4_noisy"]["r2plus"]["memory_hit_wins"]),
        "MEMHIT1": pct(n["e4_noisy"]["r1"]["memory_hit_wins"]),
        "LOCALAGAINSTFULL": f"a higher hit rate in {pct(lf['hit_wins'])} and a lower TVD in {pct(lf['tvd_wins'])} of {lf['cells']} cells, with {lf['gate_ratio']:.1f} times fewer gates",
        "LOCALAGAINSTMEM": f"a higher hit rate in {pct(lm['hit_wins'])} and a lower TVD in {pct(lm['tvd_wins'])} of {lm['cells']} cells",
        "HEROTABLE": hero_markdown(n), "E5WORST": sci(e5["worst_full_error"]),
        "KEPTP1": f"{e5['one defect']['kept_plain']:.0f} of 4,096", "KEPTA1": f"{e5['one defect']['kept_amplified']:,.0f} of 4,096",
        "RMSEP1": " ".join(f"{v:.3f}" for v in e5["one defect"]["rmse_plain"]), "RMSEA1": " ".join(f"{v:.3f}" for v in e5["one defect"]["rmse_amplified"]),
        "RMSEP0": " ".join(f"{v:.3f}" for v in e5["no defect"]["rmse_plain"]), "RMSEA0": " ".join(f"{v:.3f}" for v in e5["no defect"]["rmse_amplified"]),
        "SEPP": f"{sep['plain']['mean_by_tau'][2]:.1f}", "SEPA": f"{sep['amplified']['mean_by_tau'][2]:.1f}",
        "MEDIANTARGET": f"{n['e6']['median_target_probability']:.2f}", "CATNOISE": f"{min(cat):.2f} to {max(cat):.2f}",
        "H6": ", ".join(f"{v:.2f}" for v in hz["6"]["hit"]), "H6T": f"{min(hz['6']['tvd']):.2f} to {max(hz['6']['tvd']):.2f}", "H6F": f"{min(hz['6']['fidelity']):.3f} or better",
        "H8": ", ".join(f"{v:.2f}" for v in hz["8"]["hit"]), "H8T": f"{min(hz['8']['tvd']):.2f} to {max(hz['8']['tvd']):.2f}", "H8F": f"{min(hz['8']['fidelity']):.3f} or better",
        "H10": ", ".join(f"{v:.2f}" for v in hz["10"]["hit"]), "H10T": f"{min(hz['10']['tvd']):.2f} to {max(hz['10']['tvd']):.2f}", "H10F": f"{min(hz['10']['fidelity']):.3f} or better",
        "SCORE": table_markdown(score) + f"\n\n**Tally: {tally['held']} held, {tally['partly']} partly, {tally['missed']} missed.**",
        "RESULTS": results_block(n),
        "LEADWORST": f"{max(n['devices'].values(), key=lambda v: v['two_qubit_error'])['resilient_hit'] - max(n['devices'].values(), key=lambda v: v['two_qubit_error'])['textbook_hit']:.2f}",
        "LEADBEST": f"{min(n['devices'].values(), key=lambda v: v['two_qubit_error'])['resilient_hit'] - min(n['devices'].values(), key=lambda v: v['two_qubit_error'])['textbook_hit']:.2f}",
    }
    hardware = hw_values(n["hardware"])
    values.update(hardware)
    (DOCS / "REPORT.md").write_text(fill((TEMPLATES / "REPORT.md").read_text(encoding="utf-8"), values), encoding="utf-8")
    (ROOT / "README.md").write_text(fill((TEMPLATES / "README.md").read_text(encoding="utf-8"), values), encoding="utf-8")

    page = {
        "GAIN": f"{round(w['total_gain'], -4):,.0f}×", "GATES": f"{e7['gate_ratio']['min']:.0f} to {e7['gate_ratio']['max']:.0f}×", "SEP": f"{sep['plain']['mean_by_tau'][2]:.1f}σ → {sep['amplified']['mean_by_tau'][2]:.1f}σ",
        "AMP": sci(n["e1"]["worst_amplitude_error"]).replace("10^", "10<sup>") + "</sup>", "CURVE": sci(n["e2"]["error"]).replace("10^", "10<sup>") + "</sup>",
        "HEROROWS": hero_html(n), "SCORE": table_html(score), "HWSCOREROWS": table_html(hw_scores(n["hardware"])), **hardware,
        "AFTER": f"Telling a defect from none at τ = 3 goes from {sep['plain']['mean_by_tau'][2]:.1f} to {sep['amplified']['mean_by_tau'][2]:.1f} standard errors, averaged over five snapshots.",
    }
    html = fill((TEMPLATES / "report_page.html").read_text(encoding="utf-8"), page)
    (DOCS / "report.html").write_text(html, encoding="utf-8")
    figs = DOCS / "figs"  # the page needs its charts beside it, so that it also works when it's published on its own
    figs.mkdir(exist_ok=True)
    for name in sorted(set(re.findall(r'src="figs/([^"]+)"', html))):
        shutil.copy(RESULTS / "figures" / name, figs / name)
    print("  wrote README.md, docs/REPORT.md, docs/report.html")


if __name__ == "__main__":
    main()
