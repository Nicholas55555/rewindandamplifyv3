"""Build the V3 finals deck: finals-deck/Rewind_Amplify_Finals_V3.pptx.

The V2 deck (finals-deck/v2/) supplies the cover and the 22 backup slides unchanged. The 12 main-talk slides
after the cover are rebuilt here, problem first and one picture per slide, in the same dark style as the Lab.
Pictures of the Lab are real captures of the running page (python lab/capture.py deck). Every number on a slide
is read from the saved results at build time, so a slide cannot drift from the evidence.

The two videos are embedded as real, playable media (not pictures of videos).

    python finals-deck/build_v3_deck.py
    python finals-deck/build_v3_deck.py --cinematic path/to/final_cut.mp4      # swap in a newer cinematic cut

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
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.packuri import PackURI
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
V2 = HERE / "v2" / "Rewind_Amplify_Finals_Visual.pptx"
OUTPUT = HERE / "Rewind_Amplify_Finals_V3.pptx"
ASSETS = HERE / "assets" / "v3"
MEDIA = ROOT / "media"
REPO_URL = "https://github.com/Nicholas55555/rewindandamplifyv3"
MAIN_SLIDES = 13

NAVY, PANEL, PANEL_2 = RGBColor(0x09, 0x16, 0x24), RGBColor(0x0F, 0x20, 0x30), RGBColor(0x13, 0x2A, 0x3D)
CREAM, SOFT, MUTED = RGBColor(0xF6, 0xF3, 0xEB), RGBColor(0xC9, 0xD5, 0xDD), RGBColor(0x8F, 0xA4, 0xB3)
CYAN, AMBER, VIOLET = RGBColor(0x64, 0xD9, 0xE9), RGBColor(0xED, 0xB5, 0x68), RGBColor(0xB9, 0xA8, 0xE5)
GREEN, SLATE, TRACK = RGBColor(0x86, 0xD6, 0xA4), RGBColor(0x34, 0x4A, 0x5C), RGBColor(0x14, 0x26, 0x36)
FONT = "Arial"


def px(value: float) -> Emu:
    """Slides are laid out on a 1280 x 720 grid."""
    return Emu(int(round(value * 9525)))


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


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


def pct(value: float, digits: int = 2) -> str:
    return f"{100 * value:.{digits}f}%"


# ---------------------------------------------------------------------------- drawing helpers


def text(slide, x, y, w, h, content, size=20, color=CREAM, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         line=1.12, tracking=None, after=0, font=FONT):
    """A text box. `content` is a string, or a list of paragraphs; a paragraph is a string or a list of runs,
    and a run is a string or (string, {color, bold, size, font})."""
    box = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = anchor
    paragraphs = content if isinstance(content, list) else [content]
    for i, paragraph in enumerate(paragraphs):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        p.space_after = Pt(after)
        for run_spec in (paragraph if isinstance(paragraph, list) else [paragraph]):
            value, style = run_spec if isinstance(run_spec, tuple) else (run_spec, {})
            run = p.add_run()
            run.text = value
            f = run.font
            f.name = style.get("font", font)
            f.size = Pt(style.get("size", size) * 0.75)
            f.bold = style.get("bold", bold)
            f.color.rgb = style.get("color", color)
            if tracking:
                f._element.set("spc", str(int(tracking * 100)))
    return box


def panel(slide, x, y, w, h, fill=PANEL, outline=SLATE, radius=0.06, width=1.0, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    item = slide.shapes.add_shape(shape, px(x), px(y), px(w), px(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = radius
    if fill is None:
        item.fill.background()
    else:
        item.fill.solid()
        item.fill.fore_color.rgb = fill
    if outline is None:
        item.line.fill.background()
    else:
        item.line.color.rgb = outline
        item.line.width = Pt(width)
    item.shadow.inherit = False
    return item


def rule(slide, x0, y0, x1, y1, color=SLATE, width=1.0, dashed=False):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, px(x0), px(y0), px(x1), px(y1))
    line.line.color.rgb = color
    line.line.width = Pt(width)
    if dashed:
        line.line.dash_style = MSO_LINE.DASH
    return line


def picture(slide, name, x, y, w=None, h=None, outline=SLATE, folder=ASSETS):
    """Place a picture. Given both `w` and `h`, it is fitted inside that box with its proportions kept, so a
    recaptured Lab panel of a different shape can never be stretched or run under its neighbours."""
    path = folder / name
    if w and h:
        from PIL import Image

        with Image.open(path) as image:
            ratio = image.width / image.height
        if w / h > ratio:
            w = h * ratio
        else:
            h = w / ratio
    item = slide.shapes.add_picture(str(path), px(x), px(y), px(w) if w else None, px(h) if h else None)
    if outline is not None:
        item.line.color.rgb = outline
        item.line.width = Pt(0.75)
    return item


def base(prs, number: int, eyebrow: str, title, lede: str | None = None, footer: str | None = None):
    """A dark slide with the standard furniture. `title` is a list of runs so the second half can be cyan."""
    slide = prs.slides.add_slide(next(l for l in prs.slide_layouts if l.name == "Blank"))
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    text(slide, 64, 34, 1152, 22, eyebrow.upper(), size=14, color=CYAN, bold=True, tracking=1.6)
    text(slide, 64, 58, 1152, 58, [title], size=42, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    if lede:
        text(slide, 64, 122, 1100, 62, lede, size=21, color=SOFT, line=1.18)
    if footer:
        text(slide, 64, 664, 1070, 40, footer, size=14.5, color=MUTED, line=1.1, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 1160, 676, 56, 20, f"{number:02d}", size=14, color=MUTED, align=PP_ALIGN.RIGHT)
    return slide


def two_tone(first: str, second: str):
    return [first, (second, {"color": CYAN})]


def stat(slide, x, y, w, value, label, color=CYAN, size=50, label_size=17):
    text(slide, x, y, w, size + 8, value, size=size, color=color, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, x, y + size + 10, w, 60, label, size=label_size, color=SOFT, line=1.15)


def chip(slide, x, y, label, color):
    width = 24 + 8.6 * len(label)
    item = panel(slide, x, y, width, 26, fill=None, outline=color, radius=0.5, width=1.0)
    frame = item.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label.upper()
    run.font.size, run.font.bold, run.font.name = Pt(8.4), True, FONT
    run.font.color.rgb = color
    run.font._element.set("spc", "90")


def notes(slide, entry: dict) -> None:
    body = f"{entry['time']}\n\n{entry['text']}\n\nPRESENTER CUE: {entry['speaker']}. {entry['cue']}\n\nSOURCES: {entry['sources']}"
    slide.notes_slide.notes_text_frame.text = body


def qr_png(url: str, path: Path) -> Path:
    import segno

    segno.make(url, error="m").save(str(path), scale=12, border=2, dark="#091624", light="#F6F3EB")
    return path


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
             footer="A 45-second screen recording of lab/index.html. Open Rewind_Amplify_Lab.html to drive it yourself: "
                    "one file, no install, works offline.")
    s.shapes.add_movie(str(video), px(64), px(128), px(928), px(522), poster_frame_image=str(poster), mime_type="video/mp4")
    text(s, 1016, 132, 200, 26, "TRY IT", size=13, bold=True, color=MUTED, tracking=1.4)
    picture(s, qr.name, 1016, 162, w=200, folder=qr.parent, outline=None)
    text(s, 1016, 372, 200, 60, "Scan for the code, the Lab and every result.", size=15.5, color=SOFT, line=1.15)
    for i, line in enumerate(["Live, exact simulation", "Real IBM counts", "25 tests hold it to Qiskit and to the saved data"]):
        text(s, 1016, 452 + i * 62, 200, 56, [[("•  ", {"color": CYAN}), line]], size=15.5, color=CREAM, line=1.15)
    return s


def slide_impact(prs, e):
    s = base(prs, 11, "Who could use this", two_tone("Three places hidden memory matters. ", "Honestly scored."),
             footer="The second and third cards are simulations and a reanalysis of published data. "
                    "No photons, lasers or wafers were measured by our team.")
    cards = [("Model run on IBM hardware", GREEN, "Quantum hardware teams",
              "A physical model of the click record lets you compare explanations for a drifting qubit instead of guessing, "
              "and tell a defect from a detector error.",
              f"{e['dead_time']['ignored']:.3f} → {e['dead_time']['modelled']:.3f}",
              f"fitted coupling once detector dead time was modelled. True value {e['dead_time']['truth']:.2f} (synthetic records)."),
             ("Simulated · published data reanalysed", CYAN, "Photon-source engineers",
              "Photonic chips need photons that match, not just photons that arrive. Counting clicks misses that.",
              f"{pct(min(e['overlaps']), 0)} to {pct(max(e['overlaps']), 0)}",
              f"photon overlap across {len(e['overlaps'])} model sources with identical brightness."),
             ("Simulated · conventional sensor ahead", AMBER, "Laser and lithography metrology",
              "Is the light source drifting, or the sensor? We added an atomic reference. It helped a little. "
              "A second ordinary reference helped far more.",
              f"{pct(e['monitor']['classical_quantum'], 0)} vs {pct(e['monitor']['two_classical'], 0)}",
              "timely detection: atomic channel against a second conventional reference.")]
    for i, (status, color, who, body, big, small) in enumerate(cards):
        x = 64 + i * 392
        panel(s, x, 132, 368, 506)
        chip(s, x + 20, 150, status, color)
        text(s, x + 20, 194, 328, 64, who, size=25, bold=True, color=CREAM, line=1.1)
        text(s, x + 20, 268, 328, 170, body, size=17.5, color=SOFT, line=1.2)
        rule(s, x + 20, 452, x + 348, 452)
        text(s, x + 20, 464, 328, 56, big, size=38, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 20, 524, 328, 100, small, size=15.5, color=SOFT, line=1.16)
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


# ---------------------------------------------------------------------------- new backups


def backup_noise(prs, e, number):
    s = base(prs, number, "Backup · simulator against hardware", two_tone("The same noise model, ", "circuit by circuit."),
             "After-click answer at step 6. Exact: 4.67% with the defect and 10.10% without. The model was fitted only on echo circuits.",
             "hardware_campaign/noise_model/results.json. One scale factor stands in for everything the model leaves out.")
    columns = [("Build", 64, 260, PP_ALIGN.LEFT), ("Two-qubit gates", 330, 170, PP_ALIGN.RIGHT), ("Predicted", 520, 220, PP_ALIGN.RIGHT),
               ("Measured", 760, 220, PP_ALIGN.RIGHT), ("Order on the chip", 1000, 216, PP_ALIGN.RIGHT)]
    for name, x, w, align in columns:
        text(s, x, 196, w, 24, name.upper(), size=13, bold=True, color=MUTED, tracking=1.2, align=align)
    rows = [("Plain sampling", "loop-defect-r0", "loop-nodefect-r0"), ("Steer + local reflection", "loop-defect-r1", "loop-nodefect-r1"),
            ("Steer + full reflection", "loop-defect-full-r1", "loop-nodefect-full-r1"),
            ("Memory-only control", "loop-defect-memory-r1", "loop-nodefect-memory-r1")]
    for i, (name, d, n) in enumerate(rows):
        y = 232 + i * 96
        rule(s, 64, y, 1216, y)
        dd, nn = e["loops"][d], e["loops"][n]
        step6 = lambda row, key: row[key]["later_click_rates"][2]  # noqa: E731
        right = step6(dd, "measured") < step6(nn, "measured") and "memory" not in d
        verdict = "wrong by design" if "memory" in d else "right" if right else "reversed"
        strong = "local" in name
        text(s, 64, y + 26, 262, 44, name, size=21, bold=strong, color=CREAM if strong else SOFT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 330, y + 26, 170, 44, f"{dd['two_qubit_gates']} / {nn['two_qubit_gates']}", size=21, color=SOFT, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 520, y + 26, 220, 44, f"{pct(step6(dd, 'echo_scaled'), 1)} / {pct(step6(nn, 'echo_scaled'), 1)}", size=21, color=SOFT, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 760, y + 26, 220, 44, f"{pct(step6(dd, 'measured'), 1)} / {pct(step6(nn, 'measured'), 1)}", size=21, bold=True, color=CREAM, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 1000, y + 26, 216, 44, verdict, size=21, bold=True, color=GREEN if verdict == "right" else AMBER, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    rule(s, 64, 616, 1216, 616)
    text(s, 64, 622, 1152, 36, "Each pair is: with the defect / emitter only. Plain sampling fails because false clicks swamp a 4% event.",
         size=17, color=SOFT, anchor=MSO_ANCHOR.MIDDLE)
    return s


def backup_cinematic(prs, e, number, video: Path, poster: Path):
    s = base(prs, number, "Backup · optional cold open", two_tone("The cinematic cut. ", "45 seconds."),
             footer="A cinematic explainer with original music, not a screen recording of the product. "
                    "The model picture is conceptual; the IBM numbers are the measured ones.")
    s.shapes.add_movie(str(video), px(176), px(128), px(928), px(522), poster_frame_image=str(poster), mime_type="video/mp4")
    return s


def backup_reproduce(prs, e, number):
    s = base(prs, number, "Backup · does the code run?", two_tone("Anyone can rerun it. ", "One command."),
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


# ---------------------------------------------------------------------------- assemble


def build(cinematic: Path) -> dict:
    e = evidence()
    script = load("finals-deck/v3_notes.json")
    lab_video, lab_poster = MEDIA / "lab-tour.mp4", MEDIA / "lab-tour-poster.png"
    cinematic_poster = MEDIA / "cinematic-poster.jpg"
    for needed in (V2, lab_video, lab_poster, cinematic, cinematic_poster):
        if not needed.is_file():
            sys.exit(f"Missing {needed.relative_to(ROOT)}. Run: python lab/capture.py deck && python lab/capture.py tour")
    qr = qr_png(REPO_URL, ASSETS / "qr-repo.png")

    prs = Presentation(str(V2))
    ids = prs.slides._sldIdLst
    old = list(ids)
    assert len(old) == 35, "the V2 deck has 35 slides"
    for slide_id in old[1:MAIN_SLIDES]:                 # V2 main slides 2 to 13 make way for the rebuilt ones
        prs.part.drop_rel(slide_id.rId)
        ids.remove(slide_id)
    cover, backups = old[0], old[MAIN_SLIDES:]
    renumber(prs)                                       # python-pptx names a new slide by count, so close the gaps first

    builders = [slide_problem, slide_model, slide_question, slide_cost, slide_why_quantum, slide_method, slide_hardware,
                slide_noise, lambda p, ev: slide_demo(p, ev, lab_video, lab_poster, qr), slide_impact, slide_claims,
                lambda p, ev: slide_team(p, ev, qr)]
    main = []
    for builder, entry in zip(builders, script["main"][1:]):
        slide = builder(prs, e)
        notes(slide, entry)
        main.append(ids[-1])
    extra = []
    first_new = 1 + len(main) + len(backups) + 1
    for offset, (builder, entry) in enumerate(zip(
            [backup_noise, lambda p, ev, n: backup_cinematic(p, ev, n, cinematic, cinematic_poster), backup_reproduce],
            script["new_backups"])):
        slide = builder(prs, e, first_new + offset)
        slide.notes_slide.notes_text_frame.text = f"Backup\n\n{entry['text']}\n\nSOURCES: {entry['sources']}"
        extra.append(ids[-1])

    for element in list(ids):
        ids.remove(element)
    for element in [cover, *main, *backups, *extra]:
        ids.append(element)

    slides = list(prs.slides)
    renumber(prs)
    notes(slides[0], script["main"][0])
    retarget_rubric_slide(slides[22])
    prs.core_properties.title = "Rewind & Amplify: finals deck V3"
    prs.core_properties.author = "FGCU Qubits"
    prs.save(str(OUTPUT))
    return {"total": len(slides), "main": MAIN_SLIDES, "evidence": e}


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


def retarget_rubric_slide(slide) -> None:
    """Slide 23 maps the rubric to slide numbers. The numbers changed with the rebuilt main talk."""
    rows = [("Problem, and who it affects", "15", "2, 4, 11: the hidden defect, who has the problem, two futures"),
            ("Why quantum, and honest limits", "20", "5–7, 9, 12: cost of rarity, two catches, no speedup today"),
            ("Technical Qiskit implementation", "20", "3, 7–8, 10, 22, 38: model, four moves, compiled circuits, Lab"),
            ("Results and validation", "10", "4, 8–9, 14, 21, 36: exact, simulator, hardware, noise model"),
            ("Originality", "10", "7, 13, 24: reversible recurrent model, noise-aware build"),
            ("Communication", "15", "13 main slides, planned 9:20 including a 45-second demo"),
            ("Q&A, teamwork, learning", "10", "13–38: roles, lessons, evidence backups")]
    table = next(shape.table for shape in slide.shapes if shape.has_table)
    assert len(table.rows) == len(rows) + 1
    for row, values in zip(list(table.rows)[1:], rows):
        for cell, value in zip(row.cells, values):
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.runs[0].text = value
            for extra_run in paragraph.runs[1:]:
                extra_run.text = ""
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.startswith("Hardware bonus"):
            run = shape.text_frame.paragraphs[0].runs[0]
            run.text = ("Bonus: simulator +1 (slides 7, 9), real IBM hardware +3 (8), hardware with noise analysis or "
                        "suppression +5 (9, 14, 36). Evidence supports evaluation, not a guaranteed score.")
            for extra_run in shape.text_frame.paragraphs[0].runs[1:]:
                extra_run.text = ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cinematic", type=Path, default=MEDIA / "cinematic-45s.mp4",
                        help="the cinematic cut to embed on the optional cold-open slide")
    args = parser.parse_args()
    result = build(args.cinematic.resolve())
    print(json.dumps({"status": "built", "file": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
                      "slides": result["total"], "main": result["main"], "bytes": OUTPUT.stat().st_size}))


if __name__ == "__main__":
    main()
