"""Finish the V3 deck: write the presenter guide, a contact sheet of the main slides, and the manifest.

Run after build_v3_deck.py and finish_v3_deck.ps1 (which exports the PDF and the slide previews with PowerPoint):

    python finals-deck/build_v3_deck.py
    powershell -ExecutionPolicy Bypass -File finals-deck\\finish_v3_deck.ps1
    python finals-deck/finish_v3_deck.py

check_finals.py then verifies everything recorded here. Needs python-pptx and pillow.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from PIL import Image
from pptx import Presentation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PPTX, PDF = HERE / "Rewind_Amplify_Finals_V3.pptx", HERE / "Rewind_Amplify_Finals_V3.pdf"
GUIDE, MANIFEST, SHEET = HERE / "Presenter_Guide_V3.md", HERE / "v3_manifest.json", HERE / "main-slides.png"
PREVIEW = HERE / "preview"
MAIN = 13
# every saved result the builder reads a number from; a change to any of them means the deck must be rebuilt
EVIDENCE = [
    "research-validation/original_after_click_verification.json",
    "hardware_campaign/runs/original_precision_v1/hero_acceptance_contrast.json",
    "hardware_campaign/runs/original_precision_v1/job.json",
    "hardware_campaign/runs/original_plain_v2/analysis.json",
    "hardware_campaign/runs/original_suppressed_v1/analysis.json",
    "hardware_campaign/results.json",
    "hardware_campaign/noise_model/results.json",
    "rewindandamplify-main/results/numbers.json",
    "laser_sensor_viability/followup/main/results.json",
    "qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit0.json",
    "qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit1.json",
    "quantum_dot_bridge/results.json",
    "finals-deck/v3_notes.json",
    "finals-deck/v2/Rewind_Amplify_Finals_Visual.pptx",
    "media/lab-tour.mp4",
    "media/cinematic-45s.mp4",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seconds(stamp: str) -> int:
    minutes, secs = stamp.split(":")
    return 60 * int(minutes) + int(secs)


def slide_title(slide) -> str:
    """The title box: a tall text box near the top. The cover has none there, so fall back to its largest text."""
    px = 9525
    boxes = [shape for shape in slide.shapes if shape.has_text_frame and shape.text_frame.text.strip()
             and 40 * px <= shape.top <= 70 * px and shape.height >= 50 * px]
    if boxes:
        return re.sub(r"\s+", " ", min(boxes, key=lambda shape: shape.top).text_frame.text.strip())
    best, size = "", 0
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                if run.font.size and run.font.size > size and len(shape.text_frame.text.strip()) > 3:
                    best, size = shape.text_frame.text.strip(), run.font.size
    return re.sub(r"\s+", " ", best)


def main() -> None:
    script = json.loads((HERE / "v3_notes.json").read_text(encoding="utf-8"))
    deck = Presentation(str(PPTX))
    slides = list(deck.slides)
    assert len(script["main"]) == MAIN
    end = 0
    for entry in script["main"]:
        start, stop = (seconds(t) for t in entry["time"].split("–"))
        assert start == end, f"the talk plan has a gap or overlap at {entry['time']}"
        end = stop
    words = sum(len(entry["text"].split()) for entry in script["main"])

    # ---- presenter guide
    lines = ["# Presenter guide: finals deck V3", "",
             f"**{MAIN} main slides, planned {end // 60}:{end % 60:02d} including a 45-second Lab demo. The limit is 10:00.** "
             f"The narration below is {words:,} words, about {words / (end - 45) * 60:.0f} words a minute outside the demo.",
             "", script["plan"], "",
             "The same notes are inside the PowerPoint. Slides 14 onward are backups for questions.", "",
             "| Slide | Time | Speaker | Title |", "|---:|---|---|---|"]
    for i, entry in enumerate(script["main"], 1):
        lines.append(f"| {i} | {entry['time']} | {entry['speaker']} | {slide_title(slides[i - 1])} |")
    lines += ["", "## Main talk", ""]
    for i, entry in enumerate(script["main"], 1):
        lines += [f"### {i}. {slide_title(slides[i - 1])}", "", f"*{entry['time']} · {entry['speaker']}*", "", entry["text"], "",
                  f"**Cue.** {entry['cue']}", "", f"**Sources.** {entry['sources']}", ""]
    lines += ["## Backups", "", "| Slide | Title |", "|---:|---|"]
    for i in range(MAIN + 1, len(slides) + 1):
        lines.append(f"| {i} | {slide_title(slides[i - 1])} |")
    lines.append("")
    for i in range(MAIN + 1, len(slides) + 1):
        note = slides[i - 1].notes_slide.notes_text_frame.text.strip()
        note = re.sub(r"^Backup\s*", "", note)
        lines += [f"### {i}. {slide_title(slides[i - 1])}", "", note, ""]
    GUIDE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")

    # ---- contact sheet of the main slides, for the README
    report = {}
    previews = sorted(PREVIEW.glob("slide-*.png"))
    if len(previews) == len(slides):
        cell_w, cell_h, gap, columns = 480, 270, 12, 4
        rows = -(-MAIN // columns)
        sheet = Image.new("RGB", (columns * cell_w + (columns + 1) * gap, rows * cell_h + (rows + 1) * gap), (5, 13, 22))
        for i, path in enumerate(previews[:MAIN]):
            tile = Image.open(path).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
            sheet.paste(tile, (gap + (i % columns) * (cell_w + gap), gap + (i // columns) * (cell_h + gap)))
        sheet.save(SHEET, optimize=True)
        report = json.loads((PREVIEW / "powerpoint_report.json").read_text(encoding="utf-8-sig"))
        assert report["slides"] == len(slides)
    else:
        print("No PowerPoint previews found: run finish_v3_deck.ps1 first. The PDF and contact sheet were not refreshed.")

    # ---- manifest
    with zipfile.ZipFile(PPTX) as package:
        names = package.namelist()
        videos = sorted(n for n in names if n.startswith("ppt/media/") and n.endswith(".mp4"))
        video_slides = []
        for i in range(1, len(slides) + 1):
            xml = package.read(f"ppt/slides/slide{i}.xml").decode("utf-8")
            if "videoFile" in xml:
                assert "p14:media" in xml and "<p:timing" in xml, f"slide {i} has an incomplete video"
                video_slides.append(i)
        assert "video/mp4" in package.read("[Content_Types].xml").decode("utf-8")
    manifest = {
        "schema": 1,
        "deck": PPTX.name, "pdf": PDF.name, "presenter_guide": GUIDE.name, "contact_sheet": SHEET.name,
        "main_slide_count": MAIN, "total_slide_count": len(slides), "notes_count": sum(s.has_notes_slide for s in slides),
        "talk_timing_seconds": end, "demo_seconds": 45, "time_limit_seconds": 600, "speaking_script_words": words,
        "embedded_videos": {"count": len(videos), "slides": video_slides, "parts": videos},
        "powerpoint_check": report,
        "sha256": {p.name: sha(p) for p in (PPTX, PDF, GUIDE) if p.is_file()},
        "source_sha256": {rel: sha(ROOT / rel) for rel in EVIDENCE},
        "build": ["finals-deck/build_v3_deck.py", "finals-deck/finish_v3_deck.ps1", "finals-deck/finish_v3_deck.py"],
        "limitations": ["9:20 is a planned timeline; the team must rehearse the actual delivery.",
                        "Speaker assignments in the notes are suggestions.",
                        "The PDF shows a still frame where the deck has a video."],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "finished", "slides": len(slides), "videos_on_slides": video_slides,
                      "talk": f"{end // 60}:{end % 60:02d}", "words": words, "pdf": PDF.is_file()}))


if __name__ == "__main__":
    main()
