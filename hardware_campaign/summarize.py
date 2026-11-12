"""Build a compact, traceable hardware handoff after all requested jobs finish.

No network calls. Historical analyses remain untouched; when the analyzer source
changes, a new source-hash-named analysis is generated from the immutable raw data.
"""
import argparse
import hashlib
import json
from pathlib import Path

import analyze
from feasibility.contrast_analysis import difference

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
EXPECTED_RUNS=('original_plain_v2','dots_plain_v1','optical_controls_plain_v1',
               'spatial_plain_v1','original_suppressed_v1','dots_suppressed_v1',
               'optical_dilation_plain_v2','original_precision_v1',
               'extensions_plain_v1','dots_selected_plain_v1')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def relative(path):return str(Path(path).relative_to(ROOT)).replace('\\','/')


def current_analysis(folder):
    expected={'hardware_campaign/analyze.py':sha(HERE/'analyze.py'),
              'hardware_campaign/feasibility/adapters.py':sha(HERE/'feasibility/adapters.py'),
              'hardware_campaign/optical_controls/analyze_counts.py':sha(HERE/'optical_controls/analyze_counts.py')}
    for path in sorted(folder.glob('analysis*.json')):
        result=read(path)
        if result.get('source_sha256')==expected and result['input_sha256']['raw.json']==sha(folder/'raw.json'):
            return path,result
    path=folder/('analysis_'+expected['hardware_campaign/analyze.py'][:12]+'.json')
    return path,analyze.analyze_run(folder,path)


def compact_row(row,run):
    result={k:row[k] for k in ('name','shots','logical_qubits','native_two_qubit_gate_count','compiled_depth','observables')}
    result['run']=run
    for key in ('raw_full_z_tv','raw_reference_marginal_z_tv','reference_marginal_qubits',
                'ideal_multinomial_expected_full_z_tv_at_these_shots',
                'ideal_multinomial_expected_reference_marginal_tv_at_these_shots'):
        if key in row:result[key]=row[key]
    return result


def hero(row):
    o=row['observables'];s=o['selected']
    return {'name':row['name'],'accepted':s['successes'],'shots':s['shots'],
            'probability':s['probability'],'wilson95':s['wilson95'],
            'logical_ideal_acceptance':o['logical_ideal_selected_probability'],
            'native_two_qubit_gates':row['native_two_qubit_gate_count'],
            'selected_history_tv_to_unsteered':o['selected_history_tv_to_unsteered_target'],
            'selected_history_tv_to_logical_ideal':o['selected_history_tv_to_logical_ideal'],
            'two_qubit_gates_per_raw_accepted_shot':row['native_two_qubit_gate_count']/s['probability'] if s['probability'] else None}


def run_hero(result):
    rows={r['name']:r for r in result['rows']}
    local=hero(rows['click3-steered-memory+last-1-r1']);full=hero(rows['click3-steered-full-r1'])
    return {'run':result['run'],'job_id':result['job_id'],'local':local,'full':full,
            'difference':difference(local['accepted'],local['shots'],full['accepted'],full['shots'])}


def coverage_summary(analyses, hashes):
    """Reconcile the scoped family inventory against completed raw evidence."""
    inventory=read(HERE/'coverage.json')
    by_job={a['job_id']:a for a in analyses.values()}
    families=[]
    for family in inventory['families']:
        evidence=family.get('completed_evidence',[])
        for record in evidence:
            result=by_job[record['job_id']]
            assert record['backend']==result['backend']
            raw_path=HERE/'runs'/result['run']/'raw.json'
            assert record['raw_path']==relative(raw_path)
            raw=read(raw_path);rows={r['name']:r for r in raw['rows']}
            assert len(record['circuits'])==len(set(record['circuits']))
            assert sum(rows[name]['shots'] for name in record['circuits'])==record['shots']
        families.append({'id':family['id'],'title':family['title'],
                         'status':family['new_hardware_status'],
                         'executed_scope':family.get('executed_scope'),
                         'job_ids':sorted({e['job_id'] for e in evidence}),
                         'completed_evidence_records':len(evidence),
                         'remaining_work_items':len(family.get('remaining_work',[]))})
    assert inventory['family_count']==len(families)
    assert inventory['completed_job_count']==len(by_job)
    for path in (HERE/'coverage.json', HERE/'coverage.md'):
        hashes[relative(path)]=sha(path)
    return {'path':'hardware_campaign/coverage.json',
            'family_count':len(families),
            'families_with_completed_evidence':sum(bool(f['completed_evidence_records']) for f in families),
            'all_research_replicated':inventory['all_research_replicated'],
            'scope':'Family evidence includes explicitly limited component executions and one related distinct model; it is not full replication of every study. Families overlap in their use of hardware jobs and must not be added as independent experiments.',
            'families':families}


def build(allow_incomplete=False):
    missing=[name for name in EXPECTED_RUNS if not (HERE/'runs'/name/'raw.json').exists()]
    if missing and not allow_incomplete:raise RuntimeError('Awaiting raw results: '+', '.join(missing))
    runs=[];analyses={};hashes={};job_ids=set()
    for folder in sorted((HERE/'runs').iterdir()):
        if not (folder/'raw.json').exists():continue
        path,result=current_analysis(folder);raw=read(folder/'raw.json');plan=read(folder/'plan.json')
        if result['job_id'] in job_ids:raise ValueError('Duplicate job ID across run directories')
        job_ids.add(result['job_id']);analyses[folder.name]=result
        usage=raw['usage']
        if not isinstance(usage,(int,float)) or usage<0:raise ValueError('Unexpected actual QPU usage schema')
        metric=raw.get('metrics',{}).get('usage',{}).get('qpu_charge_time_seconds')
        if metric is not None and abs(metric-usage)>1e-8:raise ValueError('Usage/metrics disagreement')
        runs.append({'id':folder.name,'job_id':result['job_id'],'backend':result['backend'],
                     'mode':plan['mode'],'shots_per_pub':plan['shots'],
                     'science_circuits':len(result['rows']),'calibration_circuits':len(raw['rows'])-len(result['rows']),
                     'total_shots':sum(r['shots'] for r in raw['rows']),
                     'actual_quantum_seconds':usage,'analysis_path':relative(path),
                     'raw_path':relative(folder/'raw.json'),'plan_path':relative(folder/'plan.json'),
                     'workload_portal_url':'https://quantum.cloud.ibm.com/workloads',
                     'job_access_note':'IBM sign-in and appropriate access are required; local raw evidence is included.',
                     'compiled_qpy_sha256':plan['compiled_qpy_sha256']})
        for p in (path,folder/'raw.json',folder/'plan.json'):hashes[relative(p)]=sha(p)
    primary=analyses.get('original_precision_v1')
    headline=run_hero(primary) if primary else None
    if headline:
        headline.update(followup_selected_after_initial_results=True,
                        earlier_repeats=[run_hero(analyses[n]) for n in ('original_plain_v2','original_suppressed_v1') if n in analyses],
                        cost_scope='Native two-qubit gate accounting per raw accepted shot; excludes calibration, queue time, service overhead and the accuracy of the accepted answer. No money or speedup claim.')
    afterclick=None
    if primary:
        rows={r['name']:r for r in primary['rows']}
        afterclick={'run':primary['run'],'curves':{},'step6_comparisons':{},
                    'scope':'Known programmed defect/no-defect models. Fresh follow-up after initial data, analyzed separately without pooling jobs. Biased conditional answers are not discovery of a physical defect.'}
        for label,suffix in [('plain','r0'),('steered_local','r1'),('steered_full','full-r1'),('steered_memory','memory-r1')]:
            pair=[rows[f'loop-{model}-{suffix}'] for model in ('defect','nodefect')]
            for row in pair:
                afterclick['curves'][row['name']]={'selected':row['observables']['selected'],
                    'future':row['observables']['future_clicks_after_selected_click'],
                    'selected_history_tv_to_unsteered':row['observables']['selected_history_tv_to_unsteered_target']}
            a,b=[r['observables']['future_clicks_after_selected_click'][-1] for r in pair]
            x,y=a['raw_or_secondary_conditional'],b['raw_or_secondary_conditional']
            contrast=difference(x['successes'],x['shots'],y['successes'],y['shots'])
            contrast['ideal_difference']=a['unsteered_target']-b['unsteered_target']
            contrast['ideal_probabilities']=[a['unsteered_target'],b['unsteered_target']]
            afterclick['step6_comparisons'][label]=contrast
    families={k:[] for k in ('dot_frozen','dot_joint','dot_selected_four_pair','atomic','photon',
                             'spatial','optical_dilation','coherent_sector_aggregation')}
    extension={}
    for name,result in analyses.items():
        for row in result['rows']:
            family=row['family'];key=None
            if family=='frozen_classical_pair_memory_benchmark':key='dot_frozen'
            elif family=='sequential_emitter_environment_joint_photon_instrument':key='dot_joint'
            elif family=='selected_design_four_pair_joint_photon_instrument':key='dot_selected_four_pair'
            elif family=='atomic_finite_pulse':key='atomic'
            elif family=='photon_noon_or_mixture':key='photon'
            elif family=='correlated_spatial_2x2':key='spatial'
            elif family=='optical_retained_instrument':key='optical_dilation'
            elif family in ('independent_contact','catalog_cost_1024','semantic_catalog16','qrsm_fixed_round_history','bounded_rewind'):
                extension.setdefault(family,[]).append(compact_row(row,name))
            if key:families[key].append(compact_row(row,name))
        families['coherent_sector_aggregation'].extend(dict(run=name,**r) for r in result.get('coherent_sector_aggregation',[]))
    total=sum(r['actual_quantum_seconds'] for r in runs)
    coverage=coverage_summary(analyses,hashes) if not missing else None
    return {'schema':'ra-hardware-campaign-summary-v1','status':'complete' if not missing else 'in_progress',
            'missing_runs':missing,'backend':'ibm_marrakesh','execution':'Real IBM superconducting hardware, digital model circuits.',
            'jobs':len(runs),'science_circuit_executions':sum(r['science_circuits'] for r in runs),
            'calibration_circuit_executions':sum(r['calibration_circuits'] for r in runs),
            'total_shots':sum(r['total_shots'] for r in runs),'actual_campaign_quantum_seconds':total,
            'usage_scope':'Actual job usage summed across unique jobs; excludes the 24 seconds consumed before this campaign. Not wall time or a price estimate.',
            'runs':runs,'headline_original':headline,'afterclick_precision':afterclick,
            'family_results':families,'coverage_extensions':extension,'research_family_coverage':coverage,
            'limits':['No optical photons, quantum-dot source, lithography laser, resist or wafer were measured by these superconducting circuits.',
                      'Higher event acceptance is not enough: selected-answer error and hardware gate/noise costs are reported alongside it.',
                      'Wilson-based intervals condition on independent stationary shots; drift, calibration/model uncertainty and multiplicity are excluded.',
                      'Full-Z TV includes finite-shot sampling error and is not quantum-state fidelity. 29-qubit selected-dot cases have only a declared flag/memory marginal reference.',
                      'Secondary independent-readout inversion is a sensitivity analysis, not corrected truth or a confidence interval.',
                      'Fresh precision and selected-design follow-ups were chosen after earlier results; runs are not pooled to hide drift.',
                      'Full 7x7 spatial construction needs 219 compact or 389 explicit-clean qubits and does not fit the available 156-qubit backend.',
                      'Random 1024-entry cost benchmark is not semantic retrieval; fixed-round histories do not implement complete adaptive BBHT.',
                      'Classical exact recursion, dynamic programming and sequence models remain strong baselines; no quantum computational advantage is demonstrated.'],
            'source_sha256':{'hardware_campaign/summarize.py':sha(__file__),'hardware_campaign/analyze.py':sha(HERE/'analyze.py'),
                             'hardware_campaign/feasibility/contrast_analysis.py':sha(HERE/'feasibility/contrast_analysis.py')},
            'input_sha256':hashes,
            'job_retrieval_documentation':'https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/save-jobs'}


def report(result):
    h=result['headline_original'];local,full=h['local'],h['full'];delta=h['difference']
    ci=delta['independent_shot_wilson_based_interval95']
    lines=['# Real hardware campaign results','',
           f"{result['jobs']} completed IBM Marrakesh jobs executed {result['science_circuit_executions']} science circuits and {result['calibration_circuit_executions']} calibration circuits, totaling {result['total_shots']:,} shots and {result['actual_campaign_quantum_seconds']:g} charged QPU seconds. The campaign used superconducting qubits to emulate the specified models; it did not operate an optical sensor or inspect a wafer.",'',
           '## Original QRSM: useful sampling with measurable answer error','',
           'The fresh 8192-shot precision follow-up reused the same compiled circuits and physical mapping. It was chosen after the initial results and is reported separately, with no cross-job pooling.','',
           '| Quantity | Steered local reflection | Steered full reflection |','|---|---:|---:|',
           f"| Raw accepted trials | {local['accepted']}/{local['shots']} | {full['accepted']}/{full['shots']} |",
           f"| Raw acceptance | {100*local['probability']:.3f}% | {100*full['probability']:.3f}% |",
           f"| Native two-qubit gates | {local['native_two_qubit_gates']} | {full['native_two_qubit_gates']} |",
           f"| Selected-history TV from unsteered target | {local['selected_history_tv_to_unsteered']:.4f} | {full['selected_history_tv_to_unsteered']:.4f} |",'',
           f"Local minus full acceptance was {100*delta['probability_difference']:.3f} percentage points, with an independent-shot 95% interval of [{100*ci[0]:.3f}, {100*ci[1]:.3f}] points. The interval excludes drift, calibration uncertainty and model error. The lower-gate circuit returned more selected outcomes in this query; different operations, routing and drift remain confounders. The selected distribution still differed from the ideal answer.",'',
           'The earlier plain run and the exact-ISA DD/twirling repeat are retained in results.json. Suppression did not improve the headline conditional-history errors. A better result is not selected by silently pooling or discarding jobs.','',
           '## After-click fingerprint','']
    a=result['afterclick_precision']['step6_comparisons']['steered_local'];ci=a['independent_shot_wilson_based_interval95']
    lines += [f"In the fresh local-loop repeat, the programmed defect and no-defect models gave step 6 click probabilities {a['first']['probability']:.5f} and {a['second']['probability']:.5f}, versus ideal {a['ideal_probabilities'][0]:.5f} and {a['ideal_probabilities'][1]:.5f}. Their raw difference was {100*a['probability_difference']:.3f} percentage points [{100*ci[0]:.3f}, {100*ci[1]:.3f}]. The expected ordering is visible in this implementation, but the values remain biased; other loop implementations reverse the ordering. This is not a validated unknown-defect detector.",'',
              '## Other families and failures','',
              '- Quantum-dot circuits prepare nonorthogonal photon-mode states and perform joint symmetry measurements digitally. Raw overlap and conditional-memory errors remain visible; the selected four-pair model uses a declared flag/memory marginal, not a full 29-qubit reference.',
              '- Atomic Ramsey and photon-interferometer controls test physical channel/interference constructions. Photon loss, source failures, coherent vacuum and omitted photon-number tails stay charged. They do not repeat the complete laser monitoring or finite-budget phase-estimation studies.',
              '- Correlated spatial circuits show why acceptance alone is unsafe: an apparent event-rate match can coexist with a wrong selected count-map distribution and severe computed-workspace leakage.',
              '- Deep retained-instrument circuits are genuine negative stress tests. The two-bin all-click case accepts 8/512 trials, close to its 1.5466% ideal rate, yet its selected-data TV is 0.7604. Both three-bin all-click cases return zero selected trials, so no conditional answer is invented.',
              '- Coverage extensions retain the independent-site contact models, real 16-entry semantic reader, explicitly nonsemantic 1024-entry cost benchmark, longer fixed-round QRSM histories and approximate bounded rewind. Full 7×7 construction exceeds available device width.','',
              '## Evidence and interpretation','',
              f"The scoped [coverage inventory](coverage.md) records completed evidence for {result['research_family_coverage']['families_with_completed_evidence']} of {result['research_family_coverage']['family_count']} identified families. This includes component executions and one related distinct model; it does not mean that every study or apparatus was reproduced. Shared circuits support multiple families, so family counts are not independent experiment counts.",'',
              'Every job keeps its immutable plan, exact submitted ISA QPY, raw counts, metrics, physical measurement mapping and calibration controls. Current per-run analysis paths and hashes are listed in [results.json](results.json). Statistical intervals are marginal shot-based intervals; full-Z TV has an explicit finite-shot sampling benchmark. Secondary readout inversion assumes independent stationary errors and uses biased nonnegative projection, with no confidence-interval claim.','',
              '| Run | Science / calibration circuits | Shots per circuit | QPU seconds | Job ID |','|---|---:|---:|---:|---|']
    for r in result['runs']:
        lines.append(f"| {r['id']} | {r['science_circuits']} / {r['calibration_circuits']} | {r['shots_per_pub']} | {r['actual_quantum_seconds']:g} | `{r['job_id']}` |")
    lines += ['', 'IBM job retrieval requires appropriate access through the [Workloads portal](https://quantum.cloud.ibm.com/workloads); the [official retrieval documentation](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/save-jobs) explains job IDs. Local evidence remains available without a live connection.','']
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=HERE/'results.json')
    parser.add_argument('--markdown',type=Path,default=HERE/'RESULTS.md');parser.add_argument('--allow-incomplete',action='store_true');parser.add_argument('--preview',action='store_true')
    args=parser.parse_args();result=build(args.allow_incomplete)
    if args.preview:
        print(json.dumps({k:result[k] for k in ('status','jobs','science_circuit_executions','calibration_circuit_executions','total_shots','actual_campaign_quantum_seconds','missing_runs')},indent=2))
    else:
        if args.output.exists() or args.markdown.exists():raise FileExistsError('Choose new summary/report paths; preserve previous evidence')
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
        args.markdown.write_text(report(result),encoding='utf8')
        print(json.dumps({'summary':str(args.output),'report':str(args.markdown),'jobs':result['jobs']},indent=2))
