"""Render the deck's slide files locally: a PDF, one PNG per slide, and a PowerPoint with the speaker notes.

The slides in deck/project/ use plain HTML and inline styles, so a browser can draw them directly. Headless Chrome (or
Edge) does the drawing. Images on the slides are referred to by their uploaded URLs; deck/assets.json maps each of those
to its file here.

    python tools/render_deck.py
"""

import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck"
OUT = DECK / "render"
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

FONTS = ("<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;600&display=swap'>")
BASE = """<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
section{position:relative;width:1920px;height:1080px;overflow:hidden;page-break-after:always;break-after:page}
aside{display:none}
h1,h2,h3,p,ul,ol{margin:0}
table{border-collapse:collapse;width:100%}
td,th{padding:.35em .6em;text-align:left;vertical-align:top;border-bottom:1px solid #DDDAD0}
@page{size:1920px 1080px;margin:0}
</style>"""


CIRCUITS = {"qrsmcircuit": ("fig_circuit_hybrid.png", 176, 562), "grovercircuit": ("fig_circuit_grover.png", 176, 558)}


def slides() -> list:
    index = json.loads((DECK / "project" / "deck.json").read_text(encoding="utf-8"))
    assets = json.loads((DECK / "assets.json").read_text(encoding="utf-8"))
    out = []
    for slide_id in index["order"]:
        text = (DECK / "project" / "slides" / f"{slide_id}.html").read_text(encoding="utf-8")
        for url, path in assets.items():
            text = text.replace(url, (ROOT / path).as_uri())
        notes = re.search(r"<aside>(.*?)</aside>", text, re.S)
        out.append({"id": slide_id, "html": text, "notes": html.unescape(notes.group(1).strip()) if notes else ""})
    return out


def headless(args: list, seconds: int = 90) -> None:
    """Run a headless browser with a fresh profile. Chrome goes first: Edge's Startup Boost can swallow the command."""
    browser = next(b for b in BROWSERS if Path(b).exists())
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--user-data-dir={profile}", *args], timeout=seconds, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    deck = slides()
    all_slides = OUT / "deck.html"
    all_slides.write_text(f"<!doctype html><meta charset='utf-8'>{FONTS}{BASE}" + "".join(s["html"] for s in deck), encoding="utf-8")
    pdf = DECK / "Rewind_and_Amplify_deck.pdf"
    pdf.unlink(missing_ok=True)  # so a failed print can't leave an old deck looking new
    headless(["--no-pdf-header-footer", "--virtual-time-budget=6000", f"--print-to-pdf={pdf}", all_slides.as_uri()], 120)
    if not pdf.exists():
        raise SystemExit("the browser did not write the PDF")
    print(f"  wrote {pdf.name}", flush=True)

    import pymupdf

    doc = pymupdf.open(pdf)
    if len(doc) != len(deck):
        print(f"  WARNING: {len(doc)} PDF pages for {len(deck)} slides", flush=True)
    for i, (page, s) in enumerate(zip(doc, deck), 1):
        png = OUT / f"slide_{i:02d}.png"
        page.get_pixmap(matrix=pymupdf.Matrix(1920 / page.rect.width, 1080 / page.rect.height)).save(png)
        print(f"  {png.name}: {s['id']}, {len(s['notes'].split())} words of notes", flush=True)
        if s["id"] in CIRCUITS:  # the drawing alone, for the README and the report
            name, top, height = CIRCUITS[s["id"]]
            x, y = page.rect.width / 1920, page.rect.height / 1080
            clip = pymupdf.Rect(124 * x, top * y, 1796 * x, (top + height) * y)
            page.get_pixmap(matrix=pymupdf.Matrix(2 * 1920 / page.rect.width, 2 * 1080 / page.rect.height), clip=clip).save(ROOT / "results" / "figures" / name)

    from pptx import Presentation
    from pptx.util import Emu

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    blank = prs.slide_layouts[6]
    for i, s in enumerate(deck, 1):
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(OUT / f"slide_{i:02d}.png"), 0, 0, prs.slide_width, prs.slide_height)
        slide.notes_slide.notes_text_frame.text = s["notes"]
    pptx = DECK / "Rewind_and_Amplify_deck_with_notes.pptx"
    prs.save(pptx)
    print(f"  wrote {pptx.name}", flush=True)
    words = sum(len(s["notes"].split()) for s in deck)
    print(f"  {len(deck)} slides, {words} words of notes: about {words / 140:.1f} minutes at 140 words a minute", flush=True)
    write_script(deck)


def write_script(deck: list) -> None:
    """The speaker notes as one plain document, with a start time for each slide at 140 words a minute."""
    lines = ["# Speaker script", "", "Generated from the slides by `tools/render_deck.py`. Times assume 140 words a minute with a short pause per slide.", ""]
    t = 0.0
    for i, s in enumerate(deck, 1):
        title = re.search(r"<h[12][^>]*>(.*?)</h[12]>", s["html"], re.S).group(1)
        lines += [f"## {i}. {html.unescape(re.sub('<[^>]+>', '', title))}  ({int(t // 60)}:{int(t % 60):02d})", "", s["notes"], ""]
        t += len(s["notes"].split()) / 140 * 60 + 2
    lines += [f"**Total: about {t / 60:.1f} minutes.**", ""]
    (DECK / "SPEAKER_SCRIPT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote SPEAKER_SCRIPT.md: about {t / 60:.1f} minutes", flush=True)


if __name__ == "__main__":
    main()
