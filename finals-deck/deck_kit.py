"""Shared drawing kit for the V3 finals deck: the palette, the 1280 x 720 grid and the slide furniture.

build_v3_deck.py draws the main talk with it and v3_backups.py draws the backups, so every slide has one look.
"""
from __future__ import annotations

import json
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets" / "v3"
MEDIA = ROOT / "media"


NAVY, PANEL, PANEL_2 = RGBColor(0x09, 0x16, 0x24), RGBColor(0x0F, 0x20, 0x30), RGBColor(0x13, 0x2A, 0x3D)
CREAM, SOFT, MUTED = RGBColor(0xF6, 0xF3, 0xEB), RGBColor(0xC9, 0xD5, 0xDD), RGBColor(0x8F, 0xA4, 0xB3)
CYAN, AMBER, VIOLET = RGBColor(0x64, 0xD9, 0xE9), RGBColor(0xED, 0xB5, 0x68), RGBColor(0xB9, 0xA8, 0xE5)
GREEN, SLATE, TRACK = RGBColor(0x86, 0xD6, 0xA4), RGBColor(0x34, 0x4A, 0x5C), RGBColor(0x14, 0x26, 0x36)
FONT = "Arial"


def px(value: float) -> Emu:
    """Slides are laid out on a 1280 x 720 grid."""
    return Emu(int(round(value * 9525)))


LOADED: set[str] = set()      # every evidence file a slide has read a number from


def load(path: str) -> dict:
    LOADED.add(path)
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def pct(value: float, digits: int = 2) -> str:
    return f"{100 * value:.{digits}f}%"



# ---------------------------------------------------------------------------- drawing helpers


def text(slide, x, y, w, h, content, size=20, color=CREAM, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         line=1.12, tracking=None, after=0, font=FONT):
    """A text box. `content` is a string, or a list of paragraphs; a paragraph is a string or a list of runs,
    and a run is a string or (string, {color, bold, size, font, sub})."""
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
            if style.get("sub"):
                f._element.set("baseline", "-25000")
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


def base(prs, number: int, eyebrow: str, title, lede: str | None = None, footer: str | None = None, title_size: float = 42):
    """A dark slide with the standard furniture. `title` is a list of runs so the second half can be cyan."""
    slide = prs.slides.add_slide(next(l for l in prs.slide_layouts if l.name == "Blank"))
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    text(slide, 64, 34, 1152, 22, eyebrow.upper(), size=14, color=CYAN, bold=True, tracking=1.6)
    text(slide, 64, 58, 1152, 58, [title], size=title_size, bold=True, anchor=MSO_ANCHOR.MIDDLE)
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


def chip_right(slide, label, color, y=30):
    """The evidence chip in the top right corner: what kind of evidence this slide shows."""
    chip(slide, 1216 - (24 + 8.6 * len(label)), y, label, color)


def table(slide, x, y, w, columns, rows, row_h=62, size=19, head_size=13, last_rule=True):
    """A dark table: muted capital headers and thin rules, no boxes.

    `columns` is a list of (label, fraction of the width, alignment). A cell is a string or (string, style),
    where style may set color, bold and size. Returns the y of the table's bottom edge."""
    spans, cx = [], x
    for label, fraction, align in columns:
        cw = w * fraction
        pad = 0 if align == PP_ALIGN.LEFT else 12
        spans.append((cx, cw - pad, align))
        text(slide, cx, y, cw - pad, 24, label.upper(), size=head_size, bold=True, color=MUTED, tracking=1.2, align=align,
             anchor=MSO_ANCHOR.BOTTOM, line=1.0)
        cx += cw
    top = y + 32
    for r, row in enumerate(rows):
        yy = top + r * row_h
        rule(slide, x, yy, x + w, yy)
        for (cx, cw, align), cell in zip(spans, row):
            value, style = cell if isinstance(cell, tuple) else (cell, {})
            text(slide, cx, yy + 3, cw, row_h - 6, [[(value, style)]], size=style.get("size", size), color=SOFT, align=align,
                 anchor=MSO_ANCHOR.MIDDLE, line=1.08)
    bottom = top + len(rows) * row_h
    if last_rule:
        rule(slide, x, bottom, x + w, bottom)
    return bottom


def bar(slide, x, y, w, h, fraction, color, track=True):
    """A horizontal bar filled to `fraction` of its track."""
    if track:
        panel(slide, x, y, w, h, fill=TRACK, outline=None, radius=0.3)
    if fraction > 0:
        panel(slide, x, y, max(w * min(fraction, 1.0), h * 0.5), h, fill=color, outline=None, radius=0.3)


def takeaway(slide, y, content, color=CYAN, size=24, x=64, w=1152, h=38):
    """The one line to remember, in colour."""
    text(slide, x, y, w, h, content, size=size, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE, line=1.1)


def notes(slide, entry: dict) -> None:
    body = f"{entry['time']}\n\n{entry['text']}\n\nPRESENTER CUE: {entry['speaker']}. {entry['cue']}\n\nSOURCES: {entry['sources']}"
    slide.notes_slide.notes_text_frame.text = body


def backup_notes(slide, entry: dict) -> None:
    """Backups are for questions: the note says when to show the slide, what to say, and where the numbers live."""
    slide.notes_slide.notes_text_frame.text = (
        f"Backup\n\nSHOW THIS WHEN: {entry['when']}\n\n{entry['text']}\n\nSOURCES: {entry['sources']}")


def qr_png(url: str, path: Path) -> Path:
    import segno

    segno.make(url, error="m").save(str(path), scale=12, border=2, dark="#091624", light="#F6F3EB")
    return path
