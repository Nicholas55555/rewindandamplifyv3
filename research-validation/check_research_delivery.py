"""Extract a verified research ZIP and run its focused tests in fresh processes.

Leaves the temporary extraction available for inspection. Does not rerun the
large statistical studies, deserialize large QPYs, or submit hardware jobs.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from verify_research_pack import verify

SUITES = (
    ('finals-lithography/followup', 'test_*.py'),
    ('finals-lithography/full_spatial_circuit', 'test_full_spatial.py'),
    ('quantum_lithography_poc/exposure_followup', 'test_model.py'),
    ('quantum_lithography_poc/phase_inspection_followup', 'test_phase_model.py'),
    ('laser_sensor_viability/followup', 'test_followup.py'),
    ('qrsm_photon_poc/followup', 'test_*.py'),
    ('qrsm_photon_poc/multibin_followup', 'test_model.py'),
    ('qrsm_photon_poc/drive_diagnostics_followup', 'test_model.py'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', nargs='?', type=Path,
                        default=ROOT/'Rewind_Amplify_Research_Followups.zip')
    args = parser.parse_args()
    archive = args.archive.resolve()
    integrity = verify(archive)
    extraction = Path(tempfile.mkdtemp(prefix='rewind_research_verify_')).resolve()
    # verify() has already rejected traversal, case collisions and symlinks.
    with zipfile.ZipFile(archive) as package:
        package.extractall(extraction)
    extracted_integrity = verify(extraction)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')

    def run_suite(suite):
        directory, pattern = suite
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', directory,
                   '-p', pattern, '-v']
        result = subprocess.run(command, cwd=extraction, env=env,
                                capture_output=True, text=True, encoding='utf-8',
                                timeout=120)
        log = result.stdout + result.stderr
        counts = re.findall(r'Ran (\d+) tests?', log)
        count = int(counts[-1]) if counts else 0
        passed = result.returncode == 0 and count > 0 and '\nOK' in log
        print(json.dumps({'suite': directory, 'passed': passed, 'tests': count}), flush=True)
        return {'suite': directory, 'pattern': pattern, 'returncode': result.returncode,
                'passed': passed, 'tests': count, 'output': log}

    suites = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_suite, suite) for suite in SUITES]
        for future in as_completed(futures):
            suites.append(future.result())
    # Unit tests are not allowed to silently rewrite frozen numerical evidence.
    final_integrity = verify(extraction)
    report = {
        'schema': 'research-delivery-check-v1',
        'executed_utc': datetime.now(timezone.utc).isoformat(),
        'archive': archive.name,
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'extraction_directory': str(extraction),
        'zip_integrity': integrity, 'extracted_integrity': extracted_integrity,
        'integrity_after_tests': final_integrity,
        'all_checks_passed': all(s['passed'] for s in suites),
        'focused_tests_passed': sum(s['tests'] for s in suites if s['passed']),
        'suites': sorted(suites, key=lambda s: s['suite']),
        'scope': 'Portable extraction/import, focused mathematical tests and post-test integrity. Previously saved independent study receipts cover full-result validation.',
    }
    (ROOT/'research-validation/research_delivery_validation.json').write_text(
        json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if not report['all_checks_passed']:
        raise RuntimeError('At least one extracted test suite failed; inspect delivery receipt')
    print(json.dumps({'all_checks_passed': True, 'tests': report['focused_tests_passed'],
                      'extracted_to': str(extraction)}))


if __name__ == '__main__':
    main()
