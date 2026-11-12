"""Package frozen research evidence into a no-server-required application.

No benchmark is run or tuned here. This copies exact saved values and adds
plain-language descriptions. Run again after final research documentation edits.
"""
from pathlib import Path
import hashlib
import json
import shutil
import csv

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

RESEARCH_SOURCES={
    'frequency':'laser_sensor_viability/followup/main/results.json',
    'drive':'qrsm_photon_poc/drive_diagnostics_followup/main/results.json',
    'prior':'qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_estimation_control.json',
    'phase':'quantum_lithography_poc/phase_inspection_followup/results.json',
    'spatial':'finals-lithography/full_spatial_circuit/results.json',
    'inference_ignored':'qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit0.json',
    'inference_aware':'qrsm_photon_poc/followup/inference_results/fixed_411101_dead1_fit1.json',
    'dot':'quantum_dot_bridge/results.json',
    'hom_reference':'quantum_dot_bridge/reference_hom/provenance_manifest.json',
    'hom_analysis':'quantum_dot_bridge/hom_analysis/results.json',
    'joint_hom':'quantum_dot_bridge/qrsm_hom_followup/main/results.json',
    'dot_design':'quantum_dot_bridge/qrsm_hom_followup/exploratory_design/design_results.json',
    'dot_design_validation':'quantum_dot_bridge/qrsm_hom_followup/exploratory_design/validation_run/results.json',
    'hardware':'hardware_campaign/results.json',
}

def build_research(evidence):
    """Keep current followups separate from the historical known-onset data."""
    sources={key:json.loads((ROOT/rel).read_text(encoding='utf8')) for key,rel in RESEARCH_SOURCES.items()}
    assert sources['frequency']['mode']=='main'
    assert len(sources['drive']['cases'])==13
    assert sources['prior']['main_results_sha256']==sha(ROOT/RESEARCH_SOURCES['drive'])
    assert sources['inference_ignored']['test_sha256']==sources['inference_aware']['test_sha256']
    assert sources['dot']['provenance']['all_quadrature_checks_passed']
    assert sources['hom_reference']['all_checks_passed']
    assert sources['hom_analysis']['schema']=='hom-area-analysis-v1'
    assert sources['hardware']['schema']=='ra-hardware-campaign-summary-v1'
    assert sources['hardware']['status']=='complete'
    assert sources['hom_analysis']['reference_manifest_sha256']==sha(ROOT/RESEARCH_SOURCES['hom_reference'])
    primary_review=json.loads((ROOT/'quantum_dot_bridge/hom_analysis/independent_primary.json').read_text())
    assert primary_review['results_sha256']==sha(ROOT/RESEARCH_SOURCES['hom_analysis'])
    assert primary_review['all_primary_areas_centers_and_point_estimates_match']
    histograms=[]
    for entry in sources['hom_reference']['files']:
        source=ROOT/'quantum_dot_bridge/reference_hom'/entry['path']
        assert sha(source)==entry['sha256']
        assert sources['hom_analysis']['raw_sha256'][entry['path']]==entry['sha256']
        with source.open(newline='',encoding='utf8') as f:
            reader=csv.DictReader(f)
            assert reader.fieldnames==['Time (ps)','Counts']
            rows=[[int(r['Time (ps)']),int(r['Counts'])] for r in reader]
        assert len(rows)==5000 and sum(r[1] for r in rows)==entry['count_sum']
        histograms.append({'file':entry['path'],'local':'evidence/hom/'+entry['path'],
                           'sha256':entry['sha256'],'polarization':entry['polarization'],
                           'excitation_pulse_separation_ns':entry['excitation_pulse_separation_ns'],
                           'time_ps':[r[0] for r in rows],'counts':[r[1] for r in rows]})
    for path in ['qrsm_photon_poc/drive_diagnostics_followup/main/independent_review.json',
                 'qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_independent_review.json']:
        assert json.loads((ROOT/path).read_text())['all_checks_passed']
    payload={'snapshot':'11 November 2026','sources':sources,'hom_histograms':histograms,
             'provenance':{key:{'canonical':rel,'local':f'evidence/research_{key}.json','sha256':sha(ROOT/rel)} for key,rel in RESEARCH_SOURCES.items()}}
    (HERE/'research-data.js').write_text('// Generated exact followup outputs; no experiment runs in the browser.\nwindow.RESEARCH_DATA='+json.dumps(payload,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf8')
    files={ROOT/rel:evidence/f'research_{key}.json' for key,rel in RESEARCH_SOURCES.items()}
    for src,name in {
        'RESEARCH_RESULTS.md':'RESEARCH_RESULTS.md',
        'RESEARCH_CURRENT.md':'RESEARCH_CURRENT.md',
        'laser_sensor_viability/followup/README.md':'CURRENT_FREQUENCY.md',
        'qrsm_photon_poc/drive_diagnostics_followup/README.md':'CURRENT_DRIVE.md',
        'quantum_lithography_poc/phase_inspection_followup/README.md':'PHASE_INSPECTION.md',
        'finals-lithography/full_spatial_circuit/README.md':'FULL_SPATIAL_CIRCUIT.md',
        'qrsm_photon_poc/followup/README.md':'INFERENCE_FOLLOWUP.md',
        'qrsm_photon_poc/drive_diagnostics_followup/main/independent_review.json':'drive_independent_review.json',
        'qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_independent_review.json':'prior_independent_review.json',
        'laser_sensor_viability/followup/validation.json':'frequency_validation.json',
        'quantum_lithography_poc/phase_inspection_followup/verification.json':'phase_verification.json',
        'finals-lithography/full_spatial_circuit/independent_review.json':'spatial_independent_review.json',
        'quantum_dot_bridge/README.md':'QUANTUM_DOTS.md',
        'quantum_dot_bridge/PROTOCOL.md':'QUANTUM_DOT_PROTOCOL.md',
        'quantum_dot_bridge/independent_review.json':'dot_independent_review.json',
        'quantum_dot_bridge/reference_hom/README.md':'HOM_REFERENCE.md',
        'quantum_dot_bridge/reference_hom/DATA_LICENSE.md':'HOM_DATA_LICENSE.md',
        'quantum_dot_bridge/reference_hom/validation.json':'hom_reference_validation.json',
        'quantum_dot_bridge/hom_analysis/PROTOCOL.md':'HOM_ANALYSIS_PROTOCOL.md',
        'quantum_dot_bridge/hom_analysis/README.md':'HOM_ANALYSIS.md',
        'quantum_dot_bridge/hom_analysis/independent_primary.json':'hom_analysis_independent_primary.json',
        'quantum_dot_bridge/hom_analysis/validation.json':'hom_analysis_validation.json',
    }.items():files[ROOT/src]=evidence/name
    (evidence/'hom').mkdir(exist_ok=True)
    for entry in sources['hom_reference']['files']:
        files[ROOT/'quantum_dot_bridge/reference_hom'/entry['path']]=evidence/'hom'/entry['path']
    # Keep this evidence tree intact: its protocols, receipts and source links
    # remain usable when the app folder is copied without the repository.
    joint_root=ROOT/'quantum_dot_bridge/qrsm_hom_followup'
    extra_files=[]
    for path in joint_root.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':
            extra_files.append((path,evidence/'joint-hom'/path.relative_to(joint_root)))
    for name in ['README.md','RESULTS.md','coverage.md','coverage.json']:
        files[ROOT/'hardware_campaign'/name]=evidence/'hardware'/name
    for rel,expected in sources['hardware']['input_sha256'].items():
        source=ROOT/rel
        assert sha(source)==expected,rel
        files[source]=evidence/'hardware'/source.relative_to(ROOT/'hardware_campaign')
    return list(files.items())+extra_files

def build():
    result_path=ROOT/'laser_sensor_viability/results.json'
    trace_path=ROOT/'laser_sensor_viability/example_traces.json'
    results=json.loads(result_path.read_text(encoding='utf8'))
    traces=json.loads(trace_path.read_text(encoding='utf8'))
    original_path=ROOT/'research-validation/original_after_click_verification.json'
    original=json.loads(original_path.read_text(encoding='utf8'))
    if not original.get('verified'):raise ValueError('Original after-click verification has not passed')
    labels={'classical':'Power + primary coherent',
            'classical_quantum':'Baseline + atomic reference',
            'two_classical':'Baseline + independent coherent'}
    colors={'classical':'#edb568','classical_quantum':'#64d9e9','two_classical':'#b9a8e5'}
    methods=[{**m,'label':labels[m['id']],'color':colors[m['id']]} for m in results['methods'] if m['id'] in labels]
    scenarios=[]
    for raw in results['scenarios']:
        c=dict(raw);c['trace']=traces['scenarios'][c['id']]
        description=c['description'].replace('from200ms to12ms','from 200 ms to 12 ms').replace('+/-0.7Hz','±0.7 Hz').replace('A10%','A 10%').replace('correlation0.95','correlation 0.95')
        c['description']='128 s record, 64 independent atoms, 698 nm laboratory surrogate. The batch detector knows the programmed change time (64 s). '+description
        c['label']=c['label'].replace('by10%','by 10%')
        a=c['methods']['classical'];q=c['methods']['classical_quantum'];cc=c['methods']['two_classical']
        if c['id']=='nominal':
            finding=f"The atomic channel lifts detection from {100*a['detection_rate']:.1f}% to {100*q['detection_rate']:.1f}%. A second coherent reference reaches {100*cc['detection_rate']:.1f}% under these assumptions."
        elif c['id']=='atomic_reference_drift':
            finding=f"An unstable atom can look like an unstable laser. False alarms reach {100*q['false_alarm_rate']:.1f}% for the atomic combination, versus {100*cc['false_alarm_rate']:.1f}% for the two coherent references."
        elif c['id']=='shared_path_drift':
            finding="Every frequency channel sees the shared path shift. These observations cannot identify whether the source or the sampled path moved."
        elif c['id']=='short_coherence':
            finding="Shorter atomic coherence changes its calibrated response. The fixed decision rule loses reliability; new calibration would be a separate experiment."
        elif c['id']=='primary_reference_drift':
            finding="An independent reference helps challenge a misleading primary receiver. The atomic and second coherent channels provide different physical references."
        elif c['id']=='power_only_disturbance':
            finding="Power fluctuation can perturb frequency readout. Here the observed photodiode record supplies a calibrated cross-sensitivity correction."
        elif c['id']=='correlated_references':
            finding="Adding a channel is most useful when its errors add independent information. Correlation tests the fusion rule beyond its calibration conditions."
        else:
            finding="This gradual change was excluded from calibration. All detection thresholds and estimator weights remain fixed."
        c['finding']=finding
        c['trace_note']='One frozen +0.5 Hz injected record; the change starts halfway through. Hidden source truth is shown only for explanation. Atomic values are calibrated noisy ensemble readouts. The primary trace uses the split allocation.'
        if c['id']=='gradual_source_change':c['trace_note']='One frozen gradual +0.5 Hz injection, rising over the middle half of the record. Hidden source truth is shown only for explanation. The primary trace uses the split allocation.'
        scenarios.append(c)
    data={'version':1,'evidence_type':results['evidence_type'],'config':results['config'],
          'methods':methods,'scenarios':scenarios,'source_sha256':{'results.json':sha(result_path),'example_traces.json':sha(trace_path)},
          'benchmark_note':'4,000 held-out records per class. Independent null calibration targets 5% false alarms; actual rates appear above. Same 128 s duration and assumed source-tap allotment. Atomic support light, reference apparatus and cost are unmatched.',
          'resource_ledger':results['resource_ledger'],'response_curve':results['response_curve'],
          'original':original,'original_sha256':sha(original_path)}
    (HERE/'data.js').write_text('// Generated by import_results.py from frozen research outputs.\nwindow.DEMO_DATA='+json.dumps(data,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf8')
    evidence=HERE/'evidence';evidence.mkdir(exist_ok=True)
    assets=HERE/'assets';assets.mkdir(exist_ok=True)
    files={result_path:evidence/'sensor_results.json',trace_path:evidence/'example_traces.json',
           ROOT/'laser_sensor_viability/README.md':evidence/'SENSOR_MODEL.md',
           ROOT/'FINALS_EVIDENCE.md':evidence/'FINALS_EVIDENCE.md',
           ROOT/'LASER_DIAGNOSTICS_ROADMAP.md':evidence/'LASER_DIAGNOSTICS_ROADMAP.md',
           ROOT/'qrsm_photon_poc/generated/two_bin_double.json':evidence/'two_bin_double.json',
           original_path:evidence/'original_after_click_verification.json'}
    for name in ['laser-diagnostic-lenses','rewind-amplify']:
        for ext in ['mp4','png']:files[ROOT/'animations'/f'{name}.{ext}']=assets/f'{name}.{ext}'
    files[ROOT/'animations/video_manifest.json']=assets/'video_manifest.json'
    files=list(files.items())+build_research(evidence)
    for src,dst in files:
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    # Preserve local navigation from the complete new study to the separately
    # packaged hardware tree. Canonical scientific JSON/source bytes are unchanged.
    link_adaptations={
        'evidence/joint-hom/README.md':('../../hardware_campaign/','../hardware/'),
        'evidence/joint-hom/exploratory_design/README.md':('../../../hardware_campaign/','../../hardware/'),
    }
    adapted=[]
    for rel,(before,after) in link_adaptations.items():
        path=HERE/rel;old=path.read_text(encoding='utf8');new=old.replace(before,after)
        if old!=new:
            canonical_hash=sha(path);path.write_text(new,encoding='utf8')
            adapted.append({'file':rel,'canonical_sha256':canonical_hash,'change':'Relative hardware-campaign links adapted for standalone folder layout.'})
    # Retire only this app's generated GIF copies after successful MP4 packaging.
    # The original scientific-animation sources remain in animations/.
    for name in ['laser-diagnostic-lenses','rewind-amplify']:
        legacy=assets/f'{name}.gif'
        original_gif=ROOT/'animations'/f'{name}.gif'
        if legacy.is_file() and original_gif.is_file() and sha(legacy)==sha(original_gif):
            if legacy.resolve().parent != assets.resolve():raise ValueError('Unexpected legacy asset path')
            legacy.unlink()
    (evidence/'manifest.json').write_text(json.dumps({'generated_by':'import_results.py','document_link_adaptations':adapted,'files':{str(dst.relative_to(HERE)).replace('\\','/'):sha(dst) for _,dst in files}},indent=2)+'\n')
    print(f'Packaged {len(scenarios)} frozen scenarios and {len(files)} evidence/assets files.')

if __name__=='__main__':build()
