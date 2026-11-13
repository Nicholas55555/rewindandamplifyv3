"""Run existing bounded tests in isolated processes, without regenerating studies.

Directories deliberately remain separate: several research modules are named
model.py, so recursive pytest/unittest collection in one process is unsafe.
No credentials, hardware jobs, full-study generators or 389-qubit simulations.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SUITES = (
    'finals-lithography',
    'finals-lithography/followup',
    'finals-lithography/full_spatial_circuit',
    'laser_sensor_poc',
    'laser_sensor_viability',
    'laser_sensor_viability/followup',
    'qrsm_photon_poc',
    'qrsm_photon_poc/diagnostics_baselines',
    'qrsm_photon_poc/followup',
    'qrsm_photon_poc/drive_diagnostics_followup',
    'qrsm_photon_poc/multibin_followup',
    'quantum_lithography_poc',
    'quantum_lithography_poc/exposure_followup',
    'quantum_lithography_poc/phase_inspection_followup',
    'external_data/gaas_qd5',
    'quantum_dot_bridge',
    'quantum_dot_bridge/reference_hom',
    'quantum_dot_bridge/hom_analysis',
    'quantum_dot_bridge/qrsm_hom_followup',
    'quantum_dot_bridge/qrsm_hom_followup/exploratory_design',
    'hardware_campaign',
    'hardware_campaign/feasibility',
    'hardware_campaign/optical_controls',
    'hardware_campaign/extensions',
    'hardware_campaign/noise_model',
    'applied',
    'applied/contact',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['all', 'core', 'research'], default='all')
    parser.add_argument('--list', action='store_true', help='List commands without importing scientific dependencies')
    args = parser.parse_args()
    commands = []
    if args.group in ['all', 'core']:
        commands.append(('original-qrsm', ROOT/'rewindandamplify-main',
                         [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], 'pytest'))
    if args.group in ['all', 'research']:
        for directory in SUITES:
            commands.append((directory, ROOT,
                             [sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', 'test_*.py', '-v'], 'unittest'))
        # This original numerical check exposes main(), not a unittest class.
        commands.append(('photon-cptp-script', ROOT,
                         [sys.executable, 'qrsm_photon_poc/test_model.py'], 'script'))
    if args.list:
        print(json.dumps([{'suite':name,'working_directory':str(cwd.relative_to(ROOT)),
                           'arguments':cmd[1:]} for name,cwd,cmd,_ in commands], indent=2))
        return
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg')
    summaries = []
    for name,cwd,command,kind in commands:
        started=time.monotonic()
        print(f'Checking {name}', flush=True)
        try:
            result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,
                                  text=True,encoding='utf-8',errors='replace',timeout=300)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f'{name}: exceeded the 300-second per-suite limit') from exc
        log=result.stdout+result.stderr
        if kind=='unittest':
            match=re.search(r'Ran (\d+) tests?',log)
            count=int(match.group(1)) if match else 0
            passed=result.returncode==0 and count>0 and '\nOK' in log and 'skipped=' not in log
        elif kind=='pytest':
            match=re.search(r'(\d+) passed',log)
            count=int(match.group(1)) if match else 0
            passed=result.returncode==0 and count>0 and not re.search(r'\d+ skipped',log)
        else:
            count=None
            passed=result.returncode==0 and 'All numerical tests passed' in log
        row={'suite':name,'passed':passed,'tests':count,'seconds':round(time.monotonic()-started,3)}
        print(json.dumps(row),flush=True)
        if not passed:
            print(log,flush=True)
            raise RuntimeError(f'{name}: failed, empty, or unexpectedly skipped tests')
        summaries.append(row)
    print(json.dumps({'all_checks_passed':True,'group':args.group,'processes':len(summaries),
                      'counted_tests':sum(row['tests'] or 0 for row in summaries),
                      'standalone_numerical_scripts':sum(row['tests'] is None for row in summaries),
                      'suites':summaries},indent=2))


if __name__=='__main__':
    main()
