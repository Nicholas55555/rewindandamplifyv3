"""Create a bounded, illustrative quantum-dot/HOM benchmark in a new JSON file."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np

from model import (Emitter, hom_observables, hom_overlap, quadrature_overlap,
                   simulate_trap_pairs, stationary_trap_joint, trap_pair_overlap)

HERE = Path(__file__).resolve().parent


def build_results(pairs=100_000, master_seed=20261111):
    lifetime = 1e-9
    gamma = 1 / lifetime
    efficiency = 0.2
    benchmark_cases = []
    for label, pure_rate, shift in [
            ('ideal', 0, 0), ('pure_dephasing', .5 * gamma, 0),
            ('differential_detuning', 0, gamma / np.pi),
            ('combined_dephasing_and_detuning', .5 * gamma, gamma / np.pi)]:
        first, second = Emitter(lifetime, pure_rate), Emitter(lifetime, pure_rate, shift)
        benchmark_cases.append({'case': label, 'first': asdict(first), 'second': asdict(second),
                                'differential_detuning_hz': shift,
                                'differential_angular_detuning_per_s': 2 * np.pi * shift,
                                **hom_observables(hom_overlap(first, second), efficiency)})
    dephasing = []
    for fraction in [0, .05, .1, .25, .5, 1, 2]:
        emitter = Emitter(lifetime, fraction * gamma)
        dephasing.append({'pure_dephasing_over_radiative_rate': fraction,
                          'pure_dephasing_per_s': fraction * gamma,
                          'coherence_time_s': emitter.coherence_time_s,
                          **hom_observables(hom_overlap(emitter, emitter), efficiency)})
    detuning = []
    base = Emitter(lifetime)
    for shift in [0, .025e9, .05e9, .1e9, .25e9, .5e9, 1e9]:
        other = Emitter(lifetime, base.pure_dephasing_per_s, shift)
        detuning.append({'differential_detuning_hz': shift,
                         'differential_angular_detuning_per_s': 2 * np.pi * shift,
                         **hom_observables(hom_overlap(base, other), efficiency)})
    loss = [{**hom_observables(.5, eta),
             'pure_dephasing_per_s': .5 * gamma,
             'expected_excitation_pairs_per_surviving_pair': 1 / eta ** 2 if eta else None}
            for eta in [0, .1, .2, .5, .8, 1]]
    trap_offset = gamma / (2 * np.pi)
    trap_rows = []
    seed_sequences = np.random.SeedSequence(master_seed).spawn(4)
    for p, stream in zip([0, .02, .1, .5], seed_sequences):
        seed = int(stream.generate_state(1, dtype=np.uint64)[0])
        overlap = trap_pair_overlap(base, trap_offset, p)
        trap_rows.append({'switch_probability_between_endpoints': p,
                          'label': 'Fresh independent offsets' if p == .5 else 'Correlated quasi-static offsets',
                          'trap_offset_hz': trap_offset,
                          'joint_endpoint_probabilities': stationary_trap_joint(p).tolist(),
                          'each_single_photon_marginal_offset_probabilities': [.5, .5],
                          **hom_observables(overlap, efficiency),
                          'sampling_check': simulate_trap_pairs(base, trap_offset, p, efficiency, pairs, seed)})
    quadrature = []
    pairs_to_check = [
        ('transform_limited', Emitter(lifetime), Emitter(lifetime)),
        ('markov_dephasing', Emitter(lifetime, .5 * gamma), Emitter(lifetime, .5 * gamma)),
        ('differential_detuning', base, Emitter(lifetime, .1 * gamma, .5e9)),
        ('common_frequency_shift', Emitter(lifetime, .1 * gamma, .5e9), Emitter(lifetime, .1 * gamma, .5e9)),
        ('unequal_lifetimes_crosscheck', base, Emitter(1.4 * lifetime, .3 * gamma, .25e9)),
    ]
    for label, first, second in pairs_to_check:
        coarse = quadrature_overlap(first, second, order=96)
        fine = quadrature_overlap(first, second, order=192)
        exact = hom_overlap(first, second)
        quadrature.append({'case': label, 'first': asdict(first), 'second': asdict(second),
                           'analytic_overlap': exact, 'quadrature96': coarse, 'quadrature192': fine,
                           'absolute_analytic_discrepancy': abs(exact - fine['overlap']),
                           'observed_order_refinement_difference': abs(coarse['overlap'] - fine['overlap']),
                           'check_passed': abs(exact - fine['overlap']) < fine['absolute_truncation_bound'] + 1e-10})
    if not all(row['check_passed'] for row in quadrature):
        raise AssertionError('Independent temporal-kernel quadrature failed')
    source_files = ['model.py', 'run_study.py', 'test_model.py', 'requirements.txt']
    documentation = ['PROTOCOL.md'] if (HERE / 'PROTOCOL.md').exists() else []
    hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
              for name in sorted(source_files + documentation)}
    return {
        'schema_version': 1,
        'study': 'Illustrative quantum-dot single-photon coherence bridge',
        'status': 'Classical calculation of known quantum-optics formulas; synthetic sampling only.',
        'config': {'lifetime_s': lifetime, 'radiative_rate_per_s': gamma,
                   'detuning_and_trap_pure_dephasing_per_s': base.pure_dephasing_per_s,
                   'fixed_efficiency_except_loss_sweep': efficiency,
                   'sampled_independent_pairs_per_trap_setting': pairs, 'master_seed': master_seed},
        'definitions': {
            'frequency': 'Offsets in Hz; delta_angular = 2*pi*(nu_a-nu_b) in rad/s.',
            'coherence': '1/T2 = Gamma/2 + gamma_pure; Gamma = 1/T1.',
            'equal_emitter_overlap': 'Gamma*(Gamma+2*gamma_pure)/((Gamma+2*gamma_pure)^2+delta_angular^2)',
            'brightness': 'Exactly one emitted photon/excitation and g2(0)=0 are imposed assumptions, not estimated outcomes.',
            'efficiency': 'Independent per-photon survival to an otherwise ideal balanced-beamsplitter apparatus.',
            'coincidence': 'Conditional on both surviving: (1-M)/2. Per excitation pair: eta^2*(1-M)/2.',
            'trap': 'Classical ±offset endpoints with uniform marginals and explicitly specified probability of different endpoints; not a fitted switching rate.',
        },
        'assumptions': [
            'Parameters are illustrative, not calibrated to the retained GaAs dataset or any fabricated device.',
            'Ideal unit excitation is independent of photon frequency. Real narrowband resonant excitation can change brightness under detuning.',
            'No nonradiative decay, multiphoton/re-excitation, dark counts, timing jitter, phonon sidebands or polarization mismatch.',
            'Independent Markov fast dephasing baths; a quasi-static trap endpoint remains fixed throughout each photon wavepacket.',
            'The two photon wavepackets are temporally aligned at the balanced beamsplitter; the input emission separation is compensated.',
            'Independent sampled pairs are not overlapping adjacent pairs drawn from one continuous trap trajectory.',
        ],
        'limitations': [
            'HOM degradation alone does not identify a unique defect, trap, laser fluctuation or physical noise cause.',
            'Common-mode shifts cancel from this pair overlap. Counts/HOM require independent references and controls to attribute laser versus dot frequency changes.',
            'Loss reduces acquisition yield; unchanged conditional overlap does not imply unchanged measurement cost.',
            'Correlated pair states cannot generally be replaced by a product of their single-photon marginals.',
            'No quantum-computing advantage, device diagnosis, defect fit, lithography-yield or industrial-performance claim.',
        ],
        'dephasing_sweep': dephasing,
        'benchmark_cases': benchmark_cases,
        'differential_detuning_sweep': detuning,
        'collection_loss_sweep': loss,
        'classical_trap_pair_comparison': trap_rows,
        'independent_quadrature_validation': quadrature,
        'provenance': {'source_sha256': hashes, 'python': platform.python_version(),
                       'numpy': np.__version__,
                       'sampling_rng': 'NumPy default_rng(PCG64), SeedSequence parent/child streams',
                       'all_quadrature_checks_passed': True},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'results.json')
    parser.add_argument('--pairs', type=int, default=100_000)
    parser.add_argument('--seed', type=int, default=20261111)
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace an existing output file')
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        parser.error('Output already exists; choose a new path or explicitly request --overwrite')
    if not 1 <= args.pairs <= 1_000_000:
        parser.error('--pairs must be between 1 and 1000000 to bound memory/time')
    started = time.monotonic()
    results = build_results(args.pairs, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), 'seconds': round(time.monotonic() - started, 3),
                      'quadrature_checks': len(results['independent_quadrature_validation']),
                      'sampled_pairs': 4 * args.pairs, 'status': 'passed'}))


if __name__ == '__main__':
    main()
