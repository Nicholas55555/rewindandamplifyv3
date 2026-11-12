"""Recheck provenance and completed validation receipts without rerunning studies.

This adds an integration/provenance check; it does not replace independent
physics checks, reproduce Monte Carlo data, or execute the large circuits.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent
checked = {}
receipts = []


def sha(path):
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    checked[path.relative_to(ROOT).as_posix()] = value
    return value


def read(name):
    path = ROOT / name
    sha(path)
    return json.loads(path.read_text(encoding='utf-8'))


def match(path, expected):
    assert sha(path) == expected, str(path)


def mapping(base, hashes):
    for name, expected in hashes.items():
        path = ROOT / base / name.replace('\\', '/')
        assert path.resolve().is_relative_to(ROOT)
        match(path, expected)


def receipt(name, status_key='all_checks_passed', status_value=True):
    data = read(name)
    assert data[status_key] == status_value, name
    receipts.append({'path': name, 'sha256': checked[name],
                     'checked_status': data[status_key]})
    return data


def main():
    spatial = 'finals-lithography/followup'
    receipt(spatial+'/validation.json', 'status', 'passed')
    manifest = read(spatial+'/audit_manifest.json')
    mapping('', manifest['reviewed_original_files'])
    mapping(spatial, manifest['current_followup_files'])
    mapping(spatial+'/archive', manifest['archived_runs'])

    full = 'finals-lithography/full_spatial_circuit'
    receipt(full+'/validation.json', 'status', 'passed')
    review = receipt(full+'/independent_review.json', 'status', 'passed_with_explicit_scope_limits')
    assert not review['blocking_findings']
    match(ROOT/full/'results.json', review['reviewed_results_sha256'])
    mapping(full, review['source_sha256'])
    mapping('finals-lithography', review['imported_source_sha256'])
    for item in review['qpy_checks']:
        match(ROOT/full/item['file'], item['sha256'])
    result = read(full+'/results.json')
    assert result['all_constructions_completed'] and result['all_explicit_qpy_roundtrips_completed']
    assert not result['all_qpy_roundtrips_completed'], 'Compact readback limitation must remain explicit'

    for sub in ('exposure_followup', 'phase_inspection_followup'):
        base = 'quantum_lithography_poc/'+sub
        data = read(base+'/verification.json')
        assert data.get('unit_tests_passed', data.get('tests_passed', 0)) > 0
        mapping(base, data['sha256'])
        result = read(base+'/results.json')
        mapping('' if sub=='exposure_followup' else base, result['source_sha256'])
        receipts.append({'path': base+'/verification.json', 'sha256': checked[base+'/verification.json'],
                         'checked_status': 'saved tests and artifact hashes match'})
    supplement = read('quantum_lithography_poc/exposure_followup/moments_supplement.json')
    assert supplement['checks']['passed'] and supplement['checks']['moment_records'] == 90
    mapping('', supplement['source_sha256'])
    mapping('quantum_lithography_poc/exposure_followup', supplement['artifact_sha256'])

    sensor = 'laser_sensor_viability/followup'
    validation = receipt(sensor+'/validation.json')
    result = read(sensor+'/main/results.json')
    mapping('laser_sensor_viability', result['source_sha256'])
    match(ROOT/sensor/'main/record_outcomes.npz', result['record_outcomes_sha256'])
    match(ROOT/sensor/'main/results.json', validation['result_sha256'])

    inference = 'qrsm_photon_poc/followup'
    review = receipt(inference+'/independent_review.json')
    assert len(review['cases']) == 6
    match(ROOT/inference/'verify_independent_review.py', review['review_source_sha256'])
    match(ROOT/inference/'inference_results/protocol.json', review['source_manifest_sha256'])
    protocol = read(inference+'/inference_results/protocol.json')
    mapping(inference, protocol['source_sha256'])
    for case in review['cases']:
        name = case['case']+'.json'
        match(ROOT/inference/'inference_results'/name, case['fit_sha256'])
        match(ROOT/inference/'parameter_validation_v2'/name, case['canonical_parameter_audit_sha256'])
    dynamics = read(inference+'/dynamics_results.json')
    mapping('qrsm_photon_poc', dynamics['source_sha256'])
    assert dynamics['independent_quantum_jumps']['all_inside_intervals']

    multi = 'qrsm_photon_poc/multibin_followup'
    receipt(multi+'/main/validation.json')
    provenance = read(multi+'/main/provenance_start.json')
    mapping('qrsm_photon_poc', provenance['source_sha256'])
    for name in ('ideal_0p03', 'ideal_0p003', 'noise_0p03', 'noise_0p003'):
        case = read(multi+'/main/'+name+'.json')
        match(ROOT/multi/'main'/case['branch_archive'], case['branch_archive_sha256'])

    drive = 'qrsm_photon_poc/drive_diagnostics_followup'
    # New drive experiment must be fully checked before an integrated receipt.
    provenance = read(drive+'/main/provenance_start.json')
    mapping('', provenance['source_sha256'])
    result = read(drive+'/main/results.json')
    match(ROOT/drive/'main/provenance_start.json', result['provenance_sha256'])
    validation = receipt(drive+'/main/validation.json')
    match(ROOT/drive/'main/results.json', validation['results_sha256'])
    match(ROOT/drive/'validate_and_plot.py', validation['review_source_sha256'])
    mapping(drive+'/main', validation['artifact_sha256'])
    review = read(drive+'/main/independent_review.json')
    assert review.get('all_checks_passed') or str(review.get('status', '')).startswith('passed')
    assert not review.get('blocking_findings', [])
    match(ROOT/drive/'main/results.json', review['results_sha256'])
    match(ROOT/drive/'main/provenance_start.json', review['provenance_sha256'])
    mapping('', review['reviewed_source_sha256'])
    mapping(drive+'/main', review['reviewed_artifact_sha256'])
    receipts.append({'path': drive+'/main/independent_review.json',
                     'sha256': checked[drive+'/main/independent_review.json'], 'checked_status': 'passed'})
    prior = receipt(drive+'/main/prior_only_independent_review.json')
    match(ROOT/drive/'main/prior_only_estimation_control.json', prior['supplement_results_sha256'])
    match(ROOT/drive/'prior_only_control.py', prior['supplement_source_sha256'])
    match(ROOT/drive/'main/results.json', prior['main_results_sha256'])
    match(ROOT/drive/'main/independent_review.json', prior['main_independent_review_sha256'])
    mapping(drive+'/main', prior['raw_sha256'])

    report = {'schema': 'research-integration-checks-v1',
              'executed_utc': datetime.now(timezone.utc).isoformat(),
              'all_checks_passed': True,
              'scope': 'Rechecked saved validation statuses, source/artifact provenance and canonical completion. No new physical experiment or repeat statistical evidence.',
              'receipts': receipts, 'files_rechecked': checked,
              'unique_files_rechecked': len(checked),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output = ROOT/'research-validation/research_checks.json'
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'all_checks_passed': True, 'unique_files_rechecked': len(checked),
                      'validation_receipts': len(receipts)}))


if __name__ == '__main__':
    main()
