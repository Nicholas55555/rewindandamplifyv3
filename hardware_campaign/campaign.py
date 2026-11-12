"""Auditable, idempotent IBM Open Plan execution of frozen logical bundles.

No credentials enter artifacts. Prepare is read-only on the cloud; submit is
explicit and writes an exclusive intent before the API call. An unresolved
intent is reconciled by unique remote tag and is never blindly resubmitted.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import uuid
import math
import shutil
import gzip
from contextlib import contextmanager
import numpy as np
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, qpy
from qiskit.quantum_info import Statevector
from qiskit.transpiler import generate_preset_pass_manager

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'rewindandamplify-main'))
from qrsm_grover.hardware import without_qubits

def now(): return datetime.now(timezone.utc).isoformat()
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj):
    path=Path(path); temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,indent=2,default=lambda v: v.item() if isinstance(v,np.generic) else str(v))+'\n',encoding='utf-8')
    temp.replace(path)
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def save_qpy(path,circuits):
    with Path(path).open('wb') as f: qpy.dump(circuits,f)
def load_qpy(path):
    path=Path(path)
    with (gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')) as f: return qpy.load(f)

def compiled_path(dest,plan):return dest/plan.get('compiled_qpy_file','isa.qpy')

def verify_bundle(bundle,manifest):
    checked={}
    def check(filename,expected,source=False):
        candidates=[ROOT/filename,bundle.parent/filename,bundle/filename] if source else [bundle/filename]
        matches=[p for p in candidates if p.is_file() and digest(p)==expected]
        if not matches:raise RuntimeError(f'Frozen bundle hash mismatch: {filename}')
        checked[str(matches[0].resolve().relative_to(ROOT)).replace('\\','/')]=expected
    def walk(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k in ['source_sha256','artifact_sha256'] and isinstance(v,dict):
                    for filename,h in v.items():check(filename,h,k=='source_sha256')
                elif k=='source_sha256' and isinstance(v,str) and 'source_results' in obj:
                    check(obj['source_results'],v,True)
                elif k.endswith('_sha256') and k[:-7] in ['logical.qpy','ideal_probabilities.npz']:
                    check(k[:-7],v)
                else:walk(v)
        elif isinstance(obj,list):
            for v in obj:walk(v)
    walk(manifest)
    return checked

@contextmanager
def submission_lock():
    path=HERE/'submission.lock'
    with path.open('x',encoding='utf-8') as f:f.write(now())
    try:yield
    finally:path.unlink()

def service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    srv=QiskitRuntimeService(plans_preference=['open'])
    account=srv.active_account()
    if account.get('is_local') or account.get('channel')!='ibm_quantum_platform':
        raise RuntimeError('Real IBM Quantum Platform account required')
    crn=srv.active_instance()
    instances=srv.instances()
    selected=[x for x in instances if x.get('crn')==crn]
    if len(selected)!=1 or selected[0].get('plan')!='open':
        raise RuntimeError('This campaign is authorized for the Open Plan only')
    return srv

def usage_snapshot(srv):
    raw=srv.usage()
    # Explicit allowlist excludes account/instance identifiers.
    return {k:raw[k] for k in ['usage_consumed_seconds','usage_limit_seconds','usage_remaining_seconds',
             'usage_limit_reached','usage_period'] if k in raw}

def remaining(usage):
    if 'usage_remaining_seconds' in usage: return float(usage['usage_remaining_seconds'])
    if 'usage_limit_seconds' in usage and 'usage_consumed_seconds' in usage:
        return float(usage['usage_limit_seconds'])-float(usage['usage_consumed_seconds'])
    raise RuntimeError('No authoritative remaining quota in usage response')

def path_layout(target,width):
    """Prespecified beam search for a low-error connected path, no outcome fitting."""
    edges={i:set() for i in range(target.num_qubits)}; cost={}
    for gate in ['cz','ecr','cx']:
        if gate not in target.operation_names: continue
        for pair,prop in target[gate].items():
            if pair is None or len(pair)!=2: continue
            a,b=pair; edges[a].add(b);edges[b].add(a)
            cost[a,b]=cost[b,a]=float(prop.error if prop and prop.error is not None else .05)
    def ro(q):
        p=target['measure'].get((q,))
        return float(p.error if p and p.error is not None else .05)
    beam=sorted((ro(q),(q,)) for q in edges if edges[q])[:1024]
    for _ in range(1,width):
        choices=[]
        for score,path in beam:
            for q in edges[path[-1]]-set(path):
                choices.append((score+ro(q)+4*cost[path[-1],q],path+(q,)))
        beam=sorted(choices)[:1024]
        if not beam: raise RuntimeError('No connected physical path of requested width')
    return list(beam[0][1])

def measurement_map(qc):
    result={}
    measured_qubits=set()
    for inst in qc.data:
        operands={qc.find_bit(q).index for q in inst.qubits}
        if inst.operation.name=='measure':
            bit=qc.find_bit(inst.clbits[0]).index
            if bit in result:raise ValueError('Repeated classical measurement')
            if operands & measured_qubits:raise ValueError('Repeated qubit measurement')
            measured_qubits.update(operands)
            result[bit]=qc.find_bit(inst.qubits[0]).index
        elif inst.operation.name!='barrier' and (operands & measured_qubits or inst.clbits or getattr(inst.operation,'condition',None)):
            raise ValueError('Only terminal measurements are supported')
    if set(result)!=set(range(qc.num_clbits)): raise ValueError('Every classical bit must be measured once')
    return [result[i] for i in range(qc.num_clbits)]

def compact(qc):
    used=sorted({qc.find_bit(q).index for x in qc.data if x.operation.name!='barrier' for q in x.qubits})
    out=QuantumCircuit(len(used))
    for reg in qc.cregs: out.add_register(ClassicalRegister(reg.size,reg.name))
    index={q:i for i,q in enumerate(used)}
    for inst in qc.data:
        if inst.operation.name=='barrier': continue
        out.append(inst.operation,[index[qc.find_bit(q).index] for q in inst.qubits],
                   [qc.find_bit(c).index for c in inst.clbits])
    return out

def measured_probabilities(qc):
    p=Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities()
    wires=measurement_map(qc)
    indices=np.arange(len(p),dtype=np.uint64)
    dest=np.zeros(len(p),dtype=np.int64)
    for bit,q in enumerate(wires): dest |= (((indices>>q)&1).astype(np.int64)<<bit)
    return np.bincount(dest,weights=p,minlength=2**len(wires))

def probability_marginal(p,bits):
    indices=np.arange(len(p),dtype=np.uint64);dest=np.zeros(len(p),dtype=np.int64)
    for j,bit in enumerate(bits):dest |= (((indices>>bit)&1).astype(np.int64)<<j)
    return np.bincount(dest,weights=p,minlength=2**len(bits))

def duration_bound(qc,target):
    """Critical path of calibrated instruction durations; excludes service overhead."""
    clocks=[0.0]*qc.num_qubits
    for inst in qc.data:
        qs=[qc.find_bit(q).index for q in inst.qubits]
        if not qs: continue
        if inst.operation.name=='barrier': duration=0
        elif inst.operation.name=='delay':
            if inst.operation.unit!='dt': raise ValueError('Unexpected delay unit')
            duration=inst.operation.duration*target.dt
        else:
            prop=target[inst.operation.name].get(tuple(qs))
            if prop is None or prop.duration is None:
                if inst.operation.name not in ['rz','id']: raise ValueError(f'Missing duration: {inst.operation.name}, {qs}')
                duration=0
            else: duration=float(prop.duration)
        end=max(clocks[q] for q in qs)+duration
        for q in qs: clocks[q]=end
    return max(clocks)

def ref_key(row):
    if 'ideal_probability_key' in row: return row['ideal_probability_key']
    if 'ideal_z_probabilities_npz_key' in row: return row['ideal_z_probabilities_npz_key']
    ref=row.get('reference',{})
    for k in ['key','npz_key','full_z_probabilities_key']:
        if k in ref:return ref[k]
    raise ValueError(f'No reference key for {row["name"]}')

def prepare(args):
    dest=HERE/'runs'/args.label
    if dest.exists(): raise RuntimeError('Run path already exists; use immutable plans')
    bundle=Path(args.bundle).resolve(); manifest=read(bundle/'manifest.json')
    checked_sources=verify_bundle(bundle,manifest)
    validate_options(args.shots,args.cap,args.mode)
    rows=manifest['circuits']
    wanted=set(args.indices) if args.indices is not None else {r['index'] for r in rows}
    rows=[r for r in rows if r['index'] in wanted]
    if len(rows)!=len(wanted): raise ValueError('Unknown/duplicate selected indices')
    cache={}; logical=[]
    for row in rows:
        filename=row.get('qpy_file',manifest.get('qpy_file',manifest.get('logical_qpy','logical.qpy')))
        if filename not in cache: cache[filename]=load_qpy(bundle/filename)
        logical.append(cache[filename][row['index']])
    refpath=bundle/manifest.get('ideal_probabilities_file',manifest.get('reference_npz','ideal_probabilities.npz'))
    references=np.load(refpath)
    srv=service(); quota=usage_snapshot(srv)
    backend=srv.backend(args.backend)
    config=backend.configuration()
    if getattr(config,'simulator',False) or not backend.status().operational: raise RuntimeError('Real operational backend required')
    width=max(q.num_qubits for q in logical)
    if width>backend.num_qubits: raise RuntimeError('Circuit exceeds backend width')
    patch=path_layout(backend.target,width)
    target=without_qubits(backend.target,set(range(backend.num_qubits))-set(patch))
    rep_delay=float(config.default_rep_delay)
    dest.mkdir(parents=True)
    dump(dest/'backend_properties.json',backend.properties().to_dict())
    compiled=[]; records=[]
    for row,qc in zip(rows,logical):
        pm=generate_preset_pass_manager(target=target,optimization_level=3,seed_transpiler=20261111,initial_layout=patch[:qc.num_qubits])
        isa=pm.run(qc)
        mapping=measurement_map(isa)
        # Check each native operation is supported on its actual physical operands.
        for inst in isa.data:
            if inst.operation.name in ['barrier','delay']:continue
            operands=tuple(isa.find_bit(q).index for q in inst.qubits)
            if not backend.target.instruction_supported(operation_name=inst.operation.name,qargs=operands):
                raise ValueError('Non-ISA instruction')
        key=ref_key(row); expected=references[key]
        marginal_bits=row.get('reference_marginal_qubits')
        if marginal_bits is not None and (len(set(marginal_bits))!=len(marginal_bits) or any(b<0 or b>=qc.num_clbits for b in marginal_bits)):
            raise ValueError('Invalid reference marginal bit mapping')
        ref_width=qc.num_clbits if marginal_bits is None else len(marginal_bits)
        if expected.shape != (2**ref_width,) or not np.all(np.isfinite(expected)) or np.min(expected)<-1e-12 or abs(expected.sum()-1)>1e-8:raise ValueError('Invalid ideal reference')
        validation={'logical_qpy_roundtrip':True,'native_isa_checked':True}
        if ((qc.num_qubits<=12 and sum(isa.count_ops().values())<12000)
            or (qc.num_qubits<=18 and sum(isa.count_ops().values())<2000)):
            p=measured_probabilities(compact(isa))
            if marginal_bits is not None:p=probability_marginal(p,marginal_bits)
            err=float(np.max(np.abs(p-expected)))
            if err>1e-8:raise ValueError(f'Compiled reference mismatch: {err}')
            validation['compiled_probability_max_error']=err
        else:validation['compiled_statevector']='not run; logical exact reference and native instruction/wire checks retained'
        record=dict(kind='science',name=row['name'],bundle_index=row['index'],logical_qubits=qc.num_qubits,
                    reference_marginal_qubits=marginal_bits,
                    measurement_physical_qubits=mapping,initial_layout=patch[:qc.num_qubits],
                    gate_counts=dict(isa.count_ops()),depth=isa.depth(),duration_seconds=duration_bound(isa,backend.target),validation=validation)
        compiled.append(isa);records.append(record)
        print(json.dumps({'prepared':row['name'],'two_qubit':sum(v for k,v in isa.count_ops().items() if k in ['cz','cx','ecr']),'duration_s':record['duration_seconds']}),flush=True)
    # Independent SPAM calibration and two correlation diagnostics on the common patch.
    for name,bits in [('zero',[0]*width),('one',[1]*width),('alternating',[i%2 for i in range(width)]),('complement',[1-i%2 for i in range(width)])]:
        q=QuantumCircuit(QuantumRegister(width,'q'),ClassicalRegister(width,'meas'),name='cal_'+name)
        for i,b in enumerate(bits):
            if b:q.x(i)
        q.measure(range(width),range(width))
        isa=generate_preset_pass_manager(target=target,optimization_level=1,initial_layout=patch,seed_transpiler=20261111).run(q)
        compiled.append(isa);records.append(dict(kind='calibration',name='cal_'+name,prepared_bits=bits,
              measurement_physical_qubits=measurement_map(isa),duration_seconds=duration_bound(isa,backend.target)))
    order=list(range(len(compiled)));random.Random(20261111).shuffle(order)
    compiled=[compiled[i] for i in order];records=[records[i] for i in order]
    for i,row in enumerate(records):row['pub_index']=i
    save_qpy(dest/'isa.qpy',compiled)
    reloaded=load_qpy(dest/'isa.qpy')
    if any(a!=b for a,b in zip(compiled,reloaded)):raise ValueError('Compiled QPY roundtrip mismatch')
    estimate=sum(args.shots*(r['duration_seconds']+rep_delay) for r in records)
    plan=dict(schema='ra-real-hardware-plan-v1',created_utc=now(),label=args.label,backend=backend.name,
        simulator=False,dry_run=False,plan='open',bundle=str(bundle.relative_to(ROOT)).replace('\\','/'),
        manifest_sha256=digest(bundle/'manifest.json'),reference_sha256=digest(refpath),reference_file=refpath.name,
        checked_bundle_hashes=checked_sources,
        logical_qpy_sha256={p:digest(bundle/p) for p in cache},compiled_qpy_sha256=digest(dest/'isa.qpy'),
        shots=args.shots,max_execution_time=args.cap,mode=args.mode,physical_patch=patch,
        transpiler_seed=20261111,pub_order_seed=20261111,rep_delay_seconds=rep_delay,
        duration_estimate_seconds=estimate,duration_estimate_caveat='Calibrated critical path plus repetition delay; excludes service overhead and DD/twirling expansion. Cap is authoritative.',
        quota_at_prepare=quota,pubs=records)
    if estimate>args.cap*.8:raise RuntimeError(f'Estimated {estimate:.2f}s too close to cap; prepared artifacts retained, no submitted job')
    dump(dest/'plan.json',plan)
    print(json.dumps({'plan':str(dest),'pubs':len(records),'patch':patch,'estimate_seconds':estimate,'quota':quota}))

def verify_plan(dest):
    plan=read(dest/'plan.json'); bundle=ROOT/plan['bundle']
    checks=[(compiled_path(dest,plan),plan['compiled_qpy_sha256']),(bundle/'manifest.json',plan['manifest_sha256'])]
    checks += [(bundle/f,h) for f,h in plan['logical_qpy_sha256'].items()]
    checks.append((bundle/plan.get('reference_file','ideal_probabilities.npz'),plan['reference_sha256']))
    verify_bundle(bundle,read(bundle/'manifest.json'))
    for path,h in checks:
        if digest(path)!=h:raise RuntimeError(f'Immutable artifact changed: {path.name}')
    return plan

def terminal(status):return str(status).upper() in ['DONE','ERROR','CANCELLED']

def quota_guard(available,cap,reserved):
    if not all(math.isfinite(x) and x>=0 for x in [available,cap,reserved]):
        raise RuntimeError('Quota values must be finite and nonnegative')
    if cap<=0 or cap+reserved+5>available:
        raise RuntimeError(f'Quota guard: available={available}, cap={cap}, reserved={reserved}; 5s buffer required')

def validate_options(shots,cap,mode):
    if not isinstance(shots,int) or shots<=0 or not isinstance(cap,int) or cap<=0:
        raise ValueError('Shots and cap must be positive integers')
    if mode=='suppressed' and shots%32:raise ValueError('Suppressed shots must be a multiple of 32')

def reconcile(srv,intent):
    jobs=srv.jobs(limit=10,job_tags=[intent['unique_tag']])
    if len(jobs)>1:raise RuntimeError('Duplicate remote tags; manual audit required')
    return jobs[0] if jobs else None

def submit_locked(args):
    dest=HERE/'runs'/args.label;plan=verify_plan(dest)
    validate_options(plan['shots'],plan['max_execution_time'],plan['mode'])
    srv=service()
    if (dest/'job.json').exists():
        print(json.dumps({'already_submitted':read(dest/'job.json')['job_id']}));return
    intent_path=dest/'submission_intent.json'
    if intent_path.exists():
        intent=read(intent_path)
        if intent['plan_sha256']!=digest(dest/'plan.json'):raise RuntimeError('Plan changed after intent')
        job=reconcile(srv,intent)
        if job:
            dump(dest/'job.json',dict(job_id=job.job_id(),reconciled_utc=now(),unique_tag=intent['unique_tag']))
            print(json.dumps({'reconciled_job_id':job.job_id()}));return
        raise RuntimeError('Unresolved prior intent; no blind resubmission. Inspect remote job list before any new plan.')
    quota=usage_snapshot(srv);reserved=0
    if quota.get('usage_limit_reached'):raise RuntimeError('Open Plan usage limit reached')
    for path in (HERE/'runs').glob('*/submission_intent.json'):
        other=path.parent
        if other==dest:continue
        jp=other/'job.json'
        if jp.exists():otherjob=srv.job(read(jp)['job_id'])
        else:otherjob=reconcile(srv,read(path))
        if otherjob is None or not terminal(otherjob.status()):reserved+=read(other/'plan.json')['max_execution_time']
    quota_guard(remaining(quota),plan['max_execution_time'],reserved)
    backend=srv.backend(plan['backend'])
    if getattr(backend.configuration(),'simulator',False):raise RuntimeError('Simulator forbidden')
    circuits=load_qpy(compiled_path(dest,plan))
    if len(circuits)!=len(plan['pubs']):raise ValueError('PUB count mismatch')
    from qiskit_ibm_runtime import SamplerV2
    sampler=SamplerV2(mode=backend)
    sampler.options.max_execution_time=plan['max_execution_time']
    sampler.options.default_shots=plan['shots']
    sampler.options.execution.rep_delay=plan['rep_delay_seconds']
    sampler.options.dynamical_decoupling.enable=plan['mode']=='suppressed'
    if plan['mode']=='suppressed':sampler.options.dynamical_decoupling.sequence_type='XY4'
    sampler.options.twirling.enable_gates=plan['mode']=='suppressed'
    sampler.options.twirling.enable_measure=plan['mode']=='suppressed'
    if plan['mode']=='suppressed':
        sampler.options.twirling.num_randomizations=32
        sampler.options.twirling.shots_per_randomization=plan['shots']//32
    tag='ra26-'+uuid.uuid4().hex[:20]
    sampler.options.environment.job_tags=['rewind-amplify-2026',tag,args.label]
    intent=dict(created_utc=now(),unique_tag=tag,plan_sha256=digest(dest/'plan.json'),quota_before=quota,
                reserved_other_jobs_seconds=reserved,real_hardware=True,dry_run=False)
    with intent_path.open('x',encoding='utf-8') as f:json.dump(intent,f,indent=2)
    job=sampler.run(circuits,shots=plan['shots'],dry_run=False)
    dump(dest/'job.json',dict(job_id=job.job_id(),submitted_utc=now(),unique_tag=tag))
    print(json.dumps({'job_id':job.job_id(),'label':args.label,'status':job.status(),'quota_before':quota}),flush=True)

def submit(args):
    with submission_lock():submit_locked(args)

def clone_plan(args):
    source=HERE/'runs'/args.source;dest=HERE/'runs'/args.label
    plan=verify_plan(source)
    if dest.exists():raise RuntimeError('Immutable plan already exists')
    validate_options(args.shots or plan['shots'],args.cap or plan['max_execution_time'],args.mode)
    dest.mkdir()
    source_qpy=compiled_path(source,plan)
    if source_qpy.stat().st_size>45*1024**2 and source_qpy.suffix!='.gz':
        with source_qpy.open('rb') as inp, gzip.open(dest/'isa.qpy.gz','wb') as out:shutil.copyfileobj(inp,out)
        plan['compiled_qpy_file']='isa.qpy.gz'
        plan['compiled_uncompressed_sha256']=plan['compiled_qpy_sha256']
        plan['compiled_qpy_sha256']=digest(dest/'isa.qpy.gz')
    else:shutil.copyfile(source_qpy,dest/source_qpy.name)
    shutil.copyfile(source/'backend_properties.json',dest/'backend_properties.json')
    previous_shots=plan['shots']
    if args.names:
        wanted=set(args.names)
        science={r['name'] for r in plan['pubs'] if r['kind']=='science'}
        if not wanted<=science:raise ValueError('Unknown selected circuit name')
        circuits=load_qpy(compiled_path(dest,plan))
        keep=[i for i,r in enumerate(plan['pubs']) if r['kind']=='calibration' or r['name'] in wanted]
        selected=[circuits[i] for i in keep]
        plan['pubs']=[plan['pubs'][i] for i in keep]
        for i,r in enumerate(plan['pubs']):r['pub_index']=i
        save_qpy(dest/'selected_isa.qpy',selected)
        plan['compiled_qpy_file']='selected_isa.qpy'
        plan['compiled_qpy_sha256']=digest(dest/'selected_isa.qpy')
        plan['selection_names']=args.names
        plan['duration_estimate_seconds']=previous_shots*sum(r['duration_seconds']+plan['rep_delay_seconds'] for r in plan['pubs'])
    plan.update(label=args.label,created_utc=now(),mode=args.mode,shots=args.shots or previous_shots,
                max_execution_time=args.cap or plan['max_execution_time'],paired_source_plan=args.source,
                paired_source_plan_sha256=digest(source/'plan.json'))
    plan['duration_estimate_seconds']*=plan['shots']/previous_shots
    if plan['duration_estimate_seconds']>plan['max_execution_time']*.8:raise RuntimeError('Cap too close to estimate')
    dump(dest/'plan.json',plan)
    print(json.dumps({'cloned':args.label,'exact_same_isa_as':args.source,'mode':args.mode}))

def fetch(args):
    dest=HERE/'runs'/args.label;plan=verify_plan(dest);jp=dest/'job.json'
    if not jp.exists():raise RuntimeError('No confirmed job ID')
    srv=service();job=srv.job(read(jp)['job_id']);status=str(job.status())
    report=dict(checked_utc=now(),job_id=job.job_id(),status=status,quota=usage_snapshot(srv))
    dump(dest/'status.json',report)
    print(json.dumps(report),flush=True)
    if status.upper()!='DONE':return
    if (dest/'raw.json').exists():print('Raw result already saved');return
    result=job.result();rows=[]
    if len(result)!=len(plan['pubs']):raise RuntimeError('Returned PUB count mismatch')
    for desc,pub in zip(plan['pubs'],result):
        counts=pub.data.meas.get_counts()
        if sum(counts.values())!=plan['shots']:raise RuntimeError('Unexpected shot count')
        rows.append(dict(**desc,shots=sum(counts.values()),counts=counts,runtime_metadata=pub.metadata))
    jb=job.backend(); actual_backend=jb.name
    if actual_backend!=plan['backend'] or getattr(jb.configuration(),'simulator',False):raise RuntimeError('Wrong backend')
    metrics=job.metrics()
    dump(dest/'raw.json',dict(schema='ra-ibm-real-results-v1',retrieved_utc=now(),job_id=job.job_id(),
         backend=actual_backend,status=status,submitted_dry_run=False,plan_sha256=digest(dest/'plan.json'),
         metrics=metrics,usage=job.usage(),primitive_metadata=result.metadata,rows=rows))
    print(json.dumps({'saved_rows':len(rows),'job_id':job.job_id(),'metrics':metrics}),flush=True)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--bundle',required=True);a.add_argument('--label',required=True)
    a.add_argument('--backend',default='ibm_marrakesh');a.add_argument('--shots',type=int,default=2048)
    a.add_argument('--cap',type=int,default=90);a.add_argument('--mode',choices=['plain','suppressed'],default='plain')
    a.add_argument('--indices',type=int,nargs='+')
    a=sub.add_parser('clone');a.add_argument('--source',required=True);a.add_argument('--label',required=True)
    a.add_argument('--mode',choices=['plain','suppressed'],required=True);a.add_argument('--shots',type=int);a.add_argument('--cap',type=int)
    a.add_argument('--names',nargs='+')
    for name in ['submit','fetch']:
        sub.add_parser(name).add_argument('--label',required=True)
    args=p.parse_args()
    if Path(args.label).name!=args.label:raise ValueError('Label must be a single directory name')
    if args.command=='prepare':prepare(args)
    elif args.command=='submit':submit(args)
    elif args.command=='clone':clone_plan(args)
    else:fetch(args)

if __name__=='__main__':main()
