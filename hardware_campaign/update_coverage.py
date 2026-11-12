"""Attach completed-job evidence to the audited family ledger, offline only."""
from pathlib import Path
import fnmatch
import json
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def main():
    ledger=json.loads((HERE/'coverage.json').read_text())
    jobs=[]
    for rawpath in sorted((HERE/'runs').glob('*/raw.json')):
        raw=json.loads(rawpath.read_text());plan=json.loads((rawpath.parent/'plan.json').read_text())
        jobs.append((raw,plan,rawpath))
    for family in ledger['families']:
        if family['id']=='dot_joint_instrument':
            family['planned_bundle']=['quantum_dot_bridge/qrsm_hom_followup/hardware_bundle_v2/manifest.json',
                'quantum_dot_bridge/qrsm_hom_followup/exploratory_design/hardware_bundle/manifest.json']
            family['planned_circuit_selectors']=['*']
        family['job_ids']=[];family['completed_evidence']=[]
        bundles=family.get('planned_bundle') or []
        if isinstance(bundles,str):bundles=[bundles]
        selectors=family.get('planned_circuit_selectors',[])
        matches_by_bundle={b:selectors for b in bundles}
        for item in family.get('supplementary_bundles',[]):
            matches_by_bundle[item['manifest']]=item['selectors']
        for raw,plan,path in jobs:
            selected_patterns=matches_by_bundle.get(plan['bundle']+'/manifest.json')
            if selected_patterns is None:continue
            matched=[r for r in raw['rows'] if r['kind']=='science' and any(fnmatch.fnmatchcase(r['name'],s) for s in selected_patterns)]
            if matched:
                family['job_ids'].append(raw['job_id'])
                family['completed_evidence'].append(dict(job_id=raw['job_id'],backend=raw['backend'],
                    raw_path=path.relative_to(ROOT).as_posix(),circuits=[r['name'] for r in matched],
                    shots=sum(r['shots'] for r in matched)))
        if family['job_ids']:
            family['new_hardware_status']=('complete_gate_model_execution' if family['new_hardware_classification']=='planned_full_gate_execution'
                else 'component_executed_full_study_not_replicated')
            if family['id']=='reset_sensor':family['new_hardware_status']='related_distinct_model_executed'
            family['executed_scope']=family['new_hardware_classification'].replace('planned_','executed_')
    ledger['updated_utc']=datetime.now(timezone.utc).isoformat()
    ledger['status']='evidence_updated; consult each family for completed scope and remaining gaps'
    ledger['all_research_replicated']=False
    ledger['completed_job_count']=len(jobs)
    ledger['new_campaign_qpu_seconds']=sum(r['metrics']['usage']['qpu_charge_time_seconds'] for r,_,_ in jobs)
    ledger['job_status_owner']='Counts and IDs derived offline from verified raw results; no full apparatus or inference claim follows from component execution.'
    (HERE/'coverage.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
    lines=['# Research coverage and hardware scope','',
      f'This ledger audits {len(ledger["families"])} research families. **{len(jobs)} real IBM jobs completed**, using {ledger["new_campaign_qpu_seconds"]} quantum seconds. The rows below distinguish complete specified gate-model executions from component-only evidence and unreplicated studies.',
      '', 'The available devices have156qubits; the full219/389-qubit spatial constructions cannot fit. Superconducting circuits emulate the specified models; they do not replace optical, detector or material measurements.',
      '', '| Family | Actual new hardware status | Evidence | Remaining scope and limits |','|---|---|---|---|']
    for f in ledger['families']:
        evidence='; '.join(f'[{e["job_id"]}](../{e["raw_path"]})' for e in f['completed_evidence']) or 'See canonical analysis; no equivalent full hardware execution'
        lines.append(f'| {f["title"]} | {f["new_hardware_status"].replace("_"," ")} | {evidence} | {"; ".join(f["remaining_work"])} |')
    lines += ['', 'The machine-readable [coverage.json](coverage.json) retains canonical paths, circuit selectors, actual matched rows, shot counts and unresolved local research. A fixed-round circuit does not execute an adaptive search policy; a sensor channel does not replicate an online monitoring benchmark. Published optical records remain third-party experiments.', '']
    (HERE/'coverage.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'completed_jobs':len(jobs),'families_with_hardware_evidence':sum(bool(f['job_ids']) for f in ledger['families'])}))

if __name__=='__main__':main()
