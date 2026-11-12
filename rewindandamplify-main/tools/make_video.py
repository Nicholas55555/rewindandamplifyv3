"""A narrated draft of the presentation video: the slides, with the speaker notes read by a computer voice.

This is a fallback and a pacing guide. A video in your own voices will land better, since the judges score how the team
communicates. It needs Windows for the speech voice, and the imageio-ffmpeg package for ffmpeg.

    python tools/render_deck.py     first, to make the slide images
    python tools/make_video.py      then this
    python tools/make_video.py --voice "Microsoft David Desktop" --rate 3
"""

import argparse
import json
import re
import subprocess
import tempfile
from html import unescape
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck"
RENDER = DECK / "render"
OUT = DECK / "Rewind_and_Amplify_narrated_draft.mp4"

SPOKEN = [("QRSM", "Q R S M"), ("g-two", "g two"), ("LSTM", "L S T M"), ("Qiskit", "kiss kit"), ("SamplerV2", "sampler version two")]


def notes() -> list:
    order = json.loads((DECK / "project" / "deck.json").read_text(encoding="utf-8"))["order"]
    out = []
    for slide_id in order:
        text = (DECK / "project" / "slides" / f"{slide_id}.html").read_text(encoding="utf-8")
        m = re.search(r"<aside>(.*?)</aside>", text, re.S)
        out.append(unescape(m.group(1).strip()) if m else "")
    return out


def speak(text: str, wav: Path, voice: str, rate: int) -> None:
    for old, new in SPOKEN:
        text = text.replace(old, new)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        txt = f.name
    script = (f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SelectVoice('{voice}'); $s.Rate = {rate}; $s.SetOutputToWaveFile('{wav}'); "
              f"$s.Speak([IO.File]::ReadAllText('{txt}')); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    Path(txt).unlink()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--voice", default="Microsoft Zira Desktop")
    ap.add_argument("--rate", type=int, default=6, help="speech rate, -10 to 10")
    args = ap.parse_args()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    work = RENDER / "video"
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, text in enumerate(notes(), 1):
        if not text:  # a backup slide
            continue
        wav = work / f"n{i:02d}.wav"
        speak(text, wav, args.voice, args.rate)
        seg = work / f"s{i:02d}.mp4"
        subprocess.run([ffmpeg, "-y", "-loop", "1", "-framerate", "5", "-i", str(RENDER / f"slide_{i:02d}.png"), "-i", str(wav),
                        "-af", "apad=pad_dur=0.7", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "5",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", str(seg)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        parts.append(seg)
        print(f"  slide {i} done", flush=True)
    listing = work / "list.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(OUT)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    probe = subprocess.run([ffmpeg, "-i", str(OUT)], capture_output=True, text=True).stderr
    length = re.search(r"Duration: (\d+:\d+:\d+)", probe)
    print(f"wrote {OUT.name}: {length.group(1) if length else '?'} long, {OUT.stat().st_size // 2 ** 20} MB", flush=True)


if __name__ == "__main__":
    main()
