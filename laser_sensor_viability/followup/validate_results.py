"""Independent recounting, provenance checks and bounded cluster uncertainty."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import platform
import numpy as np
import matplotlib


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(path):
    result = json.loads((path/"results.json").read_text(encoding="utf-8"))
    p = result["protocol"]
    shape = (p["outer_calibrations"], p["test_sessions"], p["test_records_per_class_per_session"])
    n = int(np.prod(shape))
    base = Path(__file__).resolve().parent.parent
    checks = []
    for rel, expected in result["source_sha256"].items():
        actual = sha(base/rel)
        if actual != expected: raise AssertionError(f"Source changed:{rel}")
        checks.append({"check": "source_hash", "path": rel, "passed": True})
    if sha(path/"record_outcomes.npz") != result["record_outcomes_sha256"]:
        raise AssertionError("Outcome archive hash differs")
    boundary = []
    radius = math.sqrt(math.log(2/.05)/(2*shape[0]))
    with np.load(path/"record_outcomes.npz") as archive:
        for scenario in result["scenarios"]:
            for method, summary in scenario["methods"].items():
                def arr(field): return archive[f"{scenario['id']}__{method}__{field}"].reshape(shape)
                null, event, onset = arr("null_alarm"), arr("event_alarm"), arr("onset")
                if not np.all((onset >= 48) & (onset <= 96)): raise AssertionError("Onset domain")
                for x in (null, event):
                    if not np.all((x == -1) | ((x >= 32) & (x <= 128))): raise AssertionError("Alarm time domain")
                pre = (event >= 0) & (event <= onset)
                detected = (event > onset) & (event-onset <= 32)
                restricted = np.full(shape, 32.)
                for ri in range(shape[0]):
                    for si in range(shape[1]):
                        for j in range(shape[2]):
                            a, t = int(event[ri, si, j]), int(onset[ri, si, j])
                            if a > t: restricted[ri, si, j] = min(a-t, 32)
                truth = {"false_alarm_rate": null >= 0, "pre_onset_alarm": pre,
                         "detection_within_32s": detected, "restricted_delay_s": restricted,
                         "eventual_detection": event > onset, "no_alarm": event < 0}
                for metric, values in truth.items():
                    np.testing.assert_allclose(float(values.mean()), summary[metric], atol=1e-14, rtol=0)
                    if metric != "restricted_delay_s":
                        if int(values.sum()) != summary["counts"][metric]: raise AssertionError("Count mismatch")
                        if summary[metric+"_ci95"][0] == summary[metric+"_ci95"][1]:
                            mean = float(values.mean())
                            boundary.append({"scenario": scenario["id"], "method": method, "metric": metric,
                                "observed": mean, "independent_pipeline_count": shape[0],
                                "hoeffding_ci95": [max(0., mean-radius), min(1., mean+radius)],
                                "note": "Conservative distribution-free bounded-mean interval using independent pipeline averages; bootstrap degeneracy is not zero uncertainty."})
                if n != scenario["records_per_class"]: raise AssertionError("Denominator mismatch")
                checks.append({"check": "independent_outcome_recount", "scenario": scenario["id"], "method": method, "passed": True})
    report = {"all_checks_passed": True, "checks": checks, "records_per_class_per_scenario": n,
              "bootstrap_boundary_supplement": boundary,
              "hoeffding_scope": "Independent calibration-pipeline means are bounded[0,1]; P(|samplemean-populationmean|>r)<=2exp(-2*R*r^2). Assumes independent identical simulated pipeline populations; does not validate physical model.",
              "runtime": {"python": platform.python_version(), "numpy": np.__version__, "matplotlib": matplotlib.__version__},
              "result_sha256": sha(path/"results.json"), "outcomes_sha256": sha(path/"record_outcomes.npz"),
              "validator_sha256": sha(__file__)}
    dest = path.parent/"validation.json" if path.name == "main" else path/"validation.json"
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"all_checks_passed": True, "checks": len(checks), "boundary_intervals": len(boundary), "output": str(dest)}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True, type=Path)
    validate(p.parse_args().run)
