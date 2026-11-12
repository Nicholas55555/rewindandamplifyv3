"""Construct the original 49-cell model as a finite coherent circuit.

No full-state simulation is performed. The compact circuit contains exact
abstract MCX operations. The explicit implementation uses clean Toffoli chains
with all required ancillas allocated, including the 196-data-qubit diffuser.
"""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import math
import numpy as np
from scipy.stats import poisson
from qiskit import QuantumCircuit
from qiskit.circuit.library import RYGate


def capped_poisson(rate,bits=4):
    if not math.isfinite(rate) or rate<=0 or not isinstance(bits,int) or not 1<=bits<=6:
        raise ValueError('positive finite rate and 1..6 bits required')
    cap=2**bits-1
    return np.r_[poisson.pmf(np.arange(cap),rate),poisson.sf(cap-1,rate)]


def cell_preparation(rate,bits=4):
    """Positive amplitudes from an explicit binary conditional-RY tree."""
    pmf=capped_poisson(rate,bits)
    qc=QuantumCircuit(bits,name=f'poisson_{bits}b_{rate:g}')
    for level in range(bits):
        target=bits-1-level
        controls=list(range(bits-1,target,-1))
        for prefix in range(2**level):
            start=prefix*(2**(target+1));half=2**target
            denominator=pmf[start:start+2*half].sum()
            ratio=pmf[start+half:start+2*half].sum()/denominator if denominator else 0
            angle=2*math.asin(math.sqrt(float(ratio)))
            # Prefix is written most-significant control first.
            zeros=[q for j,q in enumerate(controls) if not(prefix>>(level-1-j))&1]
            if zeros:qc.x(zeros)
            if controls:qc.append(RYGate(angle).control(len(controls),annotated=False),controls+[target])
            else:qc.ry(angle,target)
            if zeros:qc.x(zeros)
    return qc


@lru_cache(maxsize=None)
def clean_mcx_gate(controls):
    """Exact MCX using c-2 clean ancillas and 2c-3 exact Toffolis, c>=2.

    These are ordinary CCX gates, not relative-phase Toffolis. The initial
    ancillas must be zero; the compute/action/uncompute sequence restores them.
    """
    if controls<2:raise ValueError('use X/CX for fewer than two controls')
    ancillas=max(0,controls-2)
    qc=QuantumCircuit(controls+1+ancillas,name=f'clean_mcx_{controls}')
    target=controls
    if controls==2:qc.ccx(0,1,target)
    else:
        work=list(range(controls+1,qc.num_qubits))
        qc.ccx(0,1,work[0])
        for j in range(2,controls-1):qc.ccx(work[j-2],j,work[j-1])
        qc.ccx(work[-1],controls-1,target)
        for j in reversed(range(2,controls-1)):qc.ccx(work[j-2],j,work[j-1])
        qc.ccx(0,1,work[0])
    return qc.to_gate()


def append_mcx(qc,controls,target,ancillas,style):
    if len(set(controls+[target]))!=len(controls)+1:raise ValueError('overlapping control/target')
    if not controls:qc.x(target)
    elif len(controls)==1:qc.cx(controls[0],target)
    elif style=='compact':qc.mcx(controls,target)
    elif style=='clean':
        needed=len(controls)-2
        pool=ancillas[:needed]
        if len(pool)<needed or set(pool)&set(controls+[target]):raise ValueError('insufficient/disjoint clean work')
        qc.append(clean_mcx_gate(len(controls)),controls+[target]+pool,copy=False)
    else:raise ValueError('unknown style')


def phase_zero(qc,qubits,ancillas,style):
    if not qubits:raise ValueError('empty reflection')
    qc.x(qubits);qc.h(qubits[-1])
    append_mcx(qc,qubits[:-1],qubits[-1],ancillas,style)
    qc.h(qubits[-1]);qc.x(qubits)


def layout(weights,bits=4,threshold_bits=18,style='clean'):
    weights=tuple(map(int,weights))
    if not weights or min(weights)<0 or max(weights)==0 or threshold_bits<0:
        raise ValueError('nonnegative nonzero weights and power-of-two threshold required')
    data=len(weights)*bits
    maximum=(2**bits-1)*sum(weights)
    score=max(1,maximum.bit_length())
    if score<=threshold_bits:raise ValueError('event would be always true; choose a smaller threshold')
    # Oracle arithmetic uses separate clean scratch; populated data/score bits
    # are never borrowed as clean workspace. After oracle uncompute the entire
    # score register is zero and can supply part of the diffuser's scratch.
    oracle_scratch=max(0,score-2)
    diffuser_scratch=max(0,data-3)
    extra=max(oracle_scratch,diffuser_scratch-score) if style=='clean' else 0
    return {'cells':len(weights),'count_bits_per_cell':bits,'data_qubits':data,
            'score_qubits':score,'extra_clean_qubits':extra,'total_qubits':data+score+extra,
            'maximum_encoded_score':maximum,'threshold':2**threshold_bits,
            'threshold_bits':threshold_bits,'diffuser_clean_ancillas_required':diffuser_scratch,
            'diffuser_score_qubits_reused':min(score,diffuser_scratch) if style=='clean' else 0,
            'oracle_clean_ancillas_reserved':oracle_scratch if style=='clean' else 0,
            'style':style}


def addition_plan(weights,bits,width):
    """Stream each controlled power-of-two increment, high carry first."""
    for cell,weight in enumerate(weights):
        for count_bit in range(bits):
            control=cell*bits+count_bit
            for wbit in range(int(weight).bit_length()):
                if not (int(weight)>>wbit)&1:continue
                shift=wbit+count_bit
                for target in range(width-1,shift,-1):
                    yield control,tuple(range(shift,target)),target
                yield control,(),shift


def preparation(rate,cells=49,bits=4):
    cell=cell_preparation(rate,bits).to_gate()
    qc=QuantumCircuit(cells*bits,name='prepare_all_counts')
    for i in range(cells):qc.append(cell,list(range(i*bits,(i+1)*bits)),copy=False)
    return qc


def adder(weights,bits=4,threshold_bits=18,style='clean'):
    info=layout(weights,bits,threshold_bits,style)
    n=info['data_qubits'];width=info['score_qubits']
    qc=QuantumCircuit(info['total_qubits'],name=f'weighted_sum_{style}')
    scratch=list(range(n+width,qc.num_qubits))
    for data_control,carry,target in addition_plan(weights,bits,width):
        append_mcx(qc,[data_control]+[n+j for j in carry],n+target,scratch,style)
    return qc


def oracle(weights,bits=4,threshold_bits=18,style='clean'):
    info=layout(weights,bits,threshold_bits,style)
    n=info['data_qubits'];w=info['score_qubits']
    addition=adder(weights,bits,threshold_bits,style)
    add=addition.to_gate()
    # Every addition instruction is an exact self-inverse CX/MCX. Reversing
    # them directly avoids replicating thousands of inverse gate definitions
    # during QPY serialization; this is the same unitary as add.inverse().
    undo=QuantumCircuit(info['total_qubits'],name=f'weighted_sum_uncompute_{style}')
    for inst in reversed(addition.data):
        undo.append(inst.operation,[addition.find_bit(q).index for q in inst.qubits],copy=False)
    qc=QuantumCircuit(info['total_qubits'],name=f'spatial_predicate_{style}')
    qc.append(add,range(qc.num_qubits),copy=False)
    phase_zero(qc,list(range(n+threshold_bits,n+w)),list(range(n+w,qc.num_qubits)),style)
    qc.append(undo.to_gate(),range(qc.num_qubits),copy=False)
    return qc


def make_circuit(weights,rate=1.5,bits=4,threshold_bits=18,style='clean'):
    info=layout(weights,bits,threshold_bits,style)
    n=info['data_qubits']
    prep=preparation(rate,len(weights),bits).to_gate()
    mark=oracle(weights,bits,threshold_bits,style).to_gate()
    qc=QuantumCircuit(info['total_qubits'],name=f'full_spatial_one_round_{style}',metadata=info)
    qc.append(prep,range(n),copy=False)
    qc.append(mark,range(qc.num_qubits),copy=False)
    qc.append(prep.inverse(),range(n),copy=False)
    # Score and extra ancillas are both zero here in the ideal construction.
    phase_zero(qc,list(range(n)),list(range(n,qc.num_qubits)),style)
    qc.append(prep,range(n),copy=False)
    return qc


def arithmetic_resource_counts(weights,bits=4,threshold_bits=18):
    info=layout(weights,bits,threshold_bits,'clean')
    controls=Counter(1+len(carry) for _,carry,_ in addition_plan(weights,bits,info['score_qubits']))
    adder_cx=controls.get(1,0)
    adder_ccx=sum((2*c-3)*count for c,count in controls.items() if c>=2)
    high=info['score_qubits']-threshold_bits
    mark_ccx=max(0,2*(high-1)-3) if high>=3 else 0
    mark_cx=1 if high==2 else 0
    dcontrols=info['data_qubits']-1
    diffuser_ccx=2*dcontrols-3 if dcontrols>=2 else 0
    return {'adder_mcx_control_histogram':dict(sorted(controls.items())),
            'adder_direct_cx':adder_cx,'adder_exact_ccx':adder_ccx,
            'oracle_direct_cx':2*adder_cx+mark_cx,
            'oracle_exact_ccx':2*adder_ccx+mark_ccx,
            'diffuser_exact_ccx':diffuser_ccx,
            'mark_single_qubit_x':2*high,'mark_single_qubit_h':2,
            'diffuser_single_qubit_x':2*info['data_qubits'],'diffuser_single_qubit_h':2}
