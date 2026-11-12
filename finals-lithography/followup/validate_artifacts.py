"""Execute follow-up tests and validate saved result/source/artifact integrity."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    q=json.loads((ROOT/'correlated_spatial_results.json').read_text())
    s=json.loads((ROOT/'spatial_coverage_refined_results.json').read_text())
    for name,digest in q['source_sha256'].items():
        assert sha(ROOT/name)==digest, f'changed correlated source {name}'
    assert sha(ROOT/'spatial_coverage.py')==s['source_sha256']
    assert sha(ROOT.parent/'spatial_model.py')==s['original_source_sha256']
    assert len(q['ideal_cases'])==6 and len(q['noise_cases'])==9
    assert all(r['status']=='completed' for r in q['noise_cases'])
    for row in q['ideal_cases']:
        assert abs(row['ideal']['hit_probability']-row['amplification_formula'])<1e-10
        assert row['ideal']['conditional_joint_tv']<1e-11
        assert row['dirty_workspace_probability']<1e-20
    for row in q['noise_cases']:
        assert abs(row['normalization']-1)<1e-10
        if row['cx_depolarizing_parameter']==0:
            expected=next(r for r in q['ideal_cases'] if r['rounds']==row['rounds'] and r['style']=='enumerated')
            assert abs(row['after_readout']['hit_probability']-expected['ideal']['hit_probability'])<1e-10
            assert row['after_readout']['conditional_joint_tv']<1e-11
    old=json.loads((ROOT/'archive'/'spatial_coverage_refined_results.json').read_text())
    assert old['doses']==s['doses'], 'nondefault argument fix unexpectedly changed default numerical results'
    for dose in s['doses']:
        ref=dose['reference']
        assert ref['lower']<=ref['upper'] and ref['relative_width']<.0005
        assert dose['independent_fft_reference_check']['absolute_disagreement']<1e-12
        assert dose['independent_fft_reference_check']['log_chernoff_upper_bound_on_wraparound']<-100
        assert dose['tuning']['total_pilot_maps']==40000
        for method in dose['methods'].values():assert len(method['runs'])==100
    for name in ('correlated_spatial_bridge.png','spatial_coverage.png'):
        assert (ROOT/name).read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_*.py')
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (ROOT/'test_results.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():
        print(stream.getvalue());raise SystemExit(1)
    report={'status':'passed','executed_utc':datetime.now(timezone.utc).isoformat(),
            'behavioral_tests_run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),
            'saved_artifact_checks':['all actual numerical source hashes match',
               'six ideal amplification cases match formulas and conditional law',
               'nine complete bounded density cases normalized; zero-noise matches ideal',
               'default coverage numerical results identical before/after optional-argument fix',
               'refined deterministic reference brackets and independent FFT checks',
               'held-out run counts and pilot budgets', 'PNG signatures'],
            'visual_review':'Both actual-result PNGs inspected; spacing adjusted for coverage labels.',
            'limitations':['No cloud, QPU, wafer, or calibrated photonic device tested.',
                           'Longdouble may equal float64 precision on Windows; independent FFT check is separate.',
                           'Reference bounds evaluated in floating point, not certified interval arithmetic.']}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    originals=sorted(p for p in ROOT.parent.iterdir() if p.is_file() and p.suffix in ('.py','.js','.html','.md'))
    originals.append(ROOT.parent.parent/'QUANTUM_PHOTOLITHOGRAPHY_ROADMAP.md')
    manifest={'created_utc':report['executed_utc'],
              'review_scope':'All current finals-lithography Python/JavaScript/HTML sources, tests, README and VIABILITY_COST_README, plus root QUANTUM_PHOTOLITHOGRAPHY_ROADMAP, read fresh before implementation.',
              'preservation_note':'No edits made outside followup/. Reviewed original hashes are recorded at finalization, not represented as an independently captured before/after snapshot.',
              'reviewed_original_files':{str(p.relative_to(ROOT.parent.parent)):sha(p) for p in originals},
              'current_followup_files':{p.name:sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name!='audit_manifest.json'},
              'archived_runs':{p.name:sha(p) for p in sorted((ROOT/'archive').glob('*.json'))}}
    (ROOT/'audit_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','behavioral_tests':tests.testsRun,'reviewed_original_files':len(originals)}))


if __name__=='__main__':main()
