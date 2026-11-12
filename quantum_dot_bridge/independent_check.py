"""Independently integrate saved photon kernels using adaptive SciPy quadrature.

No import of model.py or its Gauss-Legendre implementation. This checks a known
model's numerical implementation, not the physics of an experimental device.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import scipy
from scipy.integrate import dblquad

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'independent_review.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output; existing review receipts are not overwritten')
    source = HERE/'results.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    rows = []
    for case in data['independent_quadrature_validation']:
        first, second = case['first'], case['second']
        ga, gb = 1/first['lifetime_s'], 1/second['lifetime_s']
        # x=Gamma_a*t, y=Gamma_a*u. Integrate both triangular halves,
        # exploiting conjugate symmetry, directly from the density kernels.
        ratio = gb/ga
        decay = (ga+gb)/(2*ga)
        phase_decay = (first['pure_dephasing_per_s']+second['pure_dephasing_per_s'])/ga
        frequency = 2*math.pi*(first['frequency_offset_hz']-second['frequency_offset_hz'])/ga
        endpoint = 40*ga*max(first['lifetime_s'], second['lifetime_s'])

        def integrand(y, x):
            return 2*ratio*math.exp(-decay*(x+y)-phase_decay*(x-y))*math.cos(frequency*(x-y))

        value, error_estimate = dblquad(integrand, 0, endpoint, lambda x: 0,
                                        lambda x: x, epsabs=2e-11, epsrel=2e-11)
        difference = abs(value-case['analytic_overlap'])
        row = {'case': case['case'], 'adaptive_integral': value,
               'scipy_error_estimate': error_estimate,
               'absolute_difference_from_saved_analytic_value': difference,
               'finite_window_in_first_lifetimes': endpoint,
               'passed': difference < 1e-9}
        rows.append(row)
    if not all(row['passed'] for row in rows):
        raise RuntimeError('Independent adaptive integration failed')
    receipt = {'all_checks_passed': True, 'method': 'Independent dimensionless two-dimensional adaptive integration; no model import',
               'scope': 'Implementation agreement for five declared synthetic cases; adaptive error estimates are not certified device-model bounds.',
               'scipy': scipy.__version__, 'cases': rows,
               'results_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'check_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
