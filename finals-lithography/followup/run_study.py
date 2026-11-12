"""Run the isolated correlated-patch study; only local simulation is used."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import math
import multiprocessing as mp
import platform
from pathlib import Path
import time
import numpy as np
import scipy
import qiskit
import qiskit_aer
from model import (DEFAULT, joint_probabilities, summarize, dp_solution,
                   independent_control, conditional_draws, encode, classical_experiment)
from quantum import preparation, counter_oracle, enumerated_oracle, cost, ideal_case, noise_case


def worker(rounds, p2, readout, queue):
    try: queue.put(noise_case(rounds, p2, readout))
    except Exception as exc: queue.put({'status': 'failed', 'rounds': rounds, 'p2': p2,
                                      'error': f'{type(exc).__name__}: {exc}'})


def bounded_noise(rounds, p2, readout, timeout=90):
    ctx = mp.get_context('spawn')
    queue = ctx.Queue()
    process = ctx.Process(target=worker, args=(rounds, p2, readout, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        row = {'status': 'timeout', 'rounds': rounds, 'p2': p2, 'readout': readout,
               'timeout_seconds': timeout}
    elif process.exitcode:
        row = {'status': 'failed', 'rounds': rounds, 'p2': p2, 'exit_code': process.exitcode}
    else:
        row = queue.get(timeout=3)
    queue.close()
    return row


def run(output, timeout):
    start = time.monotonic()
    p, posterior, tables = dp_solution()
    independent = independent_control()
    truth = summarize(joint_probabilities())
    z, counts = conditional_draws(20000, np.random.default_rng(99102))
    sampled = np.bincount([encode(a, b) for a, b in zip(z, counts)], minlength=512)/len(z)
    conditional_summary = summarize(sampled)
    theta = math.asin(math.sqrt(p))
    peak_round = round(math.pi/(4*theta)-.5)
    result = {
        'schema_version': 1,
        'scope': 'Uncalibrated 2x2 spatial correlated-Poisson model. Local Qiskit simulation only, not a wafer or QPU experiment.',
        'config': asdict(DEFAULT),
        'response': {'weights_normalized': [1/9, 2/9, 2/9, 4/9],
                     'gaussian_sigma_cells': 1/math.sqrt(2*math.log(2)),
                     'threshold_normalized': 1/3,
                     'boundary': 'only these four cells contribute; kernel normalized over this patch'},
        'capping': {'map': 'min(Poisson count,3)',
                    'preserves': 'score<3 and each accepted original count map, exactly; latent posterior given event',
                    'does_not_preserve': 'unconditional count distribution above 2, means/variance, or general other observables'},
        'exact_classical': {'event_probability': p, 'conditional_low_dose_probability': float(posterior[0]),
                            'independent_same_marginals_event_probability': independent,
                            'shared_to_independent_probability_ratio': p/independent,
                            'unbounded_cell_mean': float(np.dot(DEFAULT.prior, DEFAULT.rates)),
                            'unbounded_cross_cell_covariance': float(np.dot(DEFAULT.prior, np.square(DEFAULT.rates))-np.dot(DEFAULT.prior, DEFAULT.rates)**2),
                            'conditional_distribution': truth,
                            'dp_messages': [x.tolist() for x in tables],
                            'conditional_sampler_20000_draw_validation': conditional_summary,
                            'conditional_sampler_seed': 99102,
                            'algorithm': 'backward weighted-sum messages; posterior dose draw then four sequential conditional count draws; no rejection'},
        'classical_monte_carlo': classical_experiment(),
        'quantum_components': {name: cost(qc) for name, qc in
                               [('preparation', preparation()), ('weighted_sum_oracle', counter_oracle()),
                                ('enumerated_oracle', enumerated_oracle())]},
        'ideal_cases': [], 'noise_cases': [],
        'ideal_formula_only': {'first_near_peak_round': peak_round,
                               'probability_at_that_round': math.sin((2*peak_round+1)*theta)**2,
                               'scope': 'formula, not an executed or compiled circuit at this round count'},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'qiskit': qiskit.__version__, 'qiskit_aer': qiskit_aer.__version__},
        'compilation': {'basis': ['u', 'cx'], 'optimization_level': 1, 'seed': 13,
                        'connectivity': 'generic all-to-all; no routing or hardware calibration'},
        'noise_scope': 'Exact density matrix of full 9-data-qubit enumerated circuits. Hypothetical depolarization and independent readout; no idle, drift, crosstalk, fault tolerance, or hardware validation.',
        'noise_timeout_per_case_seconds': timeout,
    }
    def save():
        output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    save()
    for style in ('counter', 'enumerated'):
        for rounds in (0, 1, 2):
            print(f'Ideal {style} rounds={rounds}', flush=True)
            row = ideal_case(rounds, style)
            expected = math.sin((2*rounds+1)*theta)**2
            if abs(row['ideal']['hit_probability']-expected) > 1e-10:
                raise RuntimeError('amplification disagrees with formula')
            row['amplification_formula'] = expected
            result['ideal_cases'].append(row)
            save()
    for p2, readout in ((0., 0.), (.0001, .001), (.001, .01)):
        for rounds in (0, 1, 2):
            print(f'Noise p2={p2} readout={readout} rounds={rounds}', flush=True)
            row = bounded_noise(rounds, p2, readout, timeout)
            result['noise_cases'].append(row)
            save()
            print(row['status'], flush=True)
    result['source_sha256'] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                               for name in ('model.py', 'quantum.py', 'run_study.py')}
    result['elapsed_seconds'] = time.monotonic()-start
    save()
    print(json.dumps({'exact_p': p, 'independent_p': independent,
                      'low_dose_posterior': posterior.tolist(),
                      'all_noise_cases_completed': all(x['status']=='completed' for x in result['noise_cases'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('results.json'))
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    if args.output.exists(): parser.error('output exists; choose a new path')
    run(args.output, args.timeout)
