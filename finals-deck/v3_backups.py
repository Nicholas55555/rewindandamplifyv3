"""The backup slides of the V3 finals deck, in the same dark style as the main talk.

Backups exist for questions. Each one states its finding in the title, says in a chip what kind of evidence it
shows (ran on IBM hardware, simulated by us, published data reanalysed, negative result), and reads its numbers
from the saved results at build time. They are ordered by topic, and the first one is a map of the rest.

build_v3_deck.py calls build_backups(); nothing here is run on its own.
"""
from __future__ import annotations

import math
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from deck_kit import (AMBER, CREAM, CYAN, GREEN, MUTED, SLATE, SOFT, TRACK, VIOLET, backup_notes, bar, base, chip_right,
                      load, panel, pct, picture, px, rule, table, takeaway, text, two_tone)

LEFT, RIGHT, CENTER, MIDDLE = PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE
RED = RGBColor(0xF0, 0x8A, 0x7C)
# what kind of evidence a slide shows
IBM, SIM, DATA, NEG, REF = (("Ran on IBM hardware", GREEN), ("Simulated by us", CYAN), ("Published data, reanalysed", VIOLET),
                            ("Negative result", AMBER), ("Reference", MUTED))
LOCAL, FULL = "click3-steered-memory+last-1-r1", "click3-steered-full-r1"


def backup(prs, number, group, first, second, lede=None, footer=None, kind=REF, title_size=42):
    slide = base(prs, number, f"Backup · {group}", two_tone(first, second), lede, footer, title_size=title_size)
    chip_right(slide, *kind)
    return slide


def points(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}"


# ---------------------------------------------------------------------------- numbers the backups add


def backup_evidence(e: dict) -> dict:
    """Figures quoted only on backup slides, each read from the file that stores it."""
    runs = {}
    for key, folder in (("first", "original_plain_v2"), ("suppressed", "original_suppressed_v1"), ("precision", "original_precision_v1")):
        rows = {row["name"]: row for row in load(f"hardware_campaign/runs/{folder}/analysis.json")["rows"]}
        runs[key] = rows
    b = {"runs": []}
    for key, name, note in (("first", "First run", "raw counts"), ("suppressed", "With suppression", "dynamical decoupling and twirling"),
                            ("precision", "Precision repeat", "raw counts")):
        local, full = (runs[key][n] for n in (LOCAL, FULL))
        b["runs"].append({
            "name": name, "note": note, "shots": local["observables"]["selected"]["shots"],
            "local": local["observables"]["selected"]["probability"], "full": full["observables"]["selected"]["probability"],
            "tv": [row["observables"]["selected_history_tv_to_unsteered_target"] for row in (local, full)]})
    ladder = [("Plain sampling", "click3-full-r0", MUTED), ("Steer one gate", "click3-steered-full-r0", SOFT),
              ("Textbook Grover: 3 rounds, not steered", "click3-full-r3", SOFT),
              ("Steer + 1 round, full reflection", FULL, AMBER), ("Steer + 1 round, local reflection (ours)", LOCAL, CYAN)]
    b["ladder"] = [{"name": name, "rate": runs["first"][key]["observables"]["selected"]["probability"],
                    "gates": runs["first"][key]["native_two_qubit_gate_count"], "color": color} for name, key, color in ladder]
    campaign = load("hardware_campaign/results.json")
    coverage = load("hardware_campaign/coverage.json")
    b["campaign"] = {"jobs": campaign["jobs"], "science": campaign["science_circuit_executions"],
                     "calibration": campaign["calibration_circuit_executions"], "shots": campaign["total_shots"],
                     "seconds": campaign["actual_campaign_quantum_seconds"], "families": coverage["family_count"],
                     "device_qubits": coverage["confirmed_device_qubits"]}
    deep = {row["name"]: row for row in load("hardware_campaign/runs/optical_dilation_plain_v2/analysis.json")["rows"]}
    b["deep"] = [{"cutoff": cutoff, "qubits": deep[name]["logical_qubits"], "gates": deep[name]["native_two_qubit_gate_count"],
                  "accepted": deep[name]["observables"]["accepted_shots"], "shots": deep[name]["observables"]["shots"],
                  "ideal": deep[name]["observables"]["ideal_event_probability"], "tv": deep[name]["observables"]["data_z_distribution_tv"]}
                 for cutoff, name in (("0.03", "optical_3bin_0p03_all_r1"), ("0.003", "optical_3bin_0p003_all_r1"))]
    contrast = load("hardware_campaign/runs/original_precision_v1/loop_contrasts.json")["comparisons"]["steered_local"][2]
    assert contrast["step"] == 6
    b["local_contrast"] = {"difference": contrast["probability_difference"], "interval": contrast["independent_shot_wilson_based_interval95"]}
    assert [round(100 * row["rate"], 2) for row in b["ladder"]] == [6.74, 24.07, 48.73, 64.26, 77.39]
    assert (b["campaign"]["jobs"], b["campaign"]["science"], b["campaign"]["seconds"]) == (10, 207, 244)
    b["research"] = research_evidence()
    return b


# ---------------------------------------------------------------------------- on IBM hardware


def backup_map(prs, e, b, n, index, groups):
    s = backup(prs, n, "map", "Backups, ", "by the question asked.")
    cells = [(64, 132, 262), (456, 132, 262), (848, 132, 262), (64, 410, 238), (456, 410, 238), (848, 410, 238)]
    for (x, y, h), (group, items) in zip(cells, groups):
        panel(s, x, y, 368, h)
        text(s, x + 20, y + 14, 328, 24, group.upper(), size=13, bold=True, color=CYAN, tracking=1.4)
        for i, (number, short) in enumerate(items):
            yy = y + 48 + i * 34
            text(s, x + 20, yy, 40, 28, f"{number}", size=18, bold=True, color=AMBER, font="Consolas", anchor=MIDDLE)
            text(s, x + 64, yy, 290, 28, short, size=17.5, color=CREAM, anchor=MIDDLE)
    text(s, 64, 664, 1070, 40, "In a slide show, type a slide number and press Enter to jump to it.", size=14.5, color=MUTED, anchor=MIDDLE)
    return s


def backup_ladder(prs, e, b, n, index):
    s = backup(prs, n, "on IBM hardware", "What each move bought, ", "measured on the chip.",
               "First run on IBM Marrakesh, 2,048 shots per circuit, raw counts. The chance that a shot contains the click we asked about.",
               "hardware_campaign/runs/original_plain_v2/analysis.json. One run of each circuit. The last two were repeated at 8,192 shots "
               "(next slide). Ideal values: 3.95% plain, 96% for both one-round builds.", IBM)
    text(s, 64, 196, 400, 22, "BUILD", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 480, 196, 400, 22, "CHANCE OF THE CLICK", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 1040, 196, 176, 22, "TWO-QUBIT GATES", size=13, bold=True, color=MUTED, tracking=1.2, align=RIGHT)
    for i, row in enumerate(b["ladder"]):
        y = 228 + i * 70
        rule(s, 64, y, 1216, y)
        ours = i == len(b["ladder"]) - 1
        text(s, 64, y + 8, 410, 54, row["name"], size=20, bold=ours, color=CREAM if i >= 3 else SOFT, anchor=MIDDLE, line=1.1)
        bar(s, 480, y + 20, 440, 30, row["rate"], row["color"])
        text(s, 932, y + 8, 120, 54, pct(row["rate"], 1), size=28, bold=True, color=row["color"] if i >= 3 else CREAM, anchor=MIDDLE)
        text(s, 1040, y + 8, 176, 54, f"{row['gates']}", size=24, color=SOFT, anchor=MIDDLE, align=RIGHT, font="Consolas")
    rule(s, 64, 578, 1216, 578)
    steer, grover = b["ladder"][1], b["ladder"][2]
    takeaway(s, 590, f"Steering costs no gates and lifts {pct(b['ladder'][0]['rate'], 0)} to {pct(steer['rate'], 0)}. "
                     f"Without it, {grover['gates']} gates stall at {pct(grover['rate'], 0)}.", size=23)
    return s


def backup_repeats(prs, e, b, n, index):
    s = backup(prs, n, "on IBM hardware", "Three runs. ", "The lighter build led every time.",
               "The same two compiled circuits, run three times on 11 November 2026. The runs are separate and never pooled.",
               "The 8,192-shot repeat was chosen after seeing the first run: a follow-up, not a preregistered test. "
               "Intervals are shot noise only. Routing, width and timing differ between the two circuits.", IBM)
    text(s, 64, 192, 250, 22, "RUN", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 330, 192, 520, 22, f"CHANCE OF THE CLICK · LOCAL ({e['local_gates']} GATES) AND FULL ({e['full_gates']})", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 884, 192, 120, 22, "LEAD", size=13, bold=True, color=MUTED, tracking=1.2, align=RIGHT)
    text(s, 1016, 192, 200, 22, "ANSWER ERROR", size=13, bold=True, color=MUTED, tracking=1.2, align=RIGHT)
    for i, run in enumerate(b["runs"]):
        y = 222 + i * 120
        rule(s, 64, y, 1216, y)
        text(s, 64, y + 20, 256, 32, run["name"], size=23, bold=True, color=CREAM)
        text(s, 64, y + 56, 256, 44, f"{run['shots']:,} shots · {run['note']}", size=15, color=MUTED, line=1.1)
        for j, (key, color) in enumerate((("local", CYAN), ("full", AMBER))):
            yy = y + 22 + j * 40
            bar(s, 330, yy, 430, 28, run[key], color)
            text(s, 772, yy - 6, 110, 40, pct(run[key]), size=22, bold=True, color=color, anchor=MIDDLE)
        text(s, 884, y + 30, 120, 60, f"+{points(run['local'] - run['full'])}", size=34, bold=True, color=CREAM, anchor=MIDDLE, align=RIGHT)
        text(s, 1016, y + 30, 200, 60, [[(f"{run['tv'][0]:.3f}", {"color": CYAN}), ("  /  ", {"color": MUTED}), (f"{run['tv'][1]:.3f}", {"color": AMBER})]],
             size=24, bold=True, anchor=MIDDLE, align=RIGHT)
    rule(s, 64, 582, 1216, 582)
    leads = sorted(run["local"] - run["full"] for run in b["runs"])
    takeaway(s, 594, f"The lead was {points(leads[0])} to {points(leads[-1])} points. Error suppression did not improve the answer.", size=23)
    return s


def backup_noise(prs, e, b, n, index):
    s = backup(prs, n, "on IBM hardware", "The same noise model, ", "circuit by circuit.",
               "After-click answer at step 6. Exact: 4.67% with the defect and 10.10% without. The model was fitted only on echo circuits.",
               "hardware_campaign/noise_model/results.json. One scale factor stands in for everything the model leaves out. "
               f"Local build, measured difference: {100 * b['local_contrast']['difference']:.2f} points (95% shot interval "
               f"{100 * b['local_contrast']['interval'][0]:.2f} to {100 * b['local_contrast']['interval'][1]:.2f}).".replace("-", "−"), IBM)
    columns = [("Build", 64, 260, LEFT), ("Two-qubit gates", 330, 170, RIGHT), ("Predicted", 520, 220, RIGHT),
               ("Measured", 760, 220, RIGHT), ("Order on the chip", 1000, 216, RIGHT)]
    for name, x, w, align in columns:
        text(s, x, 196, w, 24, name.upper(), size=13, bold=True, color=MUTED, tracking=1.2, align=align)
    rows = [("Plain sampling", "loop-defect-r0", "loop-nodefect-r0"), ("Steer + local reflection", "loop-defect-r1", "loop-nodefect-r1"),
            ("Steer + full reflection", "loop-defect-full-r1", "loop-nodefect-full-r1"),
            ("Memory-only control", "loop-defect-memory-r1", "loop-nodefect-memory-r1")]
    for i, (name, d, nd) in enumerate(rows):
        y = 232 + i * 96
        rule(s, 64, y, 1216, y)
        dd, nn = e["loops"][d], e["loops"][nd]
        step6 = lambda row, key: row[key]["later_click_rates"][2]  # noqa: E731
        right = step6(dd, "measured") < step6(nn, "measured") and "memory" not in d
        verdict = "wrong by design" if "memory" in d else "right" if right else "reversed"
        strong = "local" in name
        text(s, 64, y + 26, 262, 44, name, size=21, bold=strong, color=CREAM if strong else SOFT, anchor=MIDDLE)
        text(s, 330, y + 26, 170, 44, f"{dd['two_qubit_gates']} / {nn['two_qubit_gates']}", size=21, color=SOFT, align=RIGHT, anchor=MIDDLE)
        text(s, 520, y + 26, 220, 44, f"{pct(step6(dd, 'echo_scaled'), 1)} / {pct(step6(nn, 'echo_scaled'), 1)}", size=21, color=SOFT, align=RIGHT, anchor=MIDDLE)
        text(s, 760, y + 26, 220, 44, f"{pct(step6(dd, 'measured'), 1)} / {pct(step6(nn, 'measured'), 1)}", size=21, bold=True, color=CREAM, align=RIGHT, anchor=MIDDLE)
        text(s, 1000, y + 26, 216, 44, verdict, size=21, bold=True, color=GREEN if verdict == "right" else AMBER, align=RIGHT, anchor=MIDDLE)
    rule(s, 64, 616, 1216, 616)
    text(s, 64, 622, 1152, 36, "Each pair is: with the defect / emitter only. Plain sampling fails because false clicks swamp a 4% event.",
         size=17, color=SOFT, anchor=MIDDLE)
    return s


def backup_deep(prs, e, b, n, index):
    s = backup(prs, n, "on IBM hardware", "Deeper circuits ", "returned noise. We kept them.",
               "A three-bin optical model compiled for IBM Marrakesh: one amplification round, 512 shots each, beside our two featured circuits.",
               "Error is the total-variation distance of the measured data-register probabilities from the circuit's target, not a state fidelity. "
               "hardware_campaign/runs/optical_dilation_plain_v2/analysis.json", IBM)
    rows = [("Our lighter build", e["local_gates"], f"{pct(e['local_rate'], 1)} of shots hit the click", CYAN),
            ("Textbook build", e["full_gates"], f"{pct(e['full_rate'], 1)} of shots hit the click", AMBER)]
    for row in b["deep"]:
        rows.append((f"Optical query, cutoff {row['cutoff']} · {row['qubits']} qubits", row["gates"],
                     f"{row['accepted']} of {row['shots']} shots accepted", RED))
    top = math.log10(100000)
    text(s, 64, 196, 380, 22, "CIRCUIT", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 470, 196, 420, 22, "TWO-QUBIT GATES · LOG SCALE", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 900, 196, 316, 22, "WHAT CAME BACK", size=13, bold=True, color=MUTED, tracking=1.2)
    for i, (name, gates, result, color) in enumerate(rows):
        y = 228 + i * 64
        rule(s, 64, y, 1216, y)
        text(s, 64, y + 6, 400, 52, name, size=19, color=CREAM, anchor=MIDDLE, line=1.1)
        bar(s, 470, y + 18, 300, 28, math.log10(gates) / top, color)
        text(s, 782, y + 6, 110, 52, f"{gates:,}", size=22, bold=True, color=color, anchor=MIDDLE, font="Consolas")
        text(s, 900, y + 6, 316, 52, result, size=18.5, color=SOFT, anchor=MIDDLE, line=1.1)
    rule(s, 64, 484, 1216, 484)
    d0, d1 = b["deep"]
    cards = [("Zero hits proves little.", f"Even a perfect chip expects {d0['ideal'] * d0['shots']:.2f} hits in {d0['shots']} shots: "
              f"the event has a {pct(d0['ideal'], 3)} chance.", CREAM),
             ("The distribution is far off.", f"Measured against target: error {d0['tv']:.2f} and {d1['tv']:.2f}. "
              "A better mathematical model did not give a more useful hardware answer.", AMBER)]
    for i, (head, body, color) in enumerate(cards):
        x = 64 + i * 588
        panel(s, x, 500, 564, 148)
        text(s, x + 22, 510, 520, 36, head, size=23, bold=True, color=color, anchor=MIDDLE)
        text(s, x + 22, 550, 520, 92, body, size=17, color=SOFT, line=1.18)
    return s


def backup_coverage(prs, e, b, n, index):
    c = b["campaign"]
    s = backup(prs, n, "on IBM hardware", "What ran on IBM, ", "and where it stops.",
               f"{c['jobs']} jobs on ibm_marrakesh: {c['science']} science circuits and {c['calibration']} calibration circuits, "
               f"{c['shots']:,} shots, {c['seconds']} seconds of processor time.",
               "hardware_campaign/results.json, coverage.json and RESULTS.md. Executions include repeats: "
               f"{c['science']} circuit runs are not {c['science']} findings.", IBM)
    columns = [("Research family", 0.24, LEFT), ("What ran, or was built", 0.38, LEFT), ("Where it stops", 0.38, LEFT)]
    rows = [[("The original QRSM query", {"color": CREAM, "bold": True}), "The full original suite, then an 8,192-shot repeat", "The answers are biased, and routing still matters"],
            [("Quantum-dot, atomic and photon models", {"color": CREAM, "bold": True}), "Prepared states, channels and joint readout", "Digital emulation: no optical setup was involved"],
            [("Spatial and long queries", {"color": CREAM, "bold": True}), "Small models, plus deeper stress circuits", "A high hit rate can hide a wrong answer"],
            [("The full 49-cell exposure", {"color": CREAM, "bold": True}), "A 389-qubit circuit, constructed and checked",
             (f"Does not fit: the device has {c['device_qubits']} qubits", {"color": AMBER, "bold": True})]]
    bottom = table(s, 64, 196, 1152, columns, rows, row_h=84, size=18.5)
    takeaway(s, bottom + 12, f"All {c['families']} research families have a written ledger of evidence and gaps.", size=23)
    return s


# ---------------------------------------------------------------------------- method and credit


def backup_step(prs, e, b, n, index):
    s = backup(prs, n, "method", "One step of the machine, ", "in gates and in maths.",
               footer="rewindandamplify-main/qrsm_grover/model.py. Steps are dimensionless. The optical labels are an interpretation "
                      "of the model: the IBM circuits did not measure photon arrivals.")
    picture(s, "circuit.png", 64, 136, w=600, h=250)
    sub = {"sub": True}
    lines = [("One step", ["U = Exchange(φ) · RZ(ζ) · RY(θ)"], CREAM),
             ("No click", ["K", ("0", sub), " = (|0⟩⟨0| + cos α |1⟩⟨1|) U"], CREAM),
             ("Click", ["K", ("1", sub), " = sin α |0⟩⟨1| U,   sin² α = γ"], AMBER),
             ("A record", ["P(y", ("1", sub), " … y", ("T", sub), ") = ‖ K(y", ("T", sub), ") ⋯ K(y", ("1", sub), ") |00⟩ ‖²"], CYAN)]
    panel(s, 688, 136, 528, 250)
    for i, (label, formula, color) in enumerate(lines):
        y = 150 + i * 57
        text(s, 708, y, 110, 48, label.upper(), size=12.5, bold=True, color=MUTED, tracking=1.2, anchor=MIDDLE)
        text(s, 820, y, 388, 48, [formula], size=19, color=color, anchor=MIDDLE, font="Cambria Math")
    cards = [("Dynamic version", "3 qubits", "Measure the light qubit and reset it every step. Simple, but a reset cannot be undone.", SOFT),
             ("Purified version", "2 + T qubits", "Keep each step's light in a fresh qubit and measure at the end. "
              "One reversible circuit, with identical click statistics.", CYAN),
             ("What a click does", "back-action", "K₁ empties the emitter and leaves the defect conditioned on the record. "
              "No click also updates the state. That is the recurrent update.", AMBER)]
    for i, (head, big, body, color) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 404, 368, 244)
        text(s, x + 20, 416, 328, 24, head.upper(), size=13, bold=True, color=MUTED, tracking=1.3)
        text(s, x + 20, 444, 328, 52, big, size=36, bold=True, color=color, anchor=MIDDLE)
        text(s, x + 20, 504, 328, 136, body, size=17, color=SOFT, line=1.2)
    return s


def backup_reproduce(prs, e, b, n, index):
    s = backup(prs, n, "method", "Anyone can rerun it. ", "One command.",
               footer="No IBM account, no network. Model numbers are recomputed with Qiskit; measured numbers are recounted "
                      "from the saved raw counts.")
    panel(s, 64, 130, 1152, 518, fill=RGBColor(0x05, 0x0D, 0x16))
    lines = ["$ python reproduce.py",
             "",
             "1. The exact model                       with the defect   emitter only",
             f"   click at step 6, given one at step 3          {pct(e['answer_defect']):>6s}        {pct(e['answer_none']):>6s}",
             "",
             "2. The Qiskit circuits on Aer             hit rate   answer error",
             f"   plain sampling                           {pct(e['p_click']):>6s}         0.0000",
             f"   steer + full reflection, 1 round         {pct(e['ideal_full']):>6s}         0.0000",
             f"   steer + local reflection, 1 round        {pct(e['ideal_local']):>6s}         {e['ideal_local_tv']:.4f}",
             "",
             "3. Classical baseline: exact sampler, a fraction of a millisecond per sample",
             "",
             f"4. IBM Marrakesh, job {e['job_id']}     ideal   noise model   measured",
             f"   steer + local reflection   {e['local_gates']:>3d} gates    {pct(e['nm']['local']['ideal']):>6s}     {pct(e['nm']['local']['echo_scaled']):>6s}     {pct(e['local_rate']):>6s}",
             f"   steer + full reflection    {e['full_gates']:>3d} gates    {pct(e['nm']['full']['ideal']):>6s}     {pct(e['nm']['full']['echo_scaled']):>6s}     {pct(e['full_rate']):>6s}",
             "",
             "Done in about 10 s. Nothing above claims a quantum speedup."]
    text(s, 88, 146, 1104, 490, [[(line or " ", {"color": CYAN if line.startswith("$") else CREAM})] for line in lines],
         size=18.5, font="Consolas", line=1.24)
    return s


def backup_rubric(prs, e, b, n, index):
    s = backup(prs, n, "method", "The rubric, ", "and where each point is answered.",
               footer=f"Bonus: simulator +1 (slides 7, 9). Real IBM hardware +3 (slide 8). Hardware compared with a simulator, noise analysed, "
                      f"suppression tried +5 (slides 9, {index['repeats']}, {index['noise']}). Evidence for the judges, not a predicted score.")
    columns = [("Criterion", 0.34, LEFT), ("Points", 0.1, RIGHT), ("Where the talk answers it", 0.56, LEFT)]
    first, last = min(index.values()), max(index.values())
    rows = [("A clear problem, and who it affects", "15", "Slides 2, 4 and 11: the hidden defect, who has the problem, two futures"),
            ("Why quantum, and honest limits", "20", "Slides 5, 6, 7, 9 and 12: the cost of rarity, two catches, no speedup today"),
            ("Qiskit implementation that runs", "20", f"Slides 3, 7, 8 and 10; backups {index['step']} and {index['reproduce']}: gates, four moves, one command"),
            ("Results, interpreted and validated", "10", f"Slides 4, 8 and 9; backups {index['ladder']} to {index['noise']}: exact, simulator, noise model, hardware"),
            ("Originality", "10", f"Slides 7 and 13; backup {index['credit']}: the reversible recurrent model and the noise-aware build"),
            ("Clear to every audience", "15", "13 main slides, one picture each; the Lab's plain and technical captions"),
            ("Questions, teamwork, learning", "10", f"Slide 13; backups {first} to {last}: roles, lessons, and a slide for each likely question")]
    cells = [[(name, {"color": CREAM, "bold": True}), (pts, {"color": CYAN, "bold": True, "size": 24}), where] for name, pts, where in rows]
    table(s, 64, 132, 1152, columns, cells, row_h=68, size=18.5)
    return s


def backup_credit(prs, e, b, n, index):
    s = backup(prs, n, "method", "What is ours, ", "what is prior work, and where AI helped.",
               footer="Atomic laser-noise spectroscopy also predates this project (Bishof et al. 2013). No new sensing principle is claimed. "
                      "“Independent checks” means separate implementations inside the project, not external peer review.", title_size=38)
    columns = [("Origin", 0.26, LEFT), ("What belongs there", 0.74, LEFT)]
    rows = [("Established prior work", "Amplitude amplification (Brassard et al. 2002) and amplified conditional inference (Low, Yoder, Chuang 2014)", MUTED),
            ("Before the event", "The QRSM idea, the physics-shaped model and its exact filter", SOFT),
            ("The hackathon project", "The Qiskit build, the fusion with Grover, steering, the local reflection, and the experiments", CYAN),
            ("Finals work", "Model audits, the joint-photon model, the IBM Marrakesh campaign, the noise model and the Lab", CYAN),
            ("AI assistance", "Original project and V3: Claude. V2 research extensions: Codex with OpenAI models. "
             "The team set the questions and reviewed the results.", AMBER)]
    cells = [[(origin, {"color": color, "bold": True}), what] for origin, what, color in rows]
    bottom = table(s, 64, 132, 1152, columns, cells, row_h=84, size=19)
    takeaway(s, bottom + 12, "A sensing benefit and a computing speedup are separate claims. We make neither today.", size=23)
    return s


def backup_cinematic(prs, e, b, n, index, video: Path, poster: Path):
    s = backup(prs, n, "optional cold open", "The cinematic cut. ", "45 seconds.",
               footer="A cinematic explainer with original music, not a screen recording of the product. "
                      "The model picture is conceptual; the IBM numbers are the measured ones.")
    s.shapes.add_movie(str(video), px(176), px(128), px(928), px(522), poster_frame_image=str(poster), mime_type="video/mp4")
    return s


# ---------------------------------------------------------------------------- numbers for the research backups


def research_evidence() -> dict:
    """Figures quoted on the light, laser and chipmaking backups, each read from the study file that stores it."""
    r = {}
    # light: detector dead time, photon pairs, published GaAs data, the joint-photon model, cavity truncation
    fits = "qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit{}.json"
    ignored, aware = load(fits.format(0)), load(fits.format(1))
    review = load("qrsm_photon_poc/followup/independent_review.json")["additional_descriptive_deadtime_comparison"]
    r["deadtime"] = {"truth": aware["generator_parameters"]["g_defect"], "ignored": ignored["joint_parameters"]["g_defect"],
                     "modelled": aware["joint_parameters"]["g_defect"], "bins": ignored["config"]["bins"],
                     "vs_hmm": [ignored["paired"]["joint_minus_hmm"]["mean_delta_nats_per_record"],
                                aware["paired"]["joint_minus_hmm"]["mean_delta_nats_per_record"]],
                     "gain": review["corrected_minus_omitted_mean_nats_per_record"]}
    dot = load("quantum_dot_bridge/results.json")
    trap, loss = dot["classical_trap_pair_comparison"], dot["collection_loss_sweep"]
    families = load("hardware_campaign/results.json")["family_results"]
    frozen = {row["name"]: row["observables"] for row in families["dot_frozen"] if row["run"] == "dots_plain_v1"}
    attempts = {round(row["single_photon_survival_probability"], 3): row["expected_excitation_pairs_per_surviving_pair"]
                for row in loss if row["expected_excitation_pairs_per_surviving_pair"]}
    r["pairs"] = {"overlap": [trap[0]["conditional_overlap"], trap[-1]["conditional_overlap"]],
                  "coincidence": [trap[0]["coincidence_probability_per_excitation_pair"], trap[-1]["coincidence_probability_per_excitation_pair"]],
                  "survival": trap[0]["single_photon_survival_probability"],
                  "ibm": [frozen["frozen_pair_p0"]["raw_swap_overlap_estimate"], frozen["frozen_pair_p0.5"]["raw_swap_overlap_estimate"]],
                  "attempts": [attempts[0.8], attempts[0.2]]}
    hom = load("quantum_dot_bridge/hom_analysis/results.json")
    r["gaas"] = [{"ns": case["excitation_separation_ns"], "v": case["primary"]["corrected_visibility"],
                  "ci": case["primary"]["corrected_interval95"], "co_only": case["primary"]["co_only_corrected_visibility"]}
                 for case in hom["cases"]]
    joint = load("quantum_dot_bridge/qrsm_hom_followup/main/results.json")["regimes"][1]["cases"]
    four = {row["name"]: row["observables"]["flag_history_tv"] for row in families["dot_selected_four_pair"]}
    r["joint"] = {"flags": [joint[0]["flag_rate"], joint[1]["flag_rate"]],
                  "ibm_tv": [four["selected_four_coherent"], four["selected_four_classical"]]}
    trials = load("quantum_dot_bridge/qrsm_hom_followup/exploratory_design/validation_run/results.json")["power_trials"]
    r["power"] = [{"pairs": t["attempted_pairs"], "coherent": t["cases"][0]["flag_rate"], "classical": t["cases"][1]["flag_rate"]} for t in trials]
    r["power_failures"] = {"collection": trials[-1]["cases"][3]["flag_rate"], "overlap": trials[-1]["cases"][4]["flag_rate"],
                           "readout": trials[-1]["cases"][2]["flag_rate"], "records": trials[-1]["cases"][0]["records"]}
    cutoff = load("qrsm_photon_poc/followup/dynamics_results.json")["cutoff"]
    r["truncation"] = [{"levels": int(n), "default": cutoff["default"]["dimensions"][n]["max_conditional_difference_vs_dimension6"],
                        "high": cutoff["high_drive"]["dimensions"][n]["max_conditional_difference_vs_dimension6"]} for n in ("2", "4", "5")]
    # lasers: the monitoring study, the drive-amplitude study, the atomic channel on IBM
    base = load("laser_sensor_viability/results.json")
    r["sensor"] = {**{k: base["config"][k] for k in ("wavelength_nm", "atoms", "pulse_s", "dark_s", "t1_s", "t2_s", "readout_01", "readout_10")},
                   "record_s": base["resource_ledger"]["duration_s"], "dead_time_s": base["resource_ledger"]["dead_time_s"]}
    follow = {s["id"]: s for s in load("laser_sensor_viability/followup/main/results.json")["scenarios"]}
    r["stress"] = [{"name": name, "records": follow[key]["records_per_class"],
                    "cells": [(follow[key]["methods"][m]["detection_within_32s"], follow[key]["methods"][m]["false_alarm_rate"])
                              for m in ("classical", "classical_quantum", "two_classical")]}
                   for name, key in (("Everything calibrated", "unseen_nominal_sessions"), ("Atoms lose coherence sooner", "unseen_short_coherence"),
                                     ("The first reference steps", "primary_reference_changes"), ("The shared path steps", "common_sampled_path_changes"))]
    r["atoms_alone"] = follow["unseen_nominal_sessions"]["methods"]["quantum"]["detection_within_32s"]
    drive = load("qrsm_photon_poc/drive_diagnostics_followup/main/results.json")["cases"]
    prior = load("qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_estimation_control.json")["cases"]["source_step_20pct"]
    r["drive"] = {"rows": [(name, drive["source_step_20pct"]["methods"][m]["detection_within32"]["value"],
                            drive["stable_source"]["methods"][m]["record_alarm_fraction"]["value"])
                           for name, m in (("Physical QRSM", "physical_history"), ("Classical hidden-Markov model", "classical_hmm"),
                                           ("Simple count comparison", "count_contrast"))],
                  "rmse": [prior["prior_only_rmse"]["value"], drive["source_step_20pct"]["physical_fraction_rmse"]["value"]],
                  "records": drive["stable_source"]["methods"]["physical_history"]["record_alarm_fraction"]["records"]}
    atomic = {row["name"]: row for row in families["atomic"]}
    photon = {row["name"]: row for row in families["photon"]}
    r["atomic"] = {"rows": [(hz, atomic[name]["observables"]["ideal_system_zero_probability"], atomic[name]["observables"]["raw_system_zero_probability"],
                             atomic[name]["observables"]["raw_system_zero_wilson95"]) for hz, name in ((-5, "atomic_d-5_Z"), (0, "atomic_d+0_Z"), (5, "atomic_d+5_Z"))],
                   "qubits": atomic["atomic_d+0_Z"]["logical_qubits"], "gates": atomic["atomic_d+0_Z"]["native_two_qubit_gate_count"],
                   "shots": atomic["atomic_d+0_Z"]["shots"], "noon_tv": photon["noon_phi0.35"]["observables"]["occupancy_tv"]}
    # chipmaking: exposure, phase inspection, and the full spatial query
    exposure = load("quantum_lithography_poc/exposure_followup/results.json")["cases"][1]
    r["exposure"] = [(name, exposure["methods"][m]["best_threshold_accuracy"]["guard_cell_accuracy"],
                      exposure["methods"][m]["best_threshold_accuracy"]["all_guard_cells_correct_probability"],
                      exposure["methods"][m]["best_threshold_accuracy"]["sample_incident_photons"])
                     for name, m in (("Entangled pairs", "noon"), ("Laser, two shifted exposures", "phase_cycled"), ("Laser, short pulses", "phase_cycled_burst"))]
    phase_cases = load("quantum_lithography_poc/phase_inspection_followup/results.json")["cases"]
    budget = phase_cases[1]["budgets"]["equal_sample_photons"]
    slow = phase_cases[5]["budgets"]["equal_sample_photons"]
    r["phase"] = {"rows": [(name, budget[m]["global"]["rmse_full_2pi_rad"], budget[m]["global"]["wrong_pi_branch_rate"], budget[m]["global"]["repetitions"])
                           for name, m in (("Laser light", "coherent"), ("Entangled pairs alone", "noon"), ("10% laser + 90% pairs", "hybrid"))],
                  "efficiency": phase_cases[1]["setup"]["object_transmission"] * phase_cases[1]["setup"]["detection_efficiency"],
                  "photons": budget["coherent"]["resources"]["sample_incident_mean_photons_before_object"],
                  "slowdown": slow["noon"]["resources"]["elapsed_seconds_at_assumed_clock"] / slow["coherent"]["resources"]["elapsed_seconds_at_assumed_clock"]}
    spatial = load("finals-lithography/full_spatial_circuit/results.json")
    floor = spatial["circuits"][1]
    r["spatial"] = {"cells": spatial["configuration"]["cells"], "qubits": floor["qubits"],
                    "parts": [floor["metadata"][k] for k in ("data_qubits", "score_qubits", "extra_clean_qubits")],
                    "cx": [spatial["explicit_synthesis_costs"][k]["complete_one_round_generic_cx_constructive_upper_bound"] for k in ("floor", "ceil")],
                    "event": spatial["bounds"][0]["finite_capped_integer_lattice_cdf"]["floor"],
                    "device": load("hardware_campaign/coverage.json")["confirmed_device_qubits"]}
    # the figures the old deck quoted, so a changed key or file fails here and not on stage
    assert [f"{v:.3f}" for v in (r["deadtime"]["ignored"], r["deadtime"]["modelled"])] == ["0.069", "0.706"]
    assert [f"{v:.4f}" for v in r["deadtime"]["vs_hmm"]] == ["-0.4506", "0.0078"] and f"{r['deadtime']['gain']:.4f}" == "0.4584"
    assert r["pairs"]["overlap"] == [1.0, 0.6] and [round(v, 4) for v in r["pairs"]["attempts"]] == [1.5625, 25.0]
    assert [f"{g['v']:.4f}" for g in r["gaas"]] == ["0.8024", "0.8258", "0.7724"] and f"{r['gaas'][2]['co_only']:.4f}" == "0.7938"
    assert r["joint"]["flags"] == [0.056, 0.045] and [f"{v:.3f}" for v in r["joint"]["ibm_tv"]] == ["0.249", "0.286"]
    assert [t["pairs"] for t in r["power"]] == [64, 256, 1024, 2584, 4096, 7644] and r["power"][-1]["coherent"] == 0.998
    assert (r["power_failures"]["collection"], r["power_failures"]["overlap"], r["power_failures"]["readout"]) == (0.72, 0.5325, 0.2105)
    assert [f"{100 * t['default']:.4f}" for t in r["truncation"]] == ["2.7643", "0.0494", "0.0028"]
    assert [f"{100 * c[0]:.1f}" for c in r["stress"][0]["cells"]] == ["51.4", "58.0", "98.0"]
    assert [f"{100 * row[1]:.2f}" for row in r["drive"]["rows"]] == ["3.71", "3.12", "1.76"]
    assert [f"{100 * row[1]:.2f}" for row in r["atomic"]["rows"]] == ["20.86", "50.00", "79.14"] and (r["atomic"]["qubits"], r["atomic"]["gates"]) == (4, 22)
    assert [f"{100 * row[1]:.2f}" for row in r["exposure"]] == ["95.16", "78.28", "83.29"]
    assert [row[2] for row in r["phase"]["rows"]] == [0.0, 0.504, 0.0] and round(r["phase"]["slowdown"]) == 100 and round(r["phase"]["efficiency"], 2) == 0.81
    assert r["spatial"]["qubits"] == sum(r["spatial"]["parts"]) == 389 and r["spatial"]["device"] == 156
    return r


# ---------------------------------------------------------------------------- light: photons and detectors


def backup_pairs(prs, e, b, n, index):
    r = b["research"]["pairs"]
    s = backup(prs, n, "light", "Equally bright. ", "Not equally good.",
               "Two model photon sources send the same number of photons in the same mix of colours. Only the pairs differ.",
               f"A classical two-state environment, {pct(r['survival'], 0)} photon survival, ideal single photons. No semiconductor defect "
               "was identified. quantum_dot_bridge/results.json; picture captured from the Lab.", SIM)
    shot = picture(s, "photons.png", 64, 196, w=700, h=392)
    x = 64 + shot.width / 9525 + 24
    w = 1216 - x
    for i, (name, color, note) in enumerate((("Source A · environment holds still", CYAN, f"photon overlap {r['overlap'][0]:.2f}"),
                                             ("Source B · environment forgets", AMBER, f"photon overlap {r['overlap'][1]:.2f}"))):
        y = 196 + i * 138
        panel(s, x, y, w, 126, outline=color)
        text(s, x + 20, y + 10, w - 40, 22, name.upper(), size=12.5, bold=True, color=MUTED, tracking=1.2)
        text(s, x + 20, y + 34, 180, 56, pct(r["coincidence"][i], 1), size=48, bold=True, color=color, anchor=MIDDLE)
        text(s, x + 204, y + 40, w - 224, 50, "of attempts put one photon in each detector", size=15.5, color=SOFT, line=1.12, anchor=MIDDLE)
        text(s, x + 20, y + 94, w - 40, 22, note, size=14.5, color=SOFT)
    panel(s, x, 472, w, 116, outline=GREEN)
    text(s, x + 20, 482, w - 40, 22, "THE SAME TWO CASES, AS CIRCUITS ON IBM", size=12.5, bold=True, color=GREEN, tracking=1.2)
    text(s, x + 20, 506, w - 40, 44, [[(f"{r['ibm'][0]:.2f}", {"color": CYAN}), ("  vs  ", {"color": MUTED, "size": 20}), (f"{r['ibm'][1]:.2f}", {"color": AMBER})]],
         size=34, bold=True, anchor=MIDDLE)
    text(s, x + 20, 552, w - 40, 28, f"measured overlap · ideal {r['overlap'][0]:.2f} and {r['overlap'][1]:.2f}", size=14.5, color=SOFT)
    takeaway(s, 604, "One detector alone sees no difference. The pair pattern does.", size=23)
    return s


def backup_gaas(prs, e, b, n, index):
    rows = b["research"]["gaas"]
    s = backup(prs, n, "light", "A real quantum dot: ", "published data, reanalysed.",
               "How well two photons from a GaAs quantum dot interfere, at three delays between them. Measured by Münzberg et al. (2022), CC BY 4.0.",
               "Our peak-area reanalysis of their published histograms: not our measurement, and not a QRSM fit. Intervals cover counting and "
               "calibration only. quantum_dot_bridge/hom_analysis/results.json", DATA)
    lo, hi, x0, w = 0.74, 0.86, 330, 640
    X = lambda v: x0 + (v - lo) / (hi - lo) * w  # noqa: E731
    text(s, 64, 196, 250, 22, "DELAY BETWEEN PHOTONS", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, x0, 196, w, 22, "INTERFERENCE VISIBILITY · 95% INTERVAL", size=13, bold=True, color=MUTED, tracking=1.2)
    for tick in (0.74, 0.78, 0.82, 0.86):
        rule(s, X(tick), 228, X(tick), 500, color=SLATE)
        text(s, X(tick) - 30, 504, 60, 20, f"{tick:.2f}", size=14, color=MUTED, align=CENTER, font="Consolas")
    for i, row in enumerate(rows):
        y = 262 + i * 86
        text(s, 64, y - 22, 250, 44, f"{row['ns']:.1f} ns", size=28, bold=True, color=CREAM, anchor=MIDDLE)
        panel(s, X(row["ci"][0]), y - 4, X(row["ci"][1]) - X(row["ci"][0]), 8, fill=VIOLET, outline=None, radius=0.5)
        panel(s, X(row["v"]) - 10, y - 10, 20, 20, fill=CREAM, outline=VIOLET, radius=0.5, width=2)
        text(s, x0 + w + 24, y - 22, 220, 44, f"{row['v']:.3f}", size=30, bold=True, color=VIOLET, anchor=MIDDLE)
    last = rows[-1]
    y = 262 + 2 * 86
    panel(s, X(last["co_only"]) - 9, y - 9, 18, 18, fill=None, outline=AMBER, radius=0.5, width=2)
    text(s, X(last["co_only"]) - 150, y + 14, 300, 22, f"other normalization: {last['co_only']:.3f}", size=14.5, color=AMBER, align=CENTER)
    shift, half = last["co_only"] - last["v"], (last["ci"][1] - last["ci"][0]) / 2
    takeaway(s, 548, f"At {last['ns']:.1f} ns, changing the normalization moves the answer by {shift:.3f}. The interval is ±{half:.3f}.", size=23)
    text(s, 64, 592, 1152, 50, "A source-quality number depends on the measurement controls. That discrepancy says: check polarization, alignment "
         "and normalization before naming a cause.", size=17, color=SOFT, line=1.18)
    return s


def backup_deadtime(prs, e, b, n, index):
    r = b["research"]["deadtime"]
    s = backup(prs, n, "light", "Ignore the detector’s blind time, ", "and the fit is wrong.",
               f"Fresh synthetic click records with a known defect coupling of {r['truth']:.2f}. The same records, fitted twice.",
               f"{r['bins']}-bin records. Synthetic inference, not a diagnosis of a physical defect. The corrected fit still pins dephasing at its bound. "
               "qrsm_photon_poc/followup/", SIM, title_size=38)
    x0, w, y = 150, 980, 300
    X = lambda v: x0 + v * w  # noqa: E731
    text(s, 64, 196, 600, 22, "FITTED DEFECT COUPLING", size=13, bold=True, color=MUTED, tracking=1.2)
    panel(s, x0, y - 3, w, 6, fill=TRACK, outline=None, radius=0.5)
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        rule(s, X(tick), y - 10, X(tick), y + 10, color=SLATE)
        text(s, X(tick) - 30, y + 16, 60, 20, f"{tick:.2f}", size=14, color=MUTED, align=CENTER, font="Consolas")
    rule(s, X(r["truth"]), y - 62, X(r["truth"]), y + 12, color=CREAM, width=2)
    text(s, X(r["truth"]) - 110, y - 88, 220, 24, f"true value {r['truth']:.2f}", size=16, color=CREAM, align=CENTER, bold=True)
    for value, color, label in ((r["ignored"], AMBER, "blind time ignored"), (r["modelled"], CYAN, "blind time modelled")):
        panel(s, X(value) - 13, y - 13, 26, 26, fill=color, outline=None, radius=0.5)
        left = value < 0.5
        text(s, X(value) + (22 if left else 22), y - 60 if left else y + 36, 300, 30, [[(f"{value:.3f}", {"bold": True, "color": color, "size": 26}), (f"   {label}", {"color": SOFT})]],
             size=17, anchor=MIDDLE)
    cards = [(f"{r['vs_hmm'][0]:+.3f}".replace("-", "−"), "nats per record against a classical hidden-Markov model, with the blind time ignored: clearly worse", AMBER),
             (f"{r['vs_hmm'][1]:+.3f}", "once the blind time is modelled: level with the classical model, within uncertainty", CYAN),
             (f"{r['gain']:.3f}", "nats per record gained just by modelling the detector properly", CREAM)]
    for i, (big, small, color) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 404, 368, 150)
        text(s, x + 20, 414, 328, 54, big, size=40, bold=True, color=color, anchor=MIDDLE)
        text(s, x + 20, 472, 328, 76, small, size=15.5, color=SOFT, line=1.16)
    takeaway(s, 580, "After a click the detector is blind for one step. Leave that out, and the model blames the defect.", size=22)
    return s


def backup_joint(prs, e, b, n, index):
    r = b["research"]["joint"]
    s = backup(prs, n, "light", "A QRSM for photon pairs: ", "memory between pairs.",
               "A model in which the hidden environment persists from one photon pair to the next, so a run of outcomes can carry memory.",
               "quantum_dot_bridge/qrsm_hom_followup/. Flags are a calibrated test for coherent memory. The IBM error is the distance of measured "
               "from ideal flag probabilities. Neither identifies a physical defect.", SIM)
    steps = [("1", "Emit each photon", "Its shape in time depends on the state of the environment."),
             ("2", "Observe a pair", "A controlled-swap parity check gives the beam-splitter statistic."),
             ("3", "Predict the next pair", "The environment is kept, so the record so far shapes what comes next.")]
    for i, (num, head, body) in enumerate(steps):
        x = 64 + i * 392
        panel(s, x, 196, 368, 170)
        text(s, x + 18, 208, 44, 44, num, size=34, bold=True, color=CYAN, anchor=MIDDLE)
        text(s, x + 66, 208, 286, 44, head, size=22, bold=True, color=CREAM, anchor=MIDDLE)
        text(s, x + 18, 262, 332, 96, body, size=17, color=SOFT, line=1.2)
    results = [("Simulation, 64 pairs per record", [(pct(r["flags"][0], 1), CYAN), (" vs ", MUTED), (pct(r["flags"][1], 1), AMBER)],
                "of records flagged: coherent source, then a classical one. Barely apart."),
               ("Four pairs, as circuits on IBM", [(f"{r['ibm_tv'][0]:.2f}", CYAN), (" and ", MUTED), (f"{r['ibm_tv'][1]:.2f}", AMBER)],
                "error of the measured flag distribution. Implementation noise is still large.")]
    for i, (head, big, small) in enumerate(results):
        x = 64 + i * 588
        panel(s, x, 384, 564, 170, outline=GREEN if i else SLATE)
        text(s, x + 22, 396, 520, 22, head.upper(), size=12.5, bold=True, color=GREEN if i else MUTED, tracking=1.2)
        text(s, x + 22, 422, 520, 60, [[(value, {"color": color, "size": 44 if color != MUTED else 22}) for value, color in big]], size=44, bold=True, anchor=MIDDLE)
        text(s, x + 22, 488, 520, 56, small, size=16.5, color=SOFT, line=1.16)
    takeaway(s, 580, f"With 64 pairs the test hardly fires. See slide {index['calibration']} for what more data buys, and what it does not.", size=22)
    return s


def backup_calibration(prs, e, b, n, index):
    r, f = b["research"]["power"], b["research"]["power_failures"]
    s = backup(prs, n, "light", "More data helps ", "only if the calibration holds.",
               f"Simulated records flagged as carrying coherent memory, by photon pairs per record ({f['records']:,} records each).",
               "A selected control and ideal resets between four-pair blocks: a different protocol from the 64-pair study. A stronger 8-state "
               "classical model predicts as well within uncertainty. quantum_dot_bridge/qrsm_hom_followup/exploratory_design/", SIM)
    x0, base_y, top_y, step = 96, 520, 236, 104
    rule(s, 64, base_y, 720, base_y)
    for level in (0.5, 1.0):
        yy = base_y - level * (base_y - top_y)
        rule(s, 64, yy, 720, yy, color=SLATE, dashed=True)
        text(s, 660, yy - 20, 60, 18, pct(level, 0), size=13, color=MUTED, align=RIGHT, font="Consolas")
    for i, row in enumerate(r):
        x = x0 + i * step
        h = row["coherent"] * (base_y - top_y)
        panel(s, x, base_y - h, 52, max(h, 2), fill=CYAN, outline=None, radius=0.08)
        hf = row["classical"] * (base_y - top_y)
        panel(s, x + 58, base_y - hf, 20, max(hf, 2), fill=AMBER, outline=None, radius=0.1)
        text(s, x - 22, base_y - h - 30, 96, 26, pct(row["coherent"], 1), size=17, bold=True, color=CYAN, align=CENTER)
        text(s, x - 22, base_y + 8, 96, 24, f"{row['pairs']:,}", size=16, color=CREAM, align=CENTER, font="Consolas")
    text(s, 64, base_y + 34, 656, 22, "PHOTON PAIRS PER RECORD", size=12.5, bold=True, color=MUTED, tracking=1.2, align=CENTER)
    text(s, 64, 176, 656, 22, [[("■ ", {"color": CYAN}), ("COHERENT SOURCE FLAGGED     ", {"color": MUTED}), ("■ ", {"color": AMBER}),
                               (f"CLASSICAL SOURCE, FLAGGED BY MISTAKE (ABOUT {pct(r[0]['classical'], 0)})", {"color": MUTED})]],
         size=12, bold=True, tracking=0.8)
    x = 756
    panel(s, x, 196, 460, 358, outline=AMBER)
    text(s, x + 22, 208, 416, 46, f"But at {r[-1]['pairs']:,} pairs, a classical source is flagged anyway", size=19, bold=True, color=AMBER, line=1.12)
    for i, (value, label) in enumerate(((f["collection"], "if the collection efficiency changed"), (f["overlap"], "if the mode overlap changed"),
                                         (f["readout"], "if the readout changed"))):
        y = 276 + i * 90
        text(s, x + 22, y, 150, 60, pct(value, 0), size=44, bold=True, color=CREAM, anchor=MIDDLE)
        text(s, x + 180, y, 262, 60, label, size=17, color=SOFT, anchor=MIDDLE, line=1.15)
    takeaway(s, 584, "More data cannot repair a wrong model of the measurement.", size=24)
    return s


def backup_truncation(prs, e, b, n, index):
    rows = b["research"]["truncation"]
    s = backup(prs, n, "light", "A better model ", "costs more qubits.",
               "The optical circuit keeps only a few energy levels of its cavity. Largest error in the after-click prediction, against a six-level reference.",
               "A finite truncation study with a six-level reference, not proof of convergence. The circuits that ran on IBM used two levels. "
               "qrsm_photon_poc/followup/dynamics_results.json", SIM)
    text(s, 64, 196, 200, 22, "CAVITY LEVELS KEPT", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 300, 196, 560, 22, "LARGEST ERROR, IN PERCENTAGE POINTS · LOG SCALE", size=13, bold=True, color=MUTED, tracking=1.2)
    low, high = math.log10(0.001), math.log10(10)
    scale = lambda v: (math.log10(100 * v) - low) / (high - low)  # noqa: E731
    for i, row in enumerate(rows):
        y = 230 + i * 104
        rule(s, 64, y, 1216, y)
        text(s, 64, y + 14, 200, 76, f"{row['levels']}", size=56, bold=True, color=CREAM, anchor=MIDDLE)
        for j, (key, color, label) in enumerate((("default", CYAN, "default drive"), ("high", AMBER, "stronger drive"))):
            yy = y + 20 + j * 38
            bar(s, 300, yy, 560, 24, scale(row[key]), color)
            digits = 2 if 100 * row[key] >= 1 else 3 if 100 * row[key] >= 0.01 else 4
            text(s, 880, yy - 6, 150, 36, f"{100 * row[key]:.{digits}f}", size=22, bold=True, color=color, anchor=MIDDLE, font="Consolas")
            text(s, 1040, yy - 6, 176, 36, label, size=15.5, color=SOFT, anchor=MIDDLE)
    rule(s, 64, 542, 1216, 542)
    takeaway(s, 556, "Two levels are off by several points. Five are accurate, and need more qubits and gates.", size=23)
    text(s, 64, 600, 1152, 46, "Model accuracy is part of the resource budget: the cheap circuit answers a slightly different question.", size=17, color=SOFT)
    return s


# ---------------------------------------------------------------------------- lasers


def backup_stress(prs, e, b, n, index):
    rows = b["research"]["stress"]
    s = backup(prs, n, "lasers", "A calibration slip ", "can reverse the conclusion.",
               f"A laser steps by half a hertz at an unknown time. Drifts caught within 32 seconds, and false alarms on quiet records. "
               f"{rows[0]['records']:,} simulated records per cell.",
               f"Atoms alone caught {pct(b['research']['atoms_alone'], 1)}. Calibration is frozen before the stress cases. "
               "laser_sensor_viability/followup/main/results.json", NEG)
    heads = [("Ordinary reference", SOFT), ("Reference + atoms", CYAN), ("Two ordinary references", AMBER)]
    text(s, 64, 196, 300, 22, "SITUATION", size=13, bold=True, color=MUTED, tracking=1.2)
    for j, (name, color) in enumerate(heads):
        text(s, 392 + j * 280, 196, 260, 22, name.upper(), size=13, bold=True, color=color, tracking=1.2)
    for i, row in enumerate(rows):
        y = 228 + i * 84
        rule(s, 64, y, 1216, y)
        text(s, 64, y + 8, 312, 68, row["name"], size=20, bold=i == 0, color=CREAM, anchor=MIDDLE, line=1.1)
        for j, (caught, false) in enumerate(row["cells"]):
            x = 392 + j * 280
            bar(s, x, y + 16, 150, 22, caught, heads[j][1] if heads[j][1] != SOFT else MUTED)
            text(s, x + 160, y + 6, 100, 42, pct(caught, 1), size=22, bold=True, color=CREAM, anchor=MIDDLE)
            bad = false > 0.5
            text(s, x, y + 46, 260, 26, f"false alarms {pct(false, 1)}", size=15, bold=bad, color=RED if bad else MUTED)
    rule(s, 64, 564, 1216, 564)
    gain = rows[0]["cells"][1][0] - rows[0]["cells"][0][0]
    takeaway(s, 574, f"Calibrated, the atoms add {points(gain)} points and a second reference adds far more. Degraded, the atoms hurt.", size=22)
    text(s, 64, 616, 1152, 30, "A step in the shared path looks exactly like a step in the laser: every monitor raised the alarm.", size=17, color=RED)
    return s


def backup_monitor(prs, e, b, n, index):
    r = b["research"]["sensor"]
    s = backup(prs, n, "lasers", "The laser monitor: ", "what we assumed.",
               footer="Photon allocation is assumed bookkeeping. Reference lasers, cooling, trapping and readout hardware are not costed. "
                      "Atomic laser-noise spectroscopy is prior work (Bishof et al. 2013). laser_sensor_viability/results.json")
    columns = [("Model element", 0.36, LEFT), ("Assumed setting", 0.64, LEFT)]
    rows = [("Laser", f"{r['wavelength_nm']:.0f} nm, narrow-line: a laboratory wavelength atoms can read"),
            ("Atomic sensor", f"{r['atoms']} independent atoms, not entangled"),
            ("One reading", f"{1000 * r['pulse_s']:.1f} ms pulse, {1000 * r['dark_s']:.0f} ms dark time, {1000 * r['pulse_s']:.1f} ms pulse"),
            ("Record", f"{r['record_s']:.0f} s long, with {1000 * r['dead_time_s']:.0f} ms of dead time in every one-second cycle"),
            ("Atom quality", f"coherence {1000 * r['t2_s']:.0f} ms, lifetime {r['t1_s']:.0f} s, readout errors {pct(r['readout_01'], 0)} and {pct(r['readout_10'], 0)}")]
    cells = [[(name, {"color": CREAM, "bold": True}), setting] for name, setting in rows]
    bottom = table(s, 64, 132, 1152, columns, cells, row_h=78, size=20)
    takeaway(s, bottom + 14, "Time and task are matched across the monitors. Total apparatus is not.", color=AMBER, size=24)
    text(s, 64, bottom + 62, 1152, 30, "So this is a test of added information, not a resource-matched advantage claim.", size=18, color=SOFT)
    return s


def backup_atomic(prs, e, b, n, index):
    r = b["research"]["atomic"]
    s = backup(prs, n, "lasers", "The atomic channel, ", "run as a circuit on IBM.",
               f"How the model atoms respond when the laser is a few hertz off, compiled to {r['qubits']} qubits and {r['gates']} two-qubit gates. "
               f"{r['shots']:,} shots per setting.",
               "Superconducting qubits emulated the model: no atoms, no optical coupling and no 128-second monitor were measured. Raw counts. "
               "hardware_campaign/runs/optical_controls_plain_v1/", IBM)
    text(s, 64, 196, 220, 22, "LASER OFFSET", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 300, 196, 600, 22, "ATOMS LEFT EXCITED · MODEL (OUTLINE) AND IBM MARRAKESH (FILLED)", size=13, bold=True, color=MUTED, tracking=1.2)
    for i, (hz, model, measured, interval) in enumerate(r["rows"]):
        y = 230 + i * 92
        rule(s, 64, y, 1216, y)
        sign = "+" if hz > 0 else "−" if hz < 0 else ""
        text(s, 64, y + 10, 220, 72, f"{sign}{abs(hz)} Hz", size=34, bold=True, color=CREAM, anchor=MIDDLE)
        panel(s, 300, y + 18, 520 * model, 24, fill=None, outline=CREAM, radius=0.3, width=1.5)
        bar(s, 300, y + 50, 520, 24, measured, GREEN)
        text(s, 840, y + 10, 130, 36, pct(model, 1), size=22, color=CREAM, anchor=MIDDLE)
        text(s, 840, y + 46, 130, 36, pct(measured, 1), size=22, bold=True, color=GREEN, anchor=MIDDLE)
        text(s, 980, y + 46, 236, 36, f"interval {pct(interval[0], 1)} to {pct(interval[1], 1)}", size=14.5, color=MUTED, anchor=MIDDLE)
    rule(s, 64, 506, 1216, 506)
    takeaway(s, 520, "The response goes the right way, and is biased at the edges.", size=24)
    text(s, 64, 568, 1152, 70, f"Separately, a two-photon state at phase 0.35 ran as a circuit with an occupation error of {r['noon_tv']:.3f}. "
         "These are implementation tests of bounded models. Acquisition, calibration and apparatus cost remain optical questions.", size=17, color=SOFT, line=1.2)
    return s


def backup_drive(prs, e, b, n, index):
    r = b["research"]["drive"]
    s = backup(prs, n, "lasers", "Drive amplitude: ", "a negative result we keep.",
               "Can a click record reveal a 20% jump in drive strength at an unknown time? Three detectors read the same bits.",
               f"Field-amplitude proxy on 96-bin records, {r['records']} records per case, one operating point, increases only. The prior-only control "
               "was added after the holdout, so it is descriptive. qrsm_photon_poc/drive_diagnostics_followup/", NEG)
    text(s, 64, 196, 340, 22, "DETECTOR", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 420, 196, 796, 22, [[("■ ", {"color": CYAN}), ("JUMP CAUGHT IN TIME     ", {"color": MUTED}), ("■ ", {"color": AMBER}), ("FALSE ALARMS ON STEADY RECORDS", {"color": MUTED})]],
         size=13, bold=True, tracking=1.0)
    for i, (name, caught, false) in enumerate(r["rows"]):
        y = 230 + i * 88
        rule(s, 64, y, 1216, y)
        text(s, 64, y + 10, 340, 68, name, size=21, bold=i == 0, color=CREAM, anchor=MIDDLE, line=1.1)
        for j, (value, color) in enumerate(((caught, CYAN), (false, AMBER))):
            yy = y + 16 + j * 32
            bar(s, 420, yy, 520, 22, value / 0.10, color)
            text(s, 956, yy - 8, 120, 38, pct(value), size=21, bold=True, color=color, anchor=MIDDLE)
    text(s, 420, 496, 520, 20, "scale: 0% to 10%", size=13, color=MUTED)
    rule(s, 64, 494, 1216, 494)
    panel(s, 64, 522, 520, 120)
    text(s, 84, 530, 480, 22, "ERROR OF THE AMPLITUDE ESTIMATE", size=12.5, bold=True, color=MUTED, tracking=1.2)
    text(s, 84, 554, 480, 50, [[(f"{r['rmse'][0]:.4f}", {"color": MUTED}), ("  →  ", {"color": MUTED}), (f"{r['rmse'][1]:.4f}", {"color": CREAM})]], size=36, bold=True, anchor=MIDDLE)
    text(s, 84, 606, 480, 28, "ignoring the data, then using it", size=15.5, color=SOFT)
    text(s, 616, 522, 600, 120, [["Every detector raised more false alarms than detections."],
                                 [("Most of the apparent gain came from the prior, not from the clicks.", {"color": SOFT, "bold": False, "size": 18})]],
         size=23, bold=True, color=CYAN, line=1.15, after=6, anchor=MIDDLE)
    return s


def backup_layers(prs, e, b, n, index):
    s = backup(prs, n, "lasers", "Where the quantum part ", "actually enters.",
               footer="Individual channels ran as digital circuits. The full acquisition-and-diagnosis benchmark is a separate classical simulation. "
                      "hardware_campaign/optical_controls/README.md; LASER_DIAGNOSTICS_ROADMAP.md")
    layers = [("Sensor dynamics", "How the atoms respond to the laser.", "A Bloch model, and that channel as a circuit on IBM", GREEN, "RAN ON IBM AS A CIRCUIT"),
              ("Diagnostic inference", "Combining the readings into an alarm.", "Classical, on synthetic records", MUTED, "CLASSICAL"),
              ("Rare-history query", "Amplifying a rare condition in a coherent model.", "Qiskit circuits, on IBM hardware", GREEN, "RAN ON IBM")]
    for i, (name, what, evidence, color, tag) in enumerate(layers):
        x = 64 + i * 392
        panel(s, x, 136, 368, 372, outline=color)
        text(s, x + 20, 150, 328, 22, f"LAYER {i + 1}", size=13, bold=True, color=MUTED, tracking=1.4)
        text(s, x + 20, 178, 328, 66, name, size=27, bold=True, color=CREAM, line=1.08)
        text(s, x + 20, 252, 328, 80, what, size=18.5, color=SOFT, line=1.2)
        rule(s, x + 20, 352, x + 348, 352)
        text(s, x + 20, 364, 328, 22, tag, size=12.5, bold=True, color=color, tracking=1.3)
        text(s, x + 20, 392, 328, 100, evidence, size=18.5, color=CREAM, line=1.2)
    takeaway(s, 532, "Running one component on a quantum computer is not an end-to-end advantage.", size=24)
    text(s, 64, 580, 1152, 60, "A sensor can use quantum dynamics while a classical computer reads its output. "
         "A sensing benefit would not be a computing speedup, and we claim neither.", size=18, color=SOFT, line=1.2)
    return s


# ---------------------------------------------------------------------------- chipmaking


def backup_exposure(prs, e, b, n, index):
    rows = b["research"]["exposure"]
    s = backup(prs, n, "chipmaking", "Sharper lines, ", "paid for in photons.",
               "A strip of resist that needs two photons at once, under three kinds of light, each at its own best dose. 20 scored cells.",
               "An assumed resist, not a material on the shelf. With 20% transmission, a leakier resist or a 1% pair source, laser light wins. "
               "quantum_lithography_poc/exposure_followup/results.json; picture captured from the Lab.", SIM)
    shot = picture(s, "chips.png", 64, 196, w=640, h=392)
    x = min(64 + shot.width / 9525 + 32, 728)
    for name, xx, w, align in (("Light", x, 190, LEFT), ("Cells right", x + 180, 110, RIGHT), ("All 20", x + 290, 96, RIGHT), ("Photons", x + 386, 102, RIGHT)):
        text(s, xx, 196, w, 22, name.upper(), size=12.5, bold=True, color=MUTED, tracking=1.1, align=align)
    for i, (name, accuracy, perfect, photons) in enumerate(rows):
        y = 226 + i * 96
        rule(s, x, y, x + 488, y)
        color = CYAN if i == 0 else SOFT
        text(s, x, y + 10, 186, 76, name, size=18.5, bold=i == 0, color=CREAM if i == 0 else SOFT, anchor=MIDDLE, line=1.1)
        text(s, x + 190, y + 10, 100, 76, pct(accuracy, 1), size=25, bold=True, color=color, anchor=MIDDLE, align=RIGHT)
        text(s, x + 290, y + 10, 96, 76, pct(perfect, 1), size=20, color=SOFT, anchor=MIDDLE, align=RIGHT)
        text(s, x + 386, y + 10, 102, 76, f"{photons / 1e6:.1f} M" if photons >= 9.95e6 else f"{photons / 1e6:.2f} M", size=20, color=AMBER if i == 0 else SOFT,
             anchor=MIDDLE, align=RIGHT)
    rule(s, x, 514, x + 488, 514)
    text(s, x, 524, 488, 64, "The fine stripes appear for laser light too. Pairs give them about twice the contrast.", size=16.5, color=SOFT, line=1.18)
    ratio = rows[0][3] / rows[2][3]
    takeaway(s, 604, f"Pairs print the cleanest stripes, for {ratio:.0f} times the photons of the pulsed laser.", size=23)
    return s


def backup_spatial(prs, e, b, n, index):
    r = b["research"]["spatial"]
    s = backup(prs, n, "chipmaking", "The full question needs ", f"{r['qubits']} qubits. We have {r['device']}.",
               f"Our rare-event question, asked of a {r['cells']}-cell exposure: how often does a contact fail to print? Built as a reversible circuit, and checked.",
               "Gate counts are constructive upper bounds for one amplification round, not a routed compilation. Never simulated in full or run. "
               "finals-lithography/full_spatial_circuit/results.json", ("Built and checked · not run", AMBER))
    text(s, 64, 196, 600, 22, "QUBITS", size=13, bold=True, color=MUTED, tracking=1.2)
    scale = 1080 / r["qubits"]
    x = 64
    for i, (count, color, label) in enumerate(zip(r["parts"], (CYAN, VIOLET, MUTED), ("counting photons in each cell", "adding up the score",
                                                                                           "spare, for reversible arithmetic"))):
        panel(s, x, 226, count * scale - 4, 46, fill=color, outline=None, radius=0.12)
        text(s, 64 + i * 370, 278, 360, 24, [[("■  ", {"color": color}), (f"{count}", {"bold": True, "color": CREAM}), f"  {label}"]], size=15.5, color=SOFT)
        x += count * scale
    panel(s, 64, 316, r["device"] * scale, 30, fill=None, outline=GREEN, radius=0.16, width=2)
    text(s, 64 + r["device"] * scale + 16, 314, 500, 34, f"the chip we used: {r['device']} qubits", size=17, bold=True, color=GREEN, anchor=MIDDLE)
    cards = [(f"{max(r['cx']) / 1e6:.1f} million", f"two-qubit gates, as an upper bound. Our best run on the chip used {e['local_gates']}.", AMBER),
             (pct(r["event"], 2), "of exposures: the rare event the circuit would amplify. One ideal round would raise it to about "
              f"{pct(math.sin(3 * math.asin(math.sqrt(r['event']))) ** 2, 1)}.", CYAN),
             ("Solved classically", "Dynamic programming already answers this independent-cell model, quickly.", CREAM)]
    for i, (big, small, color) in enumerate(cards):
        xx = 64 + i * 392
        panel(s, xx, 372, 368, 176)
        text(s, xx + 20, 384, 328, 56, big, size=36, bold=True, color=color, anchor=MIDDLE)
        text(s, xx + 20, 446, 328, 96, small, size=16.5, color=SOFT, line=1.18)
    takeaway(s, 572, "A map of the cost, not a result: building the circuit shows neither an advantage nor that the process works.", size=21)
    return s


def backup_phase(prs, e, b, n, index):
    r = b["research"]["phase"]
    s = backup(prs, n, "chipmaking", "Reading a phase: ", "the benefit depends on the budget.",
               f"Measuring one optical phase with {r['photons']:,.0f} photons at {pct(r['efficiency'], 0)} efficiency. Every photon sent is charged.",
               "Synthetic task with a known reference, ideal photon counting and declared losses. Zero observed errors is not a guarantee. "
               "quantum_lithography_poc/phase_inspection_followup/results.json", SIM, title_size=40)
    text(s, 64, 196, 320, 22, "LIGHT", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 400, 196, 420, 22, "ERROR IN THE PHASE, RADIANS · LOG SCALE", size=13, bold=True, color=MUTED, tracking=1.2)
    text(s, 960, 196, 256, 22, "WRONG HALF-TURN", size=13, bold=True, color=MUTED, tracking=1.2, align=RIGHT)
    low, high = math.log10(0.001), math.log10(10)
    for i, (name, rmse, wrong, trials) in enumerate(r["rows"]):
        y = 230 + i * 84
        rule(s, 64, y, 1216, y)
        bad = wrong > 0.1
        color = RED if bad else CYAN if i == 2 else SOFT
        text(s, 64, y + 8, 330, 68, name, size=21, bold=i == 2, color=CREAM, anchor=MIDDLE)
        bar(s, 400, y + 28, 380, 26, (math.log10(rmse) - low) / (high - low), color if color != SOFT else MUTED)
        text(s, 796, y + 8, 150, 68, f"{rmse:.4f}" if rmse < 1 else f"{rmse:.2f}", size=24, bold=True, color=color if color != SOFT else CREAM, anchor=MIDDLE, font="Consolas")
        text(s, 960, y + 8, 256, 68, pct(wrong, 1) if bad else f"0 of {trials:,}", size=24, bold=bad, color=RED if bad else SOFT, anchor=MIDDLE, align=RIGHT)
    rule(s, 64, 482, 1216, 482)
    takeaway(s, 496, "Pairs alone cannot tell a phase from that phase plus half a turn. A small laser pilot fixes it.", size=22)
    text(s, 64, 544, 1152, 96, [["The hybrid is slightly more precise than laser light, and only at high efficiency."],
                                [(f"If the pair source succeeds 1% of the time, the same dose takes {r['slowdown']:.0f} times longer.", {"color": AMBER, "bold": True})]],
         size=18.5, color=SOFT, line=1.2, after=6)
    return s


def backup_transfer(prs, e, b, n, index):
    s = backup(prs, n, "chipmaking", "Lithography light ", "is not our laboratory laser.",
               footer="Roles of the sources: ASML (light and lasers; EUV systems). Source monitoring and wafer effects: Cymer and imec, SPIE Advanced "
                      "Lithography 2014. LASER_DIAGNOSTICS_ROADMAP.md")
    columns = [("Light", 0.26, LEFT), ("Its role in making chips", 0.44, LEFT), ("In our model", 0.30, LEFT)]
    absent, stand_in = ("Not represented", {"color": AMBER, "bold": True}), ("A synthetic stand-in", {"color": CYAN, "bold": True})
    rows = [[("193 nm excimer laser", {"color": CREAM, "bold": True}), "The deep-ultraviolet exposure source", absent],
            [("CO₂ drive laser", {"color": CREAM, "bold": True}), "Heats tin droplets into a plasma", absent],
            [("13.5 nm extreme ultraviolet", {"color": CREAM, "bold": True}), "The plasma’s light, which exposes the wafer", absent],
            [("698 nm laboratory laser", {"color": CREAM, "bold": True}), "A narrow line that atoms can read", stand_in]]
    bottom = table(s, 64, 132, 1152, columns, rows, row_h=84, size=20)
    takeaway(s, bottom + 16, "Conventional source monitors already exist, and already work.", size=24)
    text(s, 64, bottom + 62, 1152, 60, "What we tested is whether an atomic sensor adds information, on a stand-in wavelength. "
         "Transfer to a real lithography source would need its own experiment.", size=18, color=SOFT, line=1.2)
    return s


# ---------------------------------------------------------------------------- the order, and the build

# key, heading on the map, short title on the map, builder
BACKUPS = [
    ("map", None, None, backup_map),
    ("ladder", "On IBM hardware", "What each move bought", backup_ladder),
    ("repeats", "On IBM hardware", "Three runs, one leader", backup_repeats),
    ("noise", "On IBM hardware", "Noise model, circuit by circuit", backup_noise),
    ("deep", "On IBM hardware", "Deeper circuits that failed", backup_deep),
    ("coverage", "On IBM hardware", "What ran, and where it stops", backup_coverage),
    ("step", "Method and credit", "One step, in maths", backup_step),
    ("reproduce", "Method and credit", "Rerun it: one command", backup_reproduce),
    ("rubric", "Method and credit", "Rubric map", backup_rubric),
    ("credit", "Method and credit", "Ours, prior work, AI", backup_credit),
    ("pairs", "Light: photons and detectors", "Equally bright, not equally good", backup_pairs),
    ("gaas", "Light: photons and detectors", "A real quantum dot, reanalysed", backup_gaas),
    ("deadtime", "Light: photons and detectors", "The detector's blind time", backup_deadtime),
    ("joint", "Light: photons and detectors", "A QRSM for photon pairs", backup_joint),
    ("calibration", "Light: photons and detectors", "More data against calibration", backup_calibration),
    ("truncation", "Light: photons and detectors", "Better model, more qubits", backup_truncation),
    ("stress", "Lasers", "Monitors under stress", backup_stress),
    ("monitor", "Lasers", "What the monitor assumes", backup_monitor),
    ("atomic", "Lasers", "Atomic channel on IBM", backup_atomic),
    ("drive", "Lasers", "Drive amplitude: negative", backup_drive),
    ("layers", "Lasers", "Where quantum enters", backup_layers),
    ("exposure", "Chipmaking", "Sharper lines, more photons", backup_exposure),
    ("spatial", "Chipmaking", "The 389-qubit question", backup_spatial),
    ("phase", "Chipmaking", "Reading a phase", backup_phase),
    ("transfer", "Chipmaking", "Real lithography light", backup_transfer),
    ("cinematic", "Video", "The cinematic cut", backup_cinematic),
]
MAP_ORDER = ["On IBM hardware", "Method and credit", "Light: photons and detectors", "Lasers", "Chipmaking", "Video"]


def backup_index(first: int) -> dict:
    """Slide number of each backup, by key."""
    return {key: first + i for i, (key, *_rest) in enumerate(BACKUPS)}


def build_backups(prs, e: dict, script: dict, first: int, cinematic: Path, cinematic_poster: Path) -> dict:
    """Append every backup after the main talk. Returns {key: slide number}."""
    b = backup_evidence(e)
    index = backup_index(first)
    notes = {entry["key"]: entry for entry in script["backups"]}
    missing = [key for key, *_rest in BACKUPS if key not in notes]
    assert not missing, f"v3_notes.json has no backup note for: {missing}"
    groups = [(group, [(index[key], short) for key, g, short, _ in BACKUPS if g == group]) for group in MAP_ORDER]
    for key, _group, _short, builder in BACKUPS:
        if key == "map":
            slide = builder(prs, e, b, index[key], index, groups)
        elif key == "cinematic":
            slide = builder(prs, e, b, index[key], index, cinematic, cinematic_poster)
        else:
            slide = builder(prs, e, b, index[key], index)
        backup_notes(slide, notes[key])
    return index
