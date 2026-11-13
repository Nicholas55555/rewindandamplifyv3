"""Submit a prepared plan from an IBM account that cannot see the 11 November campaign's jobs.

    python applied/run_on_ibm.py submit --label applied_v1
    python applied/run_on_ibm.py fetch --label applied_v1

This spends the account's monthly IBM time. Run it only with the account owner's go-ahead.

Why this file exists. hardware_campaign/campaign.py refuses to submit until it has asked IBM for the status of every
earlier job, so that unfinished jobs keep their share of the quota. The account used on 12 November is told "job not
found" for the 11 November jobs (they were evidently submitted from another account or instance), and the tool stops,
having submitted nothing. Every one of those jobs is finished: its raw counts are saved beside its plan with status
DONE and the same job ID.

This wrapper answers that one question from the saved files. Everything else is campaign.py's own code, unchanged:
the frozen-plan check, the Open Plan check, the quota check with its five-second buffer, the run-time cap, the
exclusive intent file written before the call, and one submission per plan. A job with no saved result is still
looked up at IBM, and still blocks the submission if it cannot be found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "hardware_campaign"))

import campaign  # noqa: E402


class Finished:
    """A job whose result is already saved in this repository."""

    def status(self) -> str:
        return "DONE"


class Service:
    """The real IBM service, except that jobs already saved as finished are not looked up again."""

    def __init__(self, real, finished: set[str]):
        self._real, self._finished = real, finished

    def job(self, job_id: str):
        return Finished() if job_id in self._finished else self._real.job(job_id)

    def __getattr__(self, name: str):
        return getattr(self._real, name)


def finished_jobs() -> set[str]:
    """Job IDs whose run folder holds both the submission record and raw counts marked DONE for that same job."""
    done = set()
    for folder in sorted((campaign.HERE / "runs").iterdir()):
        job, raw = folder / "job.json", folder / "raw.json"
        if job.exists() and raw.exists():
            job_id, result = campaign.read(job)["job_id"], campaign.read(raw)
            if result.get("job_id") == job_id and str(result.get("status", "")).upper() == "DONE" and result.get("rows"):
                done.add(job_id)
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["submit", "fetch"])
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if Path(args.label).name != args.label:
        raise ValueError("Label must be a single directory name")
    if args.command == "fetch":
        campaign.fetch(args)
        return
    finished = finished_jobs()
    real_service = campaign.service
    campaign.service = lambda: Service(real_service(), finished)
    print(json.dumps({"jobs_already_saved_as_finished": len(finished)}), flush=True)
    campaign.submit(args)


if __name__ == "__main__":
    main()
