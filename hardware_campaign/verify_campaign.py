"""Verify saved real-job provenance and raw results without cloud access."""
from pathlib import Path
import json
import math
from campaign import verify_plan,digest,HERE

def main():
    rows=[]
    for path in sorted((HERE/'runs').glob('*/raw.json')):
        dest=path.parent;plan=verify_plan(dest)
        raw=json.loads(path.read_text());job=json.loads((dest/'job.json').read_text())
        intent=json.loads((dest/'submission_intent.json').read_text())
        assert raw['status']=='DONE' and raw['submitted_dry_run'] is False
        assert plan['dry_run'] is False and plan['simulator'] is False and plan['plan']=='open'
        assert raw['backend']==plan['backend'] and raw['backend'].startswith('ibm_')
        assert raw['job_id']==job['job_id']
        assert raw['plan_sha256']==intent['plan_sha256']==digest(dest/'plan.json')
        assert len(raw['rows'])==len(plan['pubs'])
        charge=raw['metrics']['usage']['qpu_charge_time_seconds']
        assert math.isfinite(charge) and charge>0
        for expected,observed in zip(plan['pubs'],raw['rows']):
            for key,value in expected.items():assert observed[key]==value,(dest.name,key)
            assert observed['shots']==plan['shots']==sum(observed['counts'].values())
            assert all(isinstance(n,int) and n>=0 for n in observed['counts'].values())
            width=len(observed['measurement_physical_qubits'])
            assert all(len(bits)==width and set(bits)<=set('01') for bits in observed['counts'])
        rows.append(dict(label=dest.name,job_id=raw['job_id'],backend=raw['backend'],pubs=len(raw['rows']),
             science_circuits=sum(r['kind']=='science' for r in raw['rows']),
             shots=sum(r['shots'] for r in raw['rows']),qpu_seconds=charge,raw_sha256=digest(path),
             plan_sha256=digest(dest/'plan.json')))
    assert rows,'No real hardware results found'
    print(json.dumps(dict(all_checks_passed=True,real_jobs=len(rows),
         science_circuit_executions=sum(r['science_circuits'] for r in rows),
         total_shots=sum(r['shots'] for r in rows),qpu_seconds=sum(r['qpu_seconds'] for r in rows),runs=rows),indent=2))

if __name__=='__main__':main()
