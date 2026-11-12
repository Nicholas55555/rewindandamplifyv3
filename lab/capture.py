"""Record the Lab: stills of every scene, and the 45-second tour as an MP4.

The page is stepped frame by frame through its own `LAB.tick` hook with a fixed random seed, so the recording is
a real screen capture of the running Lab and comes out the same every time. Nothing is composited afterwards
except an optional music track.

    python lab/capture.py stills                      # media/lab-1-signal.png ... media/lab-7-impact.png
    python lab/capture.py tour                        # media/lab-tour.mp4 (silent)
    python lab/capture.py tour --music score.wav      # the same, with a soundtrack

Needs an installed Chrome or Edge, plus two helper packages that the science code does not use:

    pip install playwright imageio-ffmpeg
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MEDIA = ROOT / "media"
PAGE = (HERE / "index.html").as_uri()
SEED = 20261114
# scene, query string, and how long to let it run before the still is taken (milliseconds of Lab time)
STILLS = [
    ("1-signal", "reveal=1&speed=1&runs=400", "signal", 4580),
    ("2-machine", "reveal=1&speed=1", "machine", 2970),
    ("3-question", "speed=4&runs=2400", "question", 2600),
    ("4-rewind", "stage=4", "rewind", 300),
    ("5-answer", "", "answer", 300),
    ("6-hardware", "", "hardware", 1600),
    ("7-impact", "", "impact", 300),
]


def browser(playwright):
    last = None
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except Exception as error:  # the channel is not installed: try the next one
            last = error
    raise SystemExit(f"No installed Chrome or Edge could be started: {last}")


def open_page(context, query: str, scene: str):
    page = context.new_page()
    page.goto(f"{PAGE}?capture=1&seed={SEED}&{query}#{scene}")
    page.wait_for_function("window.LAB !== undefined")
    page.evaluate("LAB.manual()")
    return page


def run(page, milliseconds: float, step: float = 1000 / 30) -> None:
    page.evaluate("([ms, step]) => { for (let t = 0; t < ms; t += step) LAB.tick(step); }", [milliseconds, step])


def stills(args) -> None:
    from playwright.sync_api import sync_playwright

    MEDIA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = browser(p)
        context = b.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=args.scale)
        for name, query, scene, settle in STILLS:
            if args.only and args.only not in name:
                continue
            for level in (["plain", "tech"] if args.both_levels else ["plain"]):
                page = open_page(context, f"{query}&level={level}", scene)
                run(page, settle)
                suffix = "" if level == "plain" else "-technical"
                out = MEDIA / f"lab-{name}{suffix}.png"
                page.screenshot(path=str(out))
                page.close()
                print(f"wrote {out.relative_to(ROOT)}")
        b.close()


def tour(args) -> None:
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright

    MEDIA.mkdir(exist_ok=True)
    out = MEDIA / args.output
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(args.fps), "-c:v", "png", "-i", "-"]
    if args.music:
        command += ["-i", str(args.music)]
    command += ["-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", "-r", str(args.fps)]
    if args.music:
        command += ["-c:a", "aac", "-b:a", "192k", "-af", "afade=t=in:d=0.6,afade=t=out:st={:.2f}:d=1.6".format(0),
                    "-shortest"]
    else:
        command += ["-an"]
    with sync_playwright() as p:
        b = browser(p)
        context = b.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=1)
        page = open_page(context, "tour=1", "signal")
        length = page.evaluate("LAB.tourLength()")
        frames = int(round((length + args.tail) * args.fps))
        if args.music:  # fade the music out with the picture
            i = command.index("-af") + 1
            command[i] = f"afade=t=in:d=0.6,afade=t=out:st={length + args.tail - 1.8:.2f}:d=1.8"
        encoder = subprocess.Popen(command + [str(out)], stdin=subprocess.PIPE)
        step = 1000 / args.fps
        for i in range(frames):
            page.evaluate("ms => LAB.tick(ms)", step)
            encoder.stdin.write(page.screenshot(type="png"))
            if i % (args.fps * 5) == 0:
                print(f"  {i / args.fps:5.1f} s of {frames / args.fps:.1f} s", flush=True)
        encoder.stdin.close()
        if encoder.wait():
            raise SystemExit("ffmpeg failed")
        b.close()
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size / 1e6:.1f} MB, {frames} frames at {args.fps} fps)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("stills", help="one PNG per scene")
    s.add_argument("--width", type=int, default=1600)
    s.add_argument("--height", type=int, default=900)
    s.add_argument("--scale", type=float, default=1.5, help="device pixel ratio: 1.5 gives 2400 x 1350 images")
    s.add_argument("--only", help="capture only scenes whose name contains this text")
    s.add_argument("--both-levels", action="store_true", help="also save the technical-caption version of each scene")
    s.set_defaults(run=stills)
    t = sub.add_parser("tour", help="the 45-second tour as an MP4")
    t.add_argument("--width", type=int, default=1920)
    t.add_argument("--height", type=int, default=1080)
    t.add_argument("--fps", type=int, default=30)
    t.add_argument("--crf", type=int, default=18, help="x264 quality: lower is better and larger")
    t.add_argument("--tail", type=float, default=1.0, help="seconds to hold the last frame")
    t.add_argument("--music", type=Path, help="an audio file to lay under the picture")
    t.add_argument("--output", default="lab-tour.mp4")
    t.set_defaults(run=tour)
    args = parser.parse_args()
    try:
        args.run(args)
    except ModuleNotFoundError as error:
        sys.exit(f"{error}. Install the capture helpers: pip install playwright imageio-ffmpeg")


if __name__ == "__main__":
    main()
