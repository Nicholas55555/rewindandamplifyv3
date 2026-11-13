"""Build the V3 finals deck: finals-deck/Rewind_Amplify_Finals_V3.pptx.

The V2 deck (finals-deck/v2/) supplies only the cover. The 12 main-talk slides after it are built here, problem
first and one picture per slide, in the same dark style as the Lab; v3_backups.py builds the backups to match.
Pictures of the Lab are real captures of the running page (python lab/capture.py deck). Every number on a slide
is read from the saved results at build time, so a slide cannot drift from the evidence.

The two videos are embedded as real, playable media (not pictures of videos).

    python finals-deck/build_v3_deck.py
    python finals-deck/build_v3_deck.py --cinematic path/to/final_cut.mp4      # swap in a newer cinematic cut
    python finals-deck/build_v3_deck.py --lab-video media/lab-tour-45s.mp4     # the 45-second Lab recording on slide 10

Then, on a machine with PowerPoint, finish_v3_deck.ps1 exports the PDF and slide previews, and
finish_v3_deck.py writes the presenter guide and the manifest.

Needs python-pptx, pillow and segno (for the QR code):  pip install python-pptx pillow segno
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.packuri import PackURI

from deck_kit import (AMBER, ASSETS, CREAM, CYAN, GREEN, HERE, MEDIA, MUTED, PANEL_2, ROOT, SLATE, SOFT, TRACK, VIOLET,
                      base, chip, load, notes, panel, pct, picture, px, qr_png, rule, text, two_tone)
from v3_backups import backup_index, build_backups

V2 = HERE / "v2" / "Rewind_Amplify_Finals_Visual.pptx"
OUTPUT = HERE / "Rewind_Amplify_Finals_V3.pptx"
REPO_URL = "https://github.com/Nicholas55555/rewindandamplifyv3"
MAIN_SLIDES = 13

# ---------------------------------------------------------------------------- numbers, read from the evidence


def evidence() -> dict:
    """Every figure the slides quote, with where it comes from. Nothing is typed in by hand below this point."""
    verification = load("research-validation/original_after_click_verification.json")["models"]
    defect, none = verification["with_hidden_defect"], verification["no_hidden_defect"]
    hero = load("hardware_campaign/runs/original_precision_v1/hero_acceptance_contrast.json")
    first = {row["name"]: row for row in load("hardware_campaign/runs/original_plain_v2/analysis.json")["rows"]}
    suppressed = {row["name"]: row for row in load("hardware_campaign/runs/original_suppressed_v1/analysis.json")["rows"]}
    job = load("hardware_campaign/runs/original_precision_v1/job.json")
    campaign = load("hardware_campaign/results.json")
    noise = load("hardware_campaign/noise_model/results.json")
    wall = load("rewindandamplify-main/results/numbers.json")
    sensor = load("laser_sensor_viability/followup/main/results.json")
    plain = first["click3-full-r0"]["observables"]["selected"]
    local, full = "click3-steered-memory+last-1-r1", "click3-steered-full-r1"
    loops = {row["circuit"]: row for row in noise["after_click"]}
    e = {
        "p_click": defect["original_event_probability"],
        "answer_defect": defect["exact_conditional_probabilities"][2],
        "answer_none": none["exact_conditional_probabilities"][2],
        "ideal_full": defect["ideal_circuits"]["full_steered"]["event_probability"],
        "ideal_local": defect["ideal_circuits"]["local_steered"]["event_probability"],
        "ideal_local_tv": noise["featured_pair"]["local"]["ideal"]["answer_error_tv"],
        "wall_runs": wall["wall"]["rejection_runs"], "wall_steered": wall["wall"]["steered_runs"],
        "wall_calls": wall["wall"]["steered_calls"], "classical_growth": wall["e3"]["classical_growth_per_qubit"],
        "local_hits": hero["first"]["successes"], "full_hits": hero["second"]["successes"], "shots": hero["first"]["shots"],
        "local_rate": hero["first"]["probability"], "full_rate": hero["second"]["probability"],
        "local_gates": hero["native_two_qubit_gate_counts"][0], "full_gates": hero["native_two_qubit_gate_counts"][1],
        "local_tv": hero["selected_history_tv_vs_unsteered"][0], "full_tv": hero["selected_history_tv_vs_unsteered"][1],
        "gap": hero["probability_difference"], "gap_ci": hero["independent_shot_wilson_based_interval95"],
        "plain_rate": plain["probability"], "plain_hits": plain["successes"], "plain_shots": plain["shots"],
        "job_id": job["job_id"], "jobs": campaign["jobs"], "total_shots": campaign["total_shots"],
        "noise_scale": noise["echo_fit"]["scale"],
        "nm": {key: {label: noise["featured_pair"][key][label]["hit_rate"] for label in ("ideal", "calibration", "echo_scaled", "measured")}
               for key in ("local", "full")},
        "supp_tv": [suppressed[n]["observables"]["selected_history_tv_to_unsteered_target"] for n in (local, full)],
        "first_tv": [first[n]["observables"]["selected_history_tv_to_unsteered_target"] for n in (local, full)],
        "loops": loops,
    }
    # the three follow-up studies quoted on the impact slide
    ignored = load("qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit0.json")
    aware = load("qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit1.json")
    e["dead_time"] = {"ignored": ignored["joint_parameters"]["g_defect"], "modelled": aware["joint_parameters"]["g_defect"],
                      "truth": aware["generator_parameters"]["g_defect"]}
    e["overlaps"] = [case["conditional_overlap"] for case in load("quantum_dot_bridge/results.json")["benchmark_cases"]]
    methods = sensor["scenarios"][0]["methods"]     # unknown-onset monitor, nominal scenario
    e["monitor"] = {key: methods[key]["detection_within_32s"] for key in ("classical", "classical_quantum", "two_classical")}
    assert e["local_hits"] == 6300 and e["full_hits"] == 5674 and e["shots"] == 8192
    assert (e["local_gates"], e["full_gates"]) == (58, 125)
    assert f"{100 * e['answer_defect']:.2f}" == "4.67" and f"{100 * e['answer_none']:.2f}" == "10.10"
    return e


# ---------------------------------------------------------------------------- the twelve rebuilt main slides


def slide_problem(prs, e):
    s = base(prs, 2, "The problem", two_tone("Something is hidden ", "inside the signal."),
             "A detector records one bit per time step: click, or no click. Out of sight, a defect can trade energy "
             "with the source and quietly change the pattern.",
             "Picture of our model, captured from the live Lab. On IBM hardware, superconducting qubits play these roles; "
             "no optical photons were detected.")
    picture(s, "bench-hidden.png", 64, 196, w=1152, h=276)
    cards = [("Quantum-chip teams", "Unseen defects drain their qubits between calibrations."),
             ("Photon-source engineers", "Two sources can look equally bright and behave differently."),
             ("Anyone reading a detector", "A detector fault can look exactly like a defect.")]
    for i, (who, why) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 484, 368, 104)
        text(s, x + 18, 496, 332, 28, who, size=20, bold=True, color=AMBER)
        text(s, x + 18, 528, 332, 54, why, size=17, color=SOFT, line=1.15)
    text(s, 64, 604, 1152, 40, "Guess the cause wrong, and you fix the wrong thing.", size=26, bold=True, color=CYAN,
         anchor=MSO_ANCHOR.MIDDLE)
    return s


def slide_model(prs, e):
    s = base(prs, 3, "Our model", two_tone("A recurrent machine whose ", "memory is quantum."),
             "We call it a QRSM: a quantum recurrent state machine. Every time step repeats the same four gates.",
             "Same gates as qrsm_grover/model.py. The picture is a live simulation of that circuit, tested against Qiskit to 10⁻¹².")
    picture(s, "bench-revealed.png", 64, 178, w=800, h=200)
    picture(s, "circuit.png", 64, 390, w=640, h=258)
    facts = [("2 qubits", "of memory: the emitter and a hidden defect. Never measured.", CYAN),
             ("1 bit", "comes out per step: click, or no click.", AMBER),
             ("Each bit", "updates the hidden state, so the model predicts what comes next.", VIOLET)]
    for i, (big, small, color) in enumerate(facts):
        y = 186 + i * 152
        panel(s, 892, y, 324, 136)
        text(s, 912, y + 14, 290, 44, big, size=36, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 912, y + 62, 290, 66, small, size=17, color=SOFT, line=1.15)
    return s


def slide_question(prs, e):
    s = base(prs, 4, "The question", two_tone("One click. ", "Two futures."),
             "Given a click at step 3, what happens next? With no defect, a click empties the source and the machine "
             "starts over. A hidden defect remembers.",
             "Exact predictions of two models we programmed, recomputed live by the Lab and by reproduce.py. "
             "Not a diagnosis of a real defect.")
    picture(s, "answer.png", 64, 198, w=660, h=446)
    x = 740
    panel(s, x, 198, 476, 150, outline=AMBER)
    text(s, x + 24, 210, 430, 22, "EMITTER ONLY", size=13, bold=True, color=MUTED, tracking=1.4)
    text(s, x + 24, 234, 430, 76, pct(e["answer_none"]), size=68, bold=True, color=AMBER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 24, 314, 430, 24, "chance of a click at step 6", size=16, color=SOFT)
    panel(s, x, 364, 476, 150, outline=CYAN)
    text(s, x + 24, 376, 430, 22, "WITH THE HIDDEN DEFECT", size=13, bold=True, color=MUTED, tracking=1.4)
    text(s, x + 24, 400, 430, 76, pct(e["answer_defect"]), size=68, bold=True, color=CYAN, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 24, 480, 430, 24, "chance of a click at step 6", size=16, color=SOFT)
    text(s, x, 536, 476, 100, "The pattern after a rare click is a fingerprint of hidden memory.", size=24, bold=True,
         color=CREAM, line=1.15)
    return s


def slide_cost(prs, e):
    s = base(prs, 5, "The cost", two_tone("The useful runs ", "are the rare ones."),
             "To study what follows a rare click the ordinary way, you run the machine again and again and throw away "
             "every run that missed.",
             "Rejection sampling costs 1/p runs per kept sample. The 64-step figure is an exact calculation for a real "
             "record from our first project.")
    picture(s, "raster.png", 64, 198, w=636, h=446)
    x = 716
    rows = [(pct(e["p_click"]), "of runs contain the click we asked about", AMBER),
            (f"{1 / e['p_click']:.0f} runs", "per useful sample. The other 24 are thrown away.", CREAM),
            (f"{e['wall_runs']:,.0f} runs", "to match one real 64-step record this way", CYAN)]
    for i, (big, small, color) in enumerate(rows):
        y = 198 + i * 150
        panel(s, x, y, 500, 134)
        text(s, x + 22, y + 12, 460, 64, big, size=50 if i < 2 else 44, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 22, y + 82, 460, 44, small, size=18, color=SOFT)
    return s


def slide_why_quantum(prs, e):
    s = base(prs, 6, "Why quantum might help", two_tone("Grover makes rare answers common. ", "Two catches."),
             footer="Amplitude amplification is prior work (Brassard et al. 2002; Low, Yoder and Chuang 2014). "
                    "Bars are exact calculations for one 64-step record, not hardware runs.")
    # left: the cost of one matching sample, on a log scale
    text(s, 64, 132, 560, 26, "COST OF ONE MATCHING SAMPLE · 64-STEP RECORD · LOG SCALE", size=13, bold=True, color=MUTED, tracking=1.2)
    import math
    bars = [("Throw runs away", e["wall_runs"], "runs", MUTED), ("Steer one gate (classical)", e["wall_steered"], "runs", AMBER),
            ("Steer, then amplify", e["wall_calls"], "calls of the machine", CYAN)]
    top = math.log10(e["wall_runs"])
    for i, (label, value, unit, color) in enumerate(bars):
        y = 172 + i * 104
        text(s, 64, y, 560, 26, label, size=19, color=CREAM, bold=True)
        panel(s, 64, y + 32, 560, 34, fill=TRACK, outline=None, radius=0.2)
        panel(s, 64, y + 32, max(560 * math.log10(value) / top, 14), 34, fill=color, outline=None, radius=0.2)
        text(s, 64, y + 68, 560, 26, f"{value:,.0f} {unit}", size=18, color=color, bold=True)
    text(s, 64, 488, 560, 54, "Rarity costs 1/p the ordinary way, and about 1/√p with amplification.", size=18, color=SOFT, line=1.15)
    # right: the two catches
    catches = [("1", "It must run the machine backwards.", "Our model resets a qubit every step, and a reset cannot be undone."),
               ("2", "It is deep.", "On today's hardware every extra gate is a chance for noise.")]
    for i, (n, head, body) in enumerate(catches):
        y = 132 + i * 178
        panel(s, 668, y, 548, 160)
        text(s, 690, y + 16, 60, 70, n, size=58, bold=True, color=AMBER, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 754, y + 20, 440, 34, head, size=24, bold=True, color=CREAM)
        text(s, 754, y + 62, 440, 84, body, size=18, color=SOFT, line=1.18)
    panel(s, 64, 556, 1152, 92, fill=PANEL_2, outline=AMBER, width=1.5)
    text(s, 86, 564, 1108, 76,
         [[("No speedup today. ", {"color": AMBER, "bold": True}),
           f"At this size an exact classical sampler answers in a fraction of a millisecond. Its cost grew about "
           f"{e['classical_growth']:.0f}× per added hidden qubit in our tests: that is where a quantum method could matter."]],
         size=19, color=CREAM, line=1.2, anchor=MSO_ANCHOR.MIDDLE)
    return s


def slide_method(prs, e):
    s = base(prs, 7, "Our method", two_tone("You can’t amplify ", "what you can’t rewind."),
             footer="What is ours: the mapping onto a hidden-memory model, and the noise-aware build. "
                    "Qiskit circuits, Aer verification, transpiled to IBM’s CZ basis. 114 tests on the core package.")
    moves = [("1", "Purify", "A fresh qubit replaces every reset. The whole run becomes one reversible circuit."),
             ("2", "Steer", "Tune one gate so the rare click is less rare. The answer is unchanged."),
             ("3", "Amplify locally", "One round. The reflection checks 3 qubits, not all 5: about half the gates."),
             ("4", "Verify", "The click is measured directly, so a failed shot shows itself and is dropped.")]
    for i, (n, head, body) in enumerate(moves):
        x = 64 + i * 292
        panel(s, x, 132, 276, 168)
        text(s, x + 16, 142, 40, 36, n, size=26, bold=True, color=CYAN, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 50, 142, 216, 36, head, size=23, bold=True, color=CREAM, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 16, 186, 246, 108, body, size=16.5, color=SOFT, line=1.18)
    picture(s, "amplify-replay.png", 64, 318, w=596, h=330)
    x = 676
    panel(s, x, 318, 540, 330)
    text(s, x + 24, 330, 490, 22, "IDEAL SIMULATOR · ONE ROUND", size=13, bold=True, color=MUTED, tracking=1.4)
    text(s, x + 24, 356, 490, 70, [[(pct(e["p_click"]), {"color": MUTED}), ("  →  ", {"color": MUTED}), (pct(e["ideal_local"], 1), {"color": CYAN})]],
         size=54, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 24, 430, 490, 26, "chance of the click we asked about", size=18, color=SOFT)
    rule(s, x + 24, 472, x + 516, 472)
    text(s, x + 24, 486, 230, 50, "0.000", size=40, bold=True, color=CYAN, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 24, 540, 230, 90, "error in the answer with the full reflection", size=16.5, color=SOFT, line=1.15)
    text(s, x + 280, 486, 230, 50, f"{e['ideal_local_tv']:.3f}", size=40, bold=True, color=AMBER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 280, 540, 236, 90, "with the lighter local reflection: a small, known bias", size=16.5, color=SOFT, line=1.15)
    return s


def slide_hardware(prs, e):
    s = base(prs, 8, "Real quantum hardware · IBM Marrakesh · 11 November 2026", two_tone("On IBM hardware, ", "fewer gates won."),
             footer=f"{e['shots']:,} shots per circuit, raw counts, no error mitigation. Job {e['job_id']}. "
                    "Width and routing also differ, so gate count is not proven to be the only cause.")
    x0, width = 64, 700

    def lane(y, name, gates, rate, color, ideal, model, hits):
        text(s, x0, y, 420, 28, name, size=22, bold=True, color=color)
        text(s, x0 + 420, y + 2, 280, 26, f"{gates} two-qubit gates", size=17, color=SOFT, align=PP_ALIGN.RIGHT)
        panel(s, x0, y + 36, width, 56, fill=TRACK, outline=SLATE, radius=0.12)
        panel(s, x0, y + 36, width * rate, 56, fill=color, outline=None, radius=0.12)
        rule(s, x0 + width * ideal, y + 30, x0 + width * ideal, y + 98, color=CREAM, width=1.5)
        rule(s, x0 + width * model, y + 30, x0 + width * model, y + 98, color=CREAM, width=1.5, dashed=True)
        text(s, x0 + width + 26, y + 26, 250, 70, pct(rate), size=54, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x0 + width + 28, y + 96, 420, 24, f"{hits:,} of {e['shots']:,} shots hit the click", size=15.5, color=SOFT)

    lane(140, "Our lighter build: local reflection", e["local_gates"], e["local_rate"], CYAN, e["nm"]["local"]["ideal"],
         e["nm"]["local"]["echo_scaled"], e["local_hits"])
    lane(282, "Textbook build: full reflection", e["full_gates"], e["full_rate"], AMBER, e["nm"]["full"]["ideal"],
         e["nm"]["full"]["echo_scaled"], e["full_hits"])
    y = 424
    text(s, x0, y, 420, 28, "No amplification: plain sampling", size=22, bold=True, color=MUTED)
    panel(s, x0, y + 36, width, 30, fill=TRACK, outline=SLATE, radius=0.2)
    panel(s, x0, y + 36, width * e["plain_rate"], 30, fill=MUTED, outline=None, radius=0.2)
    text(s, x0 + width + 26, y + 26, 250, 50, pct(e["plain_rate"]), size=36, bold=True, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x0, y + 72, width, 22, "solid tick: ideal simulator      dashed tick: our noise model (next slide)", size=14.5, color=MUTED)
    # the three takeaways
    cards = [(f"+{100 * e['gap']:.1f} points", f"for the lighter build (95% interval {100 * e['gap_ci'][0]:.1f} to {100 * e['gap_ci'][1]:.1f})", CYAN),
             (f"{e['local_tv']:.2f} vs {e['full_tv']:.2f}", "error in the answer. Lower is better.", CREAM),
             (f"{pct(e['plain_rate'], 0)} → {pct(e['local_rate'], 0)}", "amplification at work on a real chip", AMBER)]
    for i, (big, small, color) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 536, 368, 112)
        text(s, x + 18, 544, 332, 48, big, size=32, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 18, 594, 332, 48, small, size=16, color=SOFT, line=1.12)
    return s


def slide_noise(prs, e):
    s = base(prs, 9, "Simulator against hardware", two_tone("A simple noise model ", "predicts the gap."),
             "The same compiled circuits that ran on the chip, simulated offline with the chip’s own error rates.",
             "Depolarizing gate errors from the saved calibration, readout errors measured in the same job. "
             "Not modelled: idle decoherence, crosstalk, drift. hardware_campaign/noise_model/")
    x, y, w = 64, 190, 660
    panel(s, x, y, w, 452)
    text(s, x + 24, y + 16, 300, 24, "CHANCE OF THE CLICK", size=13, bold=True, color=MUTED, tracking=1.4)
    text(s, x + 388, y + 14, 120, 26, f"Local · {e['local_gates']}", size=17, bold=True, color=CYAN, align=PP_ALIGN.RIGHT)
    text(s, x + 516, y + 14, 120, 26, f"Full · {e['full_gates']}", size=17, bold=True, color=AMBER, align=PP_ALIGN.RIGHT)
    rows = [("Ideal simulator", "no noise: the two builds tie", "ideal", SOFT, False),
            ("Noise model, calibration only", "the chip’s reported error rates", "calibration", SOFT, False),
            ("Noise model, echo-fitted", f"gate errors × {e['noise_scale']:.2f}, fitted on echo circuits only", "echo_scaled", CREAM, True),
            ("IBM Marrakesh, measured", f"{e['shots']:,} shots each", "measured", CREAM, True)]
    for i, (name, sub, key, color, strong) in enumerate(rows):
        yy = y + 56 + i * 98
        rule(s, x + 24, yy, x + w - 24, yy)
        text(s, x + 24, yy + 14, 360, 30, name, size=22 if strong else 20, bold=strong, color=color)
        text(s, x + 24, yy + 48, 370, 40, sub, size=15, color=MUTED, line=1.1)
        size = 34 if key == "measured" else 28
        text(s, x + 388, yy + 16, 120, 56, pct(e["nm"]["local"][key], 1), size=size, bold=True,
             color=CYAN if strong else SOFT, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 516, yy + 16, 120, 56, pct(e["nm"]["full"][key], 1), size=size, bold=True,
             color=AMBER if strong else SOFT, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    lx = 752
    local_d, local_n = e["loops"]["loop-defect-r1"], e["loops"]["loop-nodefect-r1"]
    findings = [(f"{e['noise_scale']:.1f}× noisier", "than its calibration said, measured by running the machine forwards and then backwards.", AMBER),
                ("Suppression did not help",
                 f"Dynamical decoupling and twirling moved the answer error from {e['first_tv'][0]:.2f} to {e['supp_tv'][0]:.2f} "
                 f"(local) and {e['first_tv'][1]:.2f} to {e['supp_tv'][1]:.2f} (full).", CREAM),
                ("The bias is predicted",
                 f"After-click answer, local build: {pct(local_d['measured']['later_click_rates'][2], 1)} and "
                 f"{pct(local_n['measured']['later_click_rates'][2], 1)} measured, "
                 f"{pct(local_d['echo_scaled']['later_click_rates'][2], 1)} and {pct(local_n['echo_scaled']['later_click_rates'][2], 1)} "
                 f"predicted. Exact: {pct(e['answer_defect'], 1)} and {pct(e['answer_none'], 1)}.", CYAN)]
    for i, (head, body, color) in enumerate(findings):
        yy = 190 + i * 154
        panel(s, lx, yy, 464, 144)
        text(s, lx + 20, yy + 10, 424, 36, head, size=24, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, lx + 20, yy + 50, 424, 90, body, size=15.5, color=SOFT, line=1.16)
    return s


def slide_demo(prs, e, video: Path, poster: Path, qr: Path):
    s = base(prs, 10, "See it run", two_tone("The Lab: ", "our model, live in a browser."),
             footer="A screen recording of lab/index.html: the model, the method, the IBM result, then three follow-up studies. "
                    "Open Rewind_Amplify_Lab.html to drive it yourself: one file, no install, works offline.")
    s.shapes.add_movie(str(video), px(64), px(128), px(928), px(522), poster_frame_image=str(poster), mime_type="video/mp4")
    text(s, 1016, 132, 200, 26, "TRY IT", size=13, bold=True, color=MUTED, tracking=1.4)
    picture(s, qr.name, 1016, 162, w=200, folder=qr.parent, outline=None)
    text(s, 1016, 372, 200, 60, "Scan for the code, the Lab and every result.", size=15.5, color=SOFT, line=1.15)
    for i, line in enumerate(["Live, exact simulation", "Real IBM counts", "33 tests hold it to Qiskit and to the saved data"]):
        text(s, 1016, 452 + i * 62, 200, 56, [[("•  ", {"color": CYAN}), line]], size=15.5, color=CREAM, line=1.15)
    return s


def slide_impact_sources() -> None:
    """The files slide 11 reads directly (for the manifest)."""
    load("quantum_lithography_poc/exposure_followup/results.json")
    load("quantum_dot_bridge/results.json")
    load("applied/results.json")


def slide_impact(prs, e):
    s = base(prs, 11, "The same question, asked of other light", two_tone("Beyond qubits: three tests. ", "Honestly scored."),
             footer="The three studies are our simulations, plus one reanalysis of published data: no photons, lasers or wafers were measured. "
                    "Green lines: our own machine asked each field’s question on IBM Marrakesh, 12 November (backups 40 and 41).")
    ours = load("applied/results.json")
    fresh, truth = ours["new_job"], {name: machine["truth"] for name, machine in ours["machines"].items()}
    second = lambda machine: fresh["rows"][f"window-{machine}-rewound"]["another"]["probability"]  # noqa: E731
    g2 = fresh["g2"]
    chips = load("quantum_lithography_poc/exposure_followup/results.json")["cases"][1]["methods"]
    best = lambda key: chips[key]["best_threshold_accuracy"]  # noqa: E731
    dot = load("quantum_dot_bridge/results.json")["classical_trap_pair_comparison"]
    cards = [("Simulated · published data reanalysed", CYAN, "photons.png", "Photon sources",
              "Two sources, equally bright. Only the pairs show which one has a hidden memory.",
              f"{pct(dot[0]['coincidence_probability_per_excitation_pair'], 1)} vs {pct(dot[-1]['coincidence_probability_per_excitation_pair'], 1)}",
              "of attempts split the pair, at identical brightness",
              f"Right after a photon, g2 is {g2['defect'][0]['ratio']:.2f} with a hidden defect and {g2['clean'][0]['ratio']:.2f} without "
              f"(exact {truth['defect']['g2'][0]:.2f}, {truth['clean']['g2'][0]:.2f})."),
             ("Simulated · negative result", AMBER, "lasers.png", "Laser monitoring",
              "Adding an atomic sensor helped a little. A second ordinary reference helped far more.",
              f"{pct(e['monitor']['classical_quantum'], 0)} vs {pct(e['monitor']['two_classical'], 0)}",
              "of frequency steps caught within 32 seconds",
              f"A frequency step inside it lifts the second click from {pct(second('defect'), 1)} to {pct(second('stepped'), 1)} "
              f"(exact {pct(truth['defect']['another'], 1)} to {pct(truth['stepped']['another'], 1)})."),
             ("Simulated · an assumed resist", CYAN, "chips.png", "Chipmaking",
              "Entangled pairs print cleaner stripes, and use more light to do it.",
              f"{pct(best('noon')['guard_cell_accuracy'], 0)} vs {pct(best('phase_cycled_burst')['guard_cell_accuracy'], 0)}",
              f"of cells right, for {best('noon')['sample_incident_photons'] / best('phase_cycled_burst')['sample_incident_photons']:.0f} times the photons",
              f"A second photon follows a rare first {pct(second('defect'), 1)} of the time with a hidden defect, {pct(second('clean'), 1)} without "
              f"(exact {pct(truth['defect']['another'], 1)}, {pct(truth['clean']['another'], 1)}).")]
    for i, (status, color, shot, who, body, big, small, machine) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 132, 368, 506)
        chip(s, x + 20, 146, status, color)
        picture(s, shot, x + 34, 180, w=300, h=150)                      # centred in the card
        text(s, x + 20, 336, 328, 32, who, size=23, bold=True, color=CREAM, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 20, 370, 328, 62, body, size=16, color=SOFT, line=1.16)
        rule(s, x + 20, 438, x + 348, 438)
        text(s, x + 20, 442, 328, 46, big, size=34, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 20, 488, 328, 40, small, size=15, color=SOFT, line=1.14)
        rule(s, x + 20, 534, x + 348, 534, color=GREEN)
        text(s, x + 20, 541, 328, 18, "OUR OWN MACHINE · RAN ON IBM", size=11.5, bold=True, color=GREEN, tracking=1.2)
        text(s, x + 20, 561, 328, 70, machine, size=15, color=CREAM, line=1.14)
    return s


def slide_claims(prs, e):
    s = base(prs, 12, "What we can defend", two_tone("What we claim, ", "and what we don’t."))
    columns = [("WE CLAIM", CYAN, 64,
                ["A recurrent quantum model made reversible, with identical click statistics.",
                 "Amplitude amplification on its histories, with the answer preserved in the ideal case.",
                 "A lighter, noise-aware build that beat the textbook build on real IBM hardware.",
                 "Every number traceable to saved counts, compiled circuits and tests."]),
               ("WE DO NOT CLAIM", AMBER, 652,
                ["A quantum speedup. At this size an exact classical sampler is faster.",
                 "A detected defect. IBM qubits played the roles of a model we programmed.",
                 "Any measurement of photons, lasers or wafers.",
                 "That amplitude amplification is ours. It is established prior work."])]
    for head, color, x, items in columns:
        panel(s, x, 132, 564, 388, outline=color)
        text(s, x + 24, 146, 500, 24, head, size=14, bold=True, color=color, tracking=1.6)
        for i, item in enumerate(items):
            text(s, x + 24, 184 + i * 82, 26, 30, "•", size=22, color=color, bold=True)
            text(s, x + 50, 182 + i * 82, 492, 76, item, size=19, color=CREAM, line=1.2)
    panel(s, 64, 538, 1152, 110, fill=PANEL_2)
    text(s, 88, 550, 300, 24, "NEXT EXPERIMENT", size=14, bold=True, color=CYAN, tracking=1.6)
    text(s, 88, 578, 1104, 64,
         "Fit candidate models to held-out, calibrated device records and compare with a strong classical hidden-Markov baseline. "
         "Then find where a larger hidden memory makes the classical sampler the bottleneck.", size=19, color=CREAM, line=1.2)
    return s


def slide_team(prs, e, qr: Path):
    s = base(prs, 13, "Team Qubits · Florida Gulf Coast University", two_tone("What we built, ", "and what we learned."),
             footer="The QRSM idea and its exact filter predate the event. Amplitude amplification is prior work. "
                    "Built with AI assistance (Claude, Codex); the team set the questions and checked the results.")
    people = [("Nicholas Taylor", "QRSM research, the Grover fusion, experiments"),
              ("Timofey Yudintsev", "Research, and the keyword-search idea"),
              ("Dan Izquierdo", "Experimentation, and the 45-second video"),
              ("Dillon Satria Sitepu", "Formatting and revising")]
    for i, (name, role) in enumerate(people):
        y = 136 + i * 104
        panel(s, 64, y, 500, 92)
        text(s, 86, y + 12, 460, 32, name, size=24, bold=True, color=CREAM)
        text(s, 86, y + 48, 460, 36, role, size=17, color=SOFT)
    text(s, 604, 136, 400, 24, "WHAT WE LEARNED", size=14, bold=True, color=CYAN, tracking=1.6)
    lessons = [("More hits is not more truth.", "A noisy circuit can return the right bit for the wrong reason. Check the answer, not only the hit rate."),
               ("On today’s hardware, lighter wins.", f"{e['local_gates']} gates beat {e['full_gates']}, in the run and in the noise model."),
               ("Report what goes against you.",
                f"A conventional sensor beat our quantum add-on, {pct(e['monitor']['two_classical'], 0)} to "
                f"{pct(e['monitor']['classical_quantum'], 0)}. It is in the deck.")]
    for i, (head, body) in enumerate(lessons):
        y = 172 + i * 126
        text(s, 604, y, 396, 60, head, size=22, bold=True, color=AMBER, line=1.1)
        text(s, 604, y + 34, 396, 84, body, size=16.5, color=SOFT, line=1.18)
    picture(s, qr.name, 1036, 172, w=180, folder=qr.parent, outline=None)
    text(s, 1016, 360, 220, 60, "Code, Lab and evidence", size=15.5, color=SOFT, align=PP_ALIGN.CENTER)
    text(s, 604, 566, 612, 60, "Thank you. Questions?", size=34, bold=True, color=CYAN, anchor=MSO_ANCHOR.MIDDLE)
    return s


# ---------------------------------------------------------------------------- assemble


def build(cinematic: Path, lab_video: Path) -> dict:
    e = evidence()
    script = load("finals-deck/v3_notes.json")
    lab_poster = MEDIA / "lab-tour-poster.png"
    cinematic_poster = MEDIA / "cinematic-poster.jpg"
    for needed in (V2, lab_video, lab_poster, cinematic, cinematic_poster):
        if not needed.is_file():
            sys.exit(f"Missing {needed.relative_to(ROOT)}. Run: python lab/capture.py deck && python lab/capture.py tour")
    qr = qr_png(REPO_URL, ASSETS / "qr-repo.png")

    prs = Presentation(str(V2))
    ids = prs.slides._sldIdLst
    old = list(ids)
    assert len(old) == 35, "the V2 deck has 35 slides"
    for slide_id in old[1:]:                            # only the cover is kept; every other slide is rebuilt here
        prs.part.drop_rel(slide_id.rId)
        ids.remove(slide_id)
    renumber(prs)                                       # python-pptx names a new slide by count, so close the gaps first

    index = backup_index(MAIN_SLIDES + 1)
    builders = [slide_problem, slide_model, slide_question, slide_cost, slide_why_quantum, slide_method, slide_hardware,
                slide_noise, lambda p, ev: slide_demo(p, ev, lab_video, lab_poster, qr), slide_impact, slide_claims,
                lambda p, ev: slide_team(p, ev, qr)]
    for builder, entry in zip(builders, script["main"][1:]):
        notes(builder(prs, e), entry)
    build_backups(prs, e, script, MAIN_SLIDES + 1, cinematic, cinematic_poster)

    slides = list(prs.slides)
    renumber(prs)
    notes(slides[0], script["main"][0])
    prs.core_properties.title = "Rewind & Amplify: finals deck V3"
    prs.core_properties.author = "FGCU Qubits"
    prs.save(str(OUTPUT))
    return {"total": len(slides), "main": MAIN_SLIDES, "backups": index, "evidence": e}


def renumber(prs) -> None:
    """Name slide and notes parts 1..n in presentation order, so file names match slide numbers and never collide."""
    slides = list(prs.slides)
    for i, slide in enumerate(slides, 1):
        slide.part.partname = PackURI(f"/ppt/slides/slide{i + 1000}.xml")
        if slide.has_notes_slide:
            slide.notes_slide.part.partname = PackURI(f"/ppt/notesSlides/notesSlide{i + 1000}.xml")
    for i, slide in enumerate(slides, 1):
        slide.part.partname = PackURI(f"/ppt/slides/slide{i}.xml")
        if slide.has_notes_slide:
            slide.notes_slide.part.partname = PackURI(f"/ppt/notesSlides/notesSlide{i}.xml")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cinematic", type=Path, default=MEDIA / "cinematic-45s.mp4",
                        help="the cinematic cut to embed on the optional cold-open slide")
    parser.add_argument("--lab-video", type=Path, default=MEDIA / "lab-tour.mp4",
                        help="the Lab recording for slide 10: the 70-second tour, or media/lab-tour-45s.mp4")
    args = parser.parse_args()
    result = build(args.cinematic.resolve(), args.lab_video.resolve())
    print(json.dumps({"status": "built", "file": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
                      "slides": result["total"], "main": result["main"], "bytes": OUTPUT.stat().st_size}))


if __name__ == "__main__":
    main()
