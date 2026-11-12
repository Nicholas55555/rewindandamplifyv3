"""Independent arithmetic recount of saved raw results; no cloud or simulations.

The verifier uses sparse integer masks and direct raw-count sums rather than the
analyzer's vector-marginal helpers. It validates the current summary's provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]


def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    summary_path=ROOT/'hardware_campaign/results.json';summary=read(summary_path)
    assert summary['status']=='complete' and summary['jobs']==10
    for name,h in summary['source_sha256'].items():assert sha(ROOT/name)==h,name
    for name,h in summary['input_sha256'].items():assert sha(ROOT/name)==h,name
    total_shots=total_science=total_cal=total_usage=0;maximum_tv_error=0.;event_checks=dot_checks=0
    for run in summary['runs']:
        raw=read(ROOT/run['raw_path']);plan=read(ROOT/run['plan_path']);analysis=read(ROOT/run['analysis_path'])
        bundle=ROOT/plan['bundle'];manifest=read(bundle/'manifest.json');specs={r['index']:r for r in manifest['circuits']}
        analyzed={r['pub_index']:r for r in analysis['rows']}
        for name,h in analysis['source_sha256'].items():assert sha(ROOT/name)==h,name
        assert raw['job_id']==run['job_id'] and raw['backend']==run['backend']
        total_usage+=raw['usage']
        with np.load(bundle/plan.get('reference_file','ideal_probabilities.npz'),allow_pickle=False) as refs:
            for row in raw['rows']:
                counts={int(k.replace(' ',''),2):v for k,v in row['counts'].items()};shots=sum(counts.values())
                assert shots==row['shots']==plan['shots'];total_shots+=shots
                if row['kind']=='calibration':
                    total_cal+=1
                    if row['name'] in ('cal_zero','cal_one'):
                        which='e01' if row['name']=='cal_zero' else 'e10'
                        for bit,physical in enumerate(row['measurement_physical_qubits']):
                            k=sum(v for index,v in counts.items() if ((index>>bit)&1)==(1 if which=='e01' else 0))
                            estimated=analysis['calibration']['independent_bit_error_estimates'][str(physical)][which]
                            assert estimated['successes']==k and estimated['shots']==shots
                    continue
                total_science+=1;out=analyzed[row['pub_index']];spec=specs[row['bundle_index']];meta=spec['metadata']
                key=spec.get('ideal_probability_key',spec.get('ideal_z_probabilities_npz_key',spec.get('reference',{}).get('key')))
                target=refs[key];qubits=spec.get('reference_marginal_qubits')
                projected={}
                for index,n in counts.items():
                    packed=index if qubits is None else sum(((index>>q)&1)<<j for j,q in enumerate(qubits))
                    projected[packed]=projected.get(packed,0)+n
                direct_tv=.5*(sum(abs(n/shots-target[index]) for index,n in projected.items())
                               +target.sum()-sum(target[index] for index in projected))
                keytv='raw_full_z_tv' if qubits is None else 'raw_reference_marginal_z_tv'
                maximum_tv_error=max(maximum_tv_error,abs(direct_tv-out[keytv]));assert abs(direct_tv-out[keytv])<1e-12
                family=meta.get('family',meta.get('kind'));obs=out['observables']
                predicate=None;selected=obs.get('selected')
                if family in ('history','loop'):
                    mapping=spec['reference']['chronological_history_qubits']
                    if family=='loop':step=meta['t0']
                    elif meta['question']=='any click':step=None
                    else:step=int(meta['question'].split()[-1])
                    predicate=(lambda i,m=mapping:any((i>>q)&1 for q in m)) if step is None else (lambda i,q=mapping[step-1]:bool((i>>q)&1))
                    if family=='loop':
                        kept=sum(v for i,v in counts.items() if predicate(i))
                        for future in obs['future_clicks_after_selected_click']:
                            q=mapping[future['step']-1]
                            k=sum(v for i,v in counts.items() if predicate(i) and ((i>>q)&1))
                            stat=future['raw_or_secondary_conditional'];assert stat['shots']==kept and stat['successes']==k
                elif family=='echo':predicate=lambda i:i==0;selected=obs['all_zero_return']
                elif family=='catalog':predicate=lambda i:i==3;selected=obs['top_match']
                elif family=='optical_retained_instrument':
                    flags=meta['measurement']['chronological_flag_qubits']
                    predicate=(lambda i,f=flags:all((i>>q)&1 for q in f)) if meta['event']=='all' else (lambda i,q=flags[-1]:bool((i>>q)&1))
                    selected={'successes':obs['accepted_shots'],'shots':obs['shots']}
                elif family=='correlated_spatial_2x2':
                    predicate=lambda i:sum(w*((i>>(1+2*j))&3) for j,w in enumerate([1,2,2,4]))<3
                    selected={'successes':obs['accepted_shots'],'shots':obs['shots']}
                    dirty=sum(v for i,v in counts.items() if i>>9);assert dirty==obs['dirty_workspace_shots']
                elif family=='independent_contact':
                    mask=(1<<meta['sites'])-1;predicate=lambda i,m=mask:(i&m).bit_count()<2
                elif family in ('catalog_cost_1024','semantic_catalog16'):
                    marks=set(meta['marked_indices'] if family=='catalog_cost_1024' else [meta['target_index']]);predicate=lambda i,m=marks:i in m
                elif family in ('qrsm_fixed_round_history','bounded_rewind'):
                    predicate=lambda i,q=meta['event_qubit']:bool((i>>q)&1)
                if predicate:
                    k=sum(v for i,v in counts.items() if predicate(i));assert selected['successes']==k and selected['shots']==shots
                    event_checks+=1
                if 'flag_qubits' in meta:
                    flags=meta['flag_qubits']
                    for history,value in obs['histories'].items():
                        selected_counts={i:n for i,n in counts.items() if all(((i>>q)&1)==int(b) for q,b in zip(flags,history))}
                        k=sum(selected_counts.values());assert value['observed']['successes']==k
                        if 'conditional_memory_zero' in value:
                            zero=sum(v for i,v in selected_counts.items() if not ((i>>meta['memory_qubit'])&1))
                            assert value['conditional_memory_zero']['successes']==zero
                            assert value['conditional_memory_zero']['shots']==k
                        dot_checks+=1
    assert total_shots==summary['total_shots']==688640
    assert total_science==summary['science_circuit_executions']==207
    assert total_cal==summary['calibration_circuit_executions']==40
    assert total_usage==summary['actual_campaign_quantum_seconds']==244
    return {'schema':'hardware-analysis-delivery-verification-v1','all_checks_passed':True,
            'jobs':10,'science_rows':total_science,'calibration_rows':total_cal,'raw_shots_recounted':total_shots,
            'actual_qpu_seconds_reconciled':total_usage,'event_predicates_recounted':event_checks,
            'dot_history_and_conditional_memory_branches_recounted':dot_checks,
            'maximum_sparse_independent_tv_difference':maximum_tv_error,
            'summary_sha256':sha(summary_path),'report_sha256':sha(ROOT/'hardware_campaign/RESULTS.md'),
            'verifier_sha256':sha(__file__),
            'scope':'Source/artifact parity and independent sparse raw arithmetic. No service calls; no claim of independent experimental replication or full-state fidelity.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--receipt',type=Path)
    args=parser.parse_args();result=verify()
    if args.receipt:
        if args.receipt.exists():raise FileExistsError(args.receipt)
        args.receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
