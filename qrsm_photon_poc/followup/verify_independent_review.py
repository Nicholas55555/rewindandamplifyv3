"""Read-only independent recount of frozen inference artifacts; writes only review JSON.

This is an independent arithmetic/provenance review using the frozen likelihood
implementation, not a second physical solver or a refit. No parameters are tuned.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inference_model as m
sys.path.insert(0, str(HERE.parent / 'diagnostics_baselines'))
from compare import hmm_likelihood_and_stats


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / 'inference_results/protocol.json').read_text())
    for name, value in manifest['source_sha256'].items():
        assert digest(HERE / name) == value
    cases = []
    dead = {}
    max_score_error = 0.0
    mappings = {'joint_minus_hmm': ('joint', 'hmm'),
                'joint_minus_telegraph': ('joint', 'rate_matched_telegraph'),
                'known_minus_joint': ('known_nuisance', 'joint'),
                'cutoff5_minus_4': ('joint_dimension5', 'joint')}
    for path in sorted((HERE / 'inference_results').glob('*_dead*_fit*.json')):
        row = json.loads(path.read_text())
        seed = int(row['case'].split('_')[1])
        cfg = row['config']
        controls = row['protocol_controls']
        truth = m.Parameters(**row['generator_parameters'])
        fitted = m.Parameters(**row['joint_parameters'])
        blind = row['detector_dead_bins_fit']
        train = m.sample(truth, controls, cfg['train_records'] // len(controls),
                         cfg['bins'], seed, row['detector_dead_bins_truth'])
        test = m.sample(truth, controls, cfg['test_records'] // len(controls),
                        cfg['bins'], seed + 100000, row['detector_dead_bins_truth'])
        for batch, field in [(train, 'training_sha256'), (test, 'test_sha256')]:
            assert hashlib.sha256(b''.join(x.tobytes() for x in batch)).hexdigest() == row[field]
        nll = -m.all_logs(train, fitted, controls, blind).sum()
        assert abs(nll - row['joint_fit']['best']['negative_loglikelihood']) < 1e-7
        scores = {key: np.array(value) for key, value in row['scores'].items()}
        expected = {
            'joint': m.all_logs(test, fitted, controls, blind),
            'known_nuisance': m.all_logs(test, replace(truth, g_defect=row['known_nuisance_fit']['g_hat']), controls, blind),
            'generator_oracle': m.all_logs(test, truth, controls, row['detector_dead_bins_truth']),
            'joint_dimension5': m.all_logs(test, replace(fitted, n_cavity=5), controls, blind)}
        for key, field in [('hmm', 'hmm_selected_parameters'), ('rate_matched_telegraph', 'telegraph')]:
            expected[key] = np.concatenate([
                hmm_likelihood_and_stats(data, np.array(b[field]['initial']),
                                         np.array(b[field]['transition']), np.array(b[field]['emissions']))
                for data, b in zip(test, row['baseline_fits'])])
        for key, value in expected.items():
            error = float(np.max(np.abs(scores[key] - value)))
            assert error < 1e-8
            max_score_error = max(max_score_error, error)
        for key, (first, second) in mappings.items():
            stat = row['paired'][key]
            delta = scores[first] - scores[second]
            assert abs(delta.mean() - stat['mean_delta_nats_per_record']) < 1e-12
            groups = np.split(delta, np.cumsum(stat['records_per_control'])[:-1])
            rng = np.random.default_rng(stat['seed'])
            boot = np.zeros(stat['bootstrap_replicates'])
            for group in groups:
                boot += len(group) / len(delta) * np.mean(
                    group[rng.integers(len(group), size=(len(boot), len(group)))], axis=1)
            assert np.max(abs(np.quantile(boot, [.025, .975]) - stat['bootstrap_95_percentile_nats_per_record'])) < 1e-12
        audit_path = HERE / 'parameter_validation_v2' / path.name
        audit = json.loads(audit_path.read_text())
        assert audit['fit_sha256'] == digest(path)
        assert audit['audit_source_sha256'] == digest(HERE / 'parameter_diagnostics.py')
        if audit['normal_intervals_available']:
            hessian = np.array(audit['hessian_scaled_coordinates'])
            se = np.sqrt(np.diag(np.linalg.inv(hessian))) * m.SCALE
            for j, name in enumerate(m.NAMES):
                assert abs(se[j] - audit['local_normal_approximate_95pct_intervals'][name]['standard_error']) < 1e-10
        cases.append({'case': row['case'], 'fit_sha256': digest(path),
                      'canonical_parameter_audit_sha256': digest(audit_path),
                      'regenerated_train_and_test_hashes_match': True,
                      'training_likelihood_reproduced': True,
                      'all_six_score_vectors_reproduced': True,
                      'all_four_stratified_bootstrap_intervals_reproduced': True,
                      'audit_fit_and_source_hashes_match': True,
                      'physical_coordinate_standard_errors_recounted_when_available': True})
        if row['detector_dead_bins_truth']:
            dead[blind] = (row, scores)
    assert len(cases) == 6 and set(dead) == {0, 1}
    for field in ['training_sha256', 'test_sha256']:
        assert dead[0][0][field] == dead[1][0][field]
    delta = dead[1][1]['joint'] - dead[0][1]['joint']
    rng = np.random.default_rng(991112)
    boot = delta[rng.integers(len(delta), size=(10000, len(delta)))].mean(axis=1)
    result = {'review_scope': __doc__.strip(), 'reviewer': 'independent collaborating agent',
              'all_checks_passed': True, 'python': platform.python_version(),
              'numpy': np.__version__, 'review_source_sha256': digest(Path(__file__)),
              'source_manifest_sha256': digest(HERE / 'inference_results/protocol.json'),
              'max_reproduced_heldout_score_error': max_score_error, 'cases': cases,
              'additional_descriptive_deadtime_comparison': {
                  'corrected_minus_omitted_mean_nats_per_record': float(delta.mean()),
                  'bootstrap_95_percentile': np.quantile(boot, [.025, .975]).tolist(),
                  'bootstrap_seed': 991112, 'bootstrap_replicates': 10000,
                  'same_train_and_test_records': True,
                  'scope': 'Added after inspecting frozen results; descriptive paired comparison conditional on fitted models, not training or optimizer uncertainty.'},
              'interpretation_limits': [
                  'Controls break tested exact sign symmetry; first controlled local detuning interval still crosses zero.',
                  'Both fixed-protocol QRSM-minus-HMM heldout intervals cross zero.',
                  'Controlled predictive gains compare shared physical parameters with separate control-specific HMMs.',
                  'Deadtime correction improves predictions but leaves dephasing at a search bound and detector efficiency biased.',
                  'Local curvature intervals are uncalibrated and may cross physical domains; they do not prove unique identification.',
                  'No physical data, cloud hardware, computational advantage, or lithography validation is implied.']}
    output = HERE / 'independent_review.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'cases': len(cases), 'passed': True,
                      'max_score_error': max_score_error}, indent=2))


if __name__ == '__main__':
    main()
