"""Shared helpers for the experiments: where results go, and how they are saved."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESULTS = ROOT / "results"
DATA = ROOT / "data"


def _plain(value):
    """Make numpy values JSON-friendly."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def save(experiment: str, data: dict, name: str = "results.json") -> Path:
    folder = RESULTS / experiment
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(_plain(data), indent=1), encoding="utf-8")
    return path


def load(experiment: str, name: str = "results.json") -> dict:
    return json.loads((RESULTS / experiment / name).read_text(encoding="utf-8"))
