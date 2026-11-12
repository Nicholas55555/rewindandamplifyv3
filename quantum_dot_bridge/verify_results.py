"""Read-only provenance and accounting checks for the new saved benchmark."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = HERE/'results.json'
    data = json.loads(results.read_text(encoding='utf-8'))
    expected_sources = {'model.py', 'run_study.py', 'test_model.py', 'requirements.txt', 'PROTOCOL.md'}
    sources = data['provenance']['source_sha256']
    assert set(sources) == expected_sources
    for name, expected in sources.items():
        assert sha(HERE/name) == expected, name
    expected_cases = {'ideal': 1, 'pure_dephasing': .5, 'differential_detuning': .2,
                      'combined_dephasing_and_detuning': .25}
    assert {case['case'] for case in data['benchmark_cases']} == set(expected_cases)
    for case in data['benchmark_cases']:
        overlap, eta = case['conditional_overlap'], case['single_photon_survival_probability']
        assert math.isclose(overlap, expected_cases[case['case']], abs_tol=1e-12)
        assert case['emitted_photons_per_excitation'] == 1 and case['ideal_g2_zero_imposed'] == 0
        assert math.isclose(case['coincidence_probability_per_excitation_pair'], eta**2*(1-overlap)/2, abs_tol=1e-12)
    for row in data['classical_trap_pair_comparison']:
        assert math.isclose(row['conditional_overlap'], 1-.8*row['switch_probability_between_endpoints'], abs_tol=1e-12)
        sample = row['sampling_check']
        assert sample['emitted_photons'] == 2*sample['independent_excitation_pairs']
        assert sample['coincidence_pairs'] <= sample['both_survived_pairs'] <= sample['independent_excitation_pairs']
        residual = sample['sampling_error_in_standard_errors']
        assert residual is None or abs(residual) < 5
    plot = json.loads((HERE/'coherence_bridge.json').read_text())
    assert plot['results_sha256'] == sha(results)
    assert plot['plot_source_sha256'] == sha(HERE/'plot_results.py')
    assert plot['figure_sha256'] == sha(HERE/plot['figure'])
    review = json.loads((HERE/'independent_review.json').read_text())
    assert review['results_sha256'] == sha(results)
    assert review['check_source_sha256'] == sha(HERE/'independent_check.py')
    assert review['all_checks_passed'] and len(review['cases']) == 5
    assert all(row['passed'] and row['absolute_difference_from_saved_analytic_value'] < 1e-9 for row in review['cases'])
    print(json.dumps({'status': 'passed', 'source_hashes': len(sources), 'benchmark_cases': len(expected_cases),
                      'independent_integrals': len(review['cases']), 'figure_hash': 'passed',
                      'scope': 'Saved synthetic benchmark integrity and accounting; not a physical validation.'}))


if __name__ == '__main__':
    main()
