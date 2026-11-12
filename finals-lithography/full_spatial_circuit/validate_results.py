"""Validate saved construction artifacts without loading a large quantum state."""
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result=json.loads((ROOT/'results.json').read_text())
    for file,digest in result['source_sha256'].items():assert sha(ROOT/file)==digest,file
    for file,digest in result['imported_frozen_source_sha256'].items():assert sha(ROOT.parent/file)==digest,file
    assert result['all_constructions_completed']
    assert result['all_explicit_qpy_roundtrips_completed']
    assert not result['all_qpy_roundtrips_completed']
    for row in result['circuits']:
        assert row['constructed']
        if row['style']=='compact':
            assert row['qubits']==219 and row['status']=='constructed_qpy_unsupported'
        else:
            assert row['qubits']==389 and row['status']=='completed'
            assert row['signature_before']==row['signature_after']
            assert sha(ROOT/row['qpy_file'])==row['qpy_sha256']
            assert (ROOT/row['qpy_file']).stat().st_size==row['qpy_bytes']
            assert row['observed_peak_worker_rss_mb']<row['guard_rss_limit_mb']==1536
            assert row['preflight_available_system_memory_mb']>=4*row['guard_rss_limit_mb']
            counts=row['recursive_operation_counts'];cost=result['explicit_synthesis_costs'][row['weight_rounding']]
            assert cost['complete_one_round_generic_cx_constructive_upper_bound']==counts['ccx']*6+counts['cx']+3*49*196
            assert cost['complete_one_round_generic_u_constructive_upper_bound']==counts['ccx']*9+406+3*49*161
    bounds=[]
    for row in result['bounds']:
        low,high=row['original_process_probability_bracket']
        cap=row['union_bound_any_count_value_changes']
        assert 0<low<=high<1
        for name,p in row['finite_capped_integer_lattice_cdf'].items():
            diff=p-row['uncapped_integer_lattice_cdf'][name]
            assert -1e-13<=diff<=cap+1e-13
        epsilon=cap+row['uncapped_integer_lattice_cdf']['floor']-row['uncapped_integer_lattice_cdf']['ceil']
        bounds.append({'dose':row['dose'],'conditional_history_tv_conservative_upper_bound':min(1,2*epsilon/low),
                       'scope':'Ideal model approximation bound only; not noisy-circuit fidelity.'})
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT),pattern='test_full_spatial.py'))
    (ROOT/'test_results.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():print(stream.getvalue());raise SystemExit(1)
    report={'schema':'full-spatial-validation-v1','status':'passed','executed_utc':datetime.now(timezone.utc).isoformat(),
            'behavioral_tests':tests.testsRun,'source_hashes_match':True,'frozen_import_hashes_match':True,
            'explicit_clean_qpy_hashes_match':True,'construction_roundtrip_records_checked':True,
            'compact_qpy_supported':False,'full_state_simulation_performed':False,'full_generic_transpilation_performed':False,
            'full_noisy_validation_performed':False,'hardware_run_performed':False,
            'resource_counts_checked':True,'conditional_approximation_bounds':bounds,
            'failure_records':[str(p.relative_to(ROOT)) for p in sorted((ROOT/'archive').glob('results*.json'))]}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    manifest={'created_utc':report['executed_utc'],
              'files':{p.name:sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name!='artifact_manifest.json'},
              'claim_scope':'Constructed finite approximation with tested components and actual explicit QPY round-trip; not full-state or hardware execution.'}
    (ROOT/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','tests':tests.testsRun,'valid_clean_qpy_files':2,
                      'full_state_simulation_performed':False,'conditional_approximation_bounds':bounds}))


if __name__=='__main__':main()
