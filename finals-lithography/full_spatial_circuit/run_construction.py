"""Bounded construction and serialization audit; never simulate 219/389 qubits."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import gc
import json
import math
import multiprocessing as mp
from pathlib import Path
import platform
import time
import numpy as np
import psutil
import scipy
import qiskit
from qiskit import QuantumCircuit,transpile,qpy
from circuit_model import (cell_preparation,make_circuit,layout,arithmetic_resource_counts)
from process_bounds import integer_weights,bounds

ROOT=Path(__file__).resolve().parent


def semantic_key(op):
    params=tuple(float(p).hex() for p in op.params)
    return (op.name,op.num_qubits,params)


def circuit_signature(qc):
    """Canonical recursive wiring/operation signature, with cached subroutines.

    Built-in controlled RY and MCX are identified by their exact operation
    semantics. User-defined Toffoli-chain subroutines include their full body.
    No large unitary or statevector is formed.
    """
    cache={}
    def operation(op):
        key=semantic_key(op)
        if key in cache:return cache[key]
        if op.name in ('x','h','ry','cx','ccx','u','rz','p','t','tdg'):
            value=key
        elif getattr(getattr(op,'base_gate',None),'name',None)=='ry':
            value=('controlled_ry',op.num_ctrl_qubits,op.ctrl_state,tuple(float(p).hex() for p in op.params))
        elif op.name=='mcx':value=('mcx',op.num_ctrl_qubits,op.ctrl_state)
        else:
            if op.definition is None:raise ValueError(f'unknown opaque operation {op.name}')
            value=(key,body(op.definition))
        digest=hashlib.sha256(repr(value).encode()).hexdigest();cache[key]=digest
        return digest
    def body(circuit):
        return (circuit.num_qubits,float(circuit.global_phase).hex(),
                tuple((operation(i.operation),tuple(circuit.find_bit(q).index for q in i.qubits)) for i in circuit.data))
    return hashlib.sha256(repr(body(qc)).encode()).hexdigest()


def hierarchical_counts(qc):
    cache={}
    def operation(op):
        key=semantic_key(op)
        if key in cache:return cache[key]
        if op.name in ('x','h','ry','cx','ccx','u','rz','p','t','tdg'):result=Counter({op.name:1})
        elif getattr(getattr(op,'base_gate',None),'name',None)=='ry':result=Counter({f'controlled_ry_{op.num_ctrl_qubits}':1})
        elif op.name=='mcx':result=Counter({f'abstract_mcx_{op.num_ctrl_qubits}':1})
        else:
            if op.definition is None:raise ValueError(op.name)
            result=Counter()
            for inst in op.definition.data:result.update(operation(inst.operation))
        cache[key]=result
        return result
    result=Counter()
    for inst in qc.data:result.update(operation(inst.operation))
    return dict(sorted(result.items()))


def worker(kind,params,queue):
    try:
        start=time.monotonic()
        if kind=='components':
            prep=transpile(cell_preparation(1.5),basis_gates=['u','cx'],optimization_level=1,seed_transpiler=13)
            ccx=QuantumCircuit(3);ccx.ccx(0,1,2)
            ccx=transpile(ccx,basis_gates=['u','cx'],optimization_level=0)
            result={'cell_preparation':{'qubits':4,'counts':dict(prep.count_ops()),'depth':prep.depth()},
                    'exact_ccx_decomposition':{'qubits':3,'counts':dict(ccx.count_ops()),'depth':ccx.depth()},
                    'scope':'Only 4-qubit preparation and 3-qubit CCX compiled. Full circuit not transpiled.'}
        elif kind=='circuit':
            name,weights,style=params
            circuit=make_circuit(weights,style=style)
            signature=circuit_signature(circuit);counts=hierarchical_counts(circuit)
            path=ROOT/f'{name}_{style}_{circuit.num_qubits}q.qpy'
            partial=path.with_suffix('.qpy.partial')
            metadata=dict(circuit.metadata);nqubits=circuit.num_qubits;top_count=len(circuit.data)
            print(f'  {name}/{style}: constructed; serializing',flush=True)
            try:
                with partial.open('wb') as f:qpy.dump(circuit,f)
                # Do not retain both large graphs during readback.
                del circuit;gc.collect()
                print(f'  {name}/{style}: loading with original graph released',flush=True)
                with partial.open('rb') as f:restored=qpy.load(f)[0]
            except Exception as exc:
                if style=='compact' and 'at most 31' in str(exc):
                    queue.put({'status':'constructed_qpy_unsupported','constructed':True,
                               'error':f'{type(exc).__name__}: {exc}',
                               'qubits':nqubits,'metadata':metadata,'top_level_instruction_count':top_count,
                               'recursive_operation_counts':counts,'signature_before':signature,
                               'qpy_round_trip':'unsupported by installed QPY control-count representation',
                               'partial_file_not_a_valid_artifact':partial.name,'seconds':time.monotonic()-start})
                    return
                raise
            signature_after=circuit_signature(restored)
            if signature!=signature_after or counts!=hierarchical_counts(restored) or metadata!=restored.metadata:
                raise RuntimeError('QPY structural/wiring/metadata round-trip failed')
            partial.replace(path)
            result={'weight_rounding':name,'style':style,'qubits':nqubits,'constructed':True,
                    'metadata':metadata,'top_level_instruction_count':top_count,
                    'recursive_operation_counts':counts,'signature_before':signature,
                    'signature_after':signature_after,'qpy_round_trip':'passed',
                    'qpy_file':path.name,'qpy_bytes':path.stat().st_size,
                    'qpy_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        else:raise ValueError(kind)
        queue.put({'status':'completed','seconds':time.monotonic()-start,**result})
    except Exception as exc:queue.put({'status':'failed','error':f'{type(exc).__name__}: {exc}'})


def bounded(kind,params,timeout=120,rss_limit_mb=1536):
    available=psutil.virtual_memory().available/2**20
    if available<4*rss_limit_mb:
        return {'status':'insufficient_available_memory_for_guard','available_system_memory_mb':available,
                'requested_guard_rss_limit_mb':rss_limit_mb}
    ctx=mp.get_context('spawn');queue=ctx.Queue();process=ctx.Process(target=worker,args=(kind,params,queue))
    process.start();start=time.monotonic();peak=0.;reason=None
    monitored=psutil.Process(process.pid)
    while process.is_alive():
        try:peak=max(peak,monitored.memory_info().rss/2**20)
        except psutil.NoSuchProcess:pass
        if peak>rss_limit_mb:reason='memory_guard';break
        if time.monotonic()-start>timeout:reason='timeout';break
        process.join(.05)
    if reason:
        process.terminate();process.join()
        value={'status':reason}
    elif process.exitcode:
        value={'status':'process_failed','exit_code':process.exitcode}
    else:value=queue.get(timeout=3)
    queue.close()
    value.update({'guard_timeout_seconds':timeout,'guard_rss_limit_mb':rss_limit_mb,
                  'preflight_available_system_memory_mb':available,
                  'observed_peak_worker_rss_mb':peak,
                  'memory_guard_note':'RSS sampled every50ms; termination guard, not an OS hard limit; transient overshoot is possible.'})
    return value


def run(output):
    real,weights=integer_weights()
    result={'schema':'full-spatial-construction-v1',
            'scope':'Full original7x7 independent Poisson blur/ROI process, approximated by capped counts and bounded positive lattice weights. Actual circuits constructed and serialized; no full statevector, density simulation, hardware or device claim.',
            'configuration':{'cells':49,'grid':[7,7],'dose_for_saved_circuits':1.5,'count_bits':4,'cap':15,
                             'response_threshold':.8,'threshold_bits':18,'integer_threshold':2**18,
                             'real_weights':real.reshape(7,7).tolist(),
                             'integer_weights':{k:v.reshape(7,7).tolist() for k,v in weights.items()}},
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                        'qiskit':qiskit.__version__,'qpy_version':qpy.QPY_VERSION},
            'bounds':[],'circuits':[],
            'component_compilation':None,'explicit_synthesis_costs':{}}
    def save():output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for rate in (1.5,1.8):
        print(f'Finite process/CDF bounds dose={rate}',flush=True)
        result['bounds'].append(bounds(rate));save()
    print('Bounded small-component compilation',flush=True)
    components=bounded('components',None,timeout=30,rss_limit_mb=768)
    result['component_compilation']=components;save()
    if components['status']!='completed':raise RuntimeError('required small-component compilation unavailable')
    for name,w in weights.items():
        for style in ('compact','clean'):
            print(f'Construct / QPY round-trip: {name}, {style}',flush=True)
            row=bounded('circuit',(name,w.tolist(),style));row.update({'weight_rounding':name,'style':style})
            result['circuits'].append(row);save()
            print(row['status'],flush=True)
        count=arithmetic_resource_counts(w)
        clean=next(r for r in result['circuits'] if r['weight_rounding']==name and r['style']=='clean')
        if clean['status']=='completed':
            actual=clean['recursive_operation_counts']
            assert actual['ccx']==count['oracle_exact_ccx']+count['diffuser_exact_ccx']
            assert actual['cx']==count['oracle_direct_cx']
            prep=components['cell_preparation']['counts'];ccx=components['exact_ccx_decomposition']['counts']
            cx=actual['cx']+actual['ccx']*ccx['cx']+3*49*prep.get('cx',0)
            # All raw preparation X/H/controlled-RY instructions are already
            # included in the compiled cell cost. Add only non-prep X/H here.
            one=(count['mark_single_qubit_x']+count['mark_single_qubit_h']+
                 count['diffuser_single_qubit_x']+count['diffuser_single_qubit_h']+
                 actual['ccx']*ccx['u']+3*49*prep.get('u',0))
            result['explicit_synthesis_costs'][name]={**count,
                'complete_one_round_generic_cx_constructive_upper_bound':cx,
                'complete_one_round_generic_u_constructive_upper_bound':one,
                'preparation_calls':2,'inverse_preparation_calls':1,'cells_prepared_per_call':49,
                'justification':'Concatenate actual4-qubit preparation synthesis, exact6-CX Toffolis in the explicit clean circuit, and nativeCX/single-qubit gates. A constructive unoptimized upper bound, not full transpilation or a lower bound.',
                'omits':'Physical routing, scheduling, angle approximation, calibration, fault tolerance, noise, measurement latency.'}
        save()
    result['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                            for name in ('circuit_model.py','process_bounds.py','run_construction.py')}
    imported=[ROOT.parent/'spatial_model.py',ROOT.parent/'followup'/'spatial_coverage.py']
    result['imported_frozen_source_sha256']={str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in imported}
    result['all_constructions_completed']=all(r.get('constructed',False) for r in result['circuits'])
    result['all_explicit_qpy_roundtrips_completed']=all(r['status']=='completed' for r in result['circuits'] if r['style']=='clean')
    result['all_qpy_roundtrips_completed']=all(r['status']=='completed' for r in result['circuits'])
    save()
    print(json.dumps({'all_constructions_completed':result['all_constructions_completed'],
                      'synthesis':{k:v['complete_one_round_generic_cx_constructive_upper_bound'] for k,v in result['explicit_synthesis_costs'].items()}}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'results.json')
    a=p.parse_args()
    if a.output.exists():p.error('output exists; select a new filename')
    run(a.output)
