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

import build_v3_deck
import deck_kit
import v3_backups

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PPTX, PDF = HERE / "Rewind_Amplify_Finals_V3.pptx", HERE / "Rewind_Amplify_Finals_V3.pdf"
GUIDE, MANIFEST, SHEET = HERE / "Presenter_Guide_V3.md", HERE / "v3_manifest.json", HERE / "main-slides.png"
BACKUP_SHEET = HERE / "backup-slides.png"
PREVIEW = HERE / "preview"
MAIN = 13
DEMO_SECONDS = 71        # the Lab recording on slide 10
# what the deck is built from besides the saved results; the results themselves are listed by evidence_files()
INPUTS = ["finals-deck/v3_notes.json", "finals-deck/v2/Rewind_Amplify_Finals_Visual.pptx", "media/lab-tour.mp4", "media/cinematic-45s.mp4"]


def evidence_files() -> list[str]:
    """Every saved result a slide reads a number from: collected by running the builder's own readers, so the list
    cannot fall behind the slides. A change to any of these files means the deck must be rebuilt."""
    deck_kit.LOADED.clear()
    v3_backups.backup_evidence(build_v3_deck.evidence())
    build_v3_deck.slide_impact_sources()
    return sorted(deck_kit.LOADED | set(INPUTS))


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
             f"**{MAIN} main slides, planned {end // 60}:{end % 60:02d} including a {DEMO_SECONDS - 1}-second Lab demo. The limit is 10:00.** "
             f"The narration below is {words:,} words, about {words / end * 60:.0f} words a minute overall.",
             "", script["plan"], "",
             "The same notes are inside the PowerPoint. Slides 14 onward are backups for questions: slide 14 is a map of them, "
             "and each one's note says when to show it.", "",
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
        note = note.replace("SHOW THIS WHEN: ", "**Show this when.** ").replace("SOURCES: ", "**Sources.** ")
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
        # and the backups, smaller: enough to find a slide by its look
        cell_w, cell_h, gap, columns = 400, 225, 10, 5
        backups = previews[MAIN:]
        rows = -(-len(backups) // columns)
        sheet = Image.new("RGB", (columns * cell_w + (columns + 1) * gap, rows * cell_h + (rows + 1) * gap), (5, 13, 22))
        for i, path in enumerate(backups):
            tile = Image.open(path).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
            sheet.paste(tile, (gap + (i % columns) * (cell_w + gap), gap + (i // columns) * (cell_h + gap)))
        sheet.save(BACKUP_SHEET, optimize=True)
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
        "deck": PPTX.name, "pdf": PDF.name, "presenter_guide": GUIDE.name, "contact_sheet": SHEET.name, "backup_contact_sheet": BACKUP_SHEET.name,
        "main_slide_count": MAIN, "total_slide_count": len(slides), "notes_count": sum(s.has_notes_slide for s in slides),
        "talk_timing_seconds": end, "demo_seconds": DEMO_SECONDS, "time_limit_seconds": 600, "speaking_script_words": words,
        "embedded_videos": {"count": len(videos), "slides": video_slides, "parts": videos},
        "powerpoint_check": report,
        "sha256": {p.name: sha(p) for p in (PPTX, PDF, GUIDE) if p.is_file()},
        "source_sha256": {rel: sha(ROOT / rel) for rel in evidence_files()},
        "build": ["finals-deck/deck_kit.py", "finals-deck/build_v3_deck.py", "finals-deck/v3_backups.py", "finals-deck/finish_v3_deck.ps1",
                  "finals-deck/finish_v3_deck.py"],
        "limitations": [f"{end // 60}:{end % 60:02d} is a planned timeline; the team must rehearse the actual delivery.",
                        "Speaker assignments in the notes are suggestions.",
                        "The PDF shows a still frame where the deck has a video."],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "finished", "slides": len(slides), "videos_on_slides": video_slides,
                      "talk": f"{end // 60}:{end % 60:02d}", "words": words, "pdf": PDF.is_file()}))


if __name__ == "__main__":
    main()
