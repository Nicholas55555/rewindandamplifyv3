"""Explore run-to-run variability of the synthetic spatial importance sampler.

This is a descriptive diagnostic, not a coverage or calibration study. Seeds
are spaced by two so each run's direct and proposal random streams use distinct
seeds. It does not change the main demonstration or its saved results.
"""
from __future__ import annotations

import argparse
import statistics

from spatial_model import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=60)
    parser.add_argument('--shots', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=1000)
    args = parser.parse_args()
    if args.runs < 2:
        parser.error('--runs must be at least 2')

    results = [run(shots=args.shots, seed=args.seed + 2*i) for i in range(args.runs)]
    print(f'{args.runs} runs, {args.shots} maps/method/run, seeds {args.seed}+2i')
    for name in ('direct', 'importance'):
        estimates = [item[name]['failure_rate_estimate'] for item in results]
        errors = [item[name]['standard_error'] for item in results
                  if item[name]['standard_error'] is not None]
        mean_error = f'{statistics.mean(errors):.8f}' if errors else 'unavailable'
        print(f'{name}: mean estimate {statistics.mean(estimates):.8f}, '
              f'run-to-run SD {statistics.stdev(estimates):.8f}, '
              f'mean estimated SE {mean_error} ({len(errors)}/{args.runs} available), '
              f'range {min(estimates):.8f} to {max(estimates):.8f}')
    ess = [item['importance']['failure_weight_effective_sample_size'] for item in results]
    print(f'event-weight ESS: median {statistics.median(ess):.1f}, '
          f'range {min(ess):.1f} to {max(ess):.1f}')
    print('Descriptive synthetic runs only; not a confidence-interval coverage study.')


if __name__ == '__main__':
    main()
