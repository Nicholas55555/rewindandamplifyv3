"""A short clip for the README and the talk: 48 runs of the machine, as the build changes.

Each row is one run; time goes left to right; a tick is a click. The column on the right is the rare click we asked
about. Runs are drawn from the exact distribution of each build, so what you see is what the circuits do.

    python demo/make_clip.py        writes results/figures/raster.gif and raster.mp4
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from qrsm_grover.amplify import steered_gamma
from qrsm_grover.fastsim import FastPurified, light_distribution, reflection_qubits
from qrsm_grover.model import QRSM
from qrsm_grover.predicates import click_at

MODEL = QRSM()
T = 6
ROWS = 48
W, H = 960, 600
LEFT, TOP, PLOT_W, ROW_H = 40, 130, 880, 8.4
BG, ROW_HIT, INK, INK2, CLICK, LINE, OTHER = "#F6F5F0", "#FBE3D7", "#12203A", "#3B4658", "#D9531E", "#DDDAD0", "#475569"
OUT = ROOT / "results" / "figures"


def font(size: int, bold: bool = False):
    for name in (("seguisb.ttf" if bold else "segoeui.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def distribution(gamma_last, reflection, r):
    mask = click_at(T).mask(T)
    fast = FastPurified(MODEL, T, None if gamma_last is None else [None] * (T - 1) + [gamma_last])
    state = dict(fast.amplify(mask, r, reflection_qubits(MODEL, T, reflection)))[r]
    return light_distribution(state, T, fast.dim)


def frame(title: str, detail: str, runs: np.ndarray, hit: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((LEFT, 26), title, fill=INK, font=font(34, True))
    d.text((LEFT, 78), detail, fill=INK2, font=font(21))
    cw = PLOT_W / T
    for i, y in enumerate(runs):
        top = TOP + i * ROW_H
        if (int(y) >> (T - 1)) & 1:
            d.rectangle([LEFT, top, LEFT + PLOT_W, top + ROW_H - 1.4], fill=ROW_HIT)
        for t in range(T):
            if (int(y) >> t) & 1:
                x = LEFT + t * cw + cw / 2
                d.rectangle([x - 5, top + 0.4, x + 5, top + ROW_H - 1.8], fill=CLICK if t == T - 1 else OTHER)
    for t in range(1, T):
        x = LEFT + t * cw
        d.line([x, TOP, x, TOP + ROWS * ROW_H], fill=LINE, width=1)
    d.text((LEFT, H - 44), f"{hit:.0%} of runs have the click at step {T}", fill=INK, font=font(24, True))
    return img


def main() -> None:
    probs = MODEL.history_probabilities(T)
    mask = click_at(T).mask(T)
    p = float(probs[mask].sum())
    steer = steered_gamma(p, MODEL.gamma)
    stages = [("Plain sampling", "Run it and keep what matches", None, "full", 0),
              ("Textbook Grover, 1 iteration", "Rewind everything, reflect about the whole start state", None, "full", 1),
              ("Textbook Grover, 2 iterations", "Exact, and about 380 two-qubit gates", None, "full", 2),
              ("Steer, then 1 iteration", f"Tune the last emission from γ = 0.2 to {steer:.2f}: still exact", steer, "full", 1),
              ("Steer + local reflection", "Watch 3 qubits at any length: about 110 two-qubit gates", steer, "memory+last-1", 1)]
    rng = np.random.default_rng(6)
    frames, durations = [], []
    for title, detail, gamma, reflection, r in stages:
        d = distribution(gamma, reflection, r)
        d = d / d.sum()
        hit = float(d[mask].sum())
        for k in range(3):  # three fresh draws of 48 runs per build
            frames.append(frame(title, detail, rng.choice(d.size, size=ROWS, p=d), hit))
            durations.append(900)
    durations[-1] = 2400
    OUT.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT / "raster.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)

    import imageio_ffmpeg

    tmp = OUT / "_raster"
    tmp.mkdir(exist_ok=True)
    listing = []
    for i, (f, ms) in enumerate(zip(frames, durations)):
        f.save(tmp / f"{i:03d}.png")
        listing.append(f"file '{(tmp / f'{i:03d}.png').as_posix()}'\nduration {ms / 1000}\n")
    (tmp / "list.txt").write_text("".join(listing) + f"file '{(tmp / f'{len(frames) - 1:03d}.png').as_posix()}'\n", encoding="utf-8")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-vf", "fps=10,format=yuv420p",
                    "-c:v", "libx264", str(OUT / "raster.mp4")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print(f"wrote raster.gif ({(OUT / 'raster.gif').stat().st_size // 1024} KB) and raster.mp4", flush=True)


if __name__ == "__main__":
    main()
