"""Recompute every deterministic result and check saved source/raw hashes."""
import json
from pathlib import Path

from analysis import sha256
from run_analysis import run

HERE = Path(__file__).resolve().parent


def main():
    saved = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    for name, digest in saved["source_sha256"].items():
        if sha256(HERE / name) != digest:
            raise AssertionError(f"Source changed: {name}")
    for name, digest in saved["raw_sha256"].items():
        if sha256(HERE.parent / "reference_hom" / name) != digest:
            raise AssertionError(f"Raw file changed: {name}")
    plot = json.loads((HERE / "plot_manifest.json").read_text(encoding="utf-8"))
    assert sha256(HERE / "results.json") == plot["results_sha256"]
    assert sha256(HERE / "plot_analysis.py") == plot["plot_source_sha256"]
    for name, digest in plot["artifacts"].items():
        assert sha256(HERE / name) == digest, f"Plot changed: {name}"
    independent = json.loads((HERE / "independent_primary.json").read_text(encoding="utf-8"))
    for name, field in [("independent_check.py", "source_sha256"),
                        ("results.json", "results_sha256"), ("PROTOCOL.md", "protocol_sha256")]:
        assert sha256(HERE / name) == independent[field], f"Independent receipt stale: {name}"
    for acquisition in independent["acquisitions"]:
        assert sha256(HERE.parent / "reference_hom" / acquisition["file"]) == acquisition["raw_sha256"]
    validation = json.loads((HERE / "validation.json").read_text(encoding="utf-8"))
    assert "validation.json" not in validation["artifact_sha256"], "Validation must not hash itself"
    for name, digest in validation["artifact_sha256"].items():
        assert sha256(HERE / name) == digest, f"Validation artifact changed: {name}"
    fresh = run(saved["monte_carlo"]["samples"])
    # Environment versions identify the original calculation, not a metric.
    for key in ("created_utc", "runtime_seconds", "environment"):
        saved.pop(key)
        fresh.pop(key)

    def compare(a, b, path=""):
        if isinstance(a, dict):
            assert a.keys() == b.keys(), path
            for key in a:
                compare(a[key], b[key], f"{path}/{key}")
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)):
                compare(x, y, f"{path}/{i}")
        elif isinstance(a, float):
            # Roundoff tolerance across compatible numerical libraries;
            # seeded Monte Carlo arrays otherwise require matching RNG semantics.
            assert abs(a-b) <= 1e-11 * max(1, abs(a)), (path, a, b)
        else:
            assert a == b, (path, a, b)
    compare(saved, fresh)
    print("Verified source/raw/plot/independent-receipt/validation hashes and every deterministic estimator/MC/sensitivity field.")


if __name__ == "__main__":
    main()
