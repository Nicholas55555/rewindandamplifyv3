"""Supplementary faithful circuit adapters. No account or backend access."""
from pathlib import Path
import sys,math,importlib.util
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import DiagonalGate
from qiskit.quantum_info import Statevector

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'rewindandamplify-main'),str(ROOT/'finals-lithography')]
from viability_cost_study import make_circuit
from oracle_comparison import counter_oracle,enumerated_oracle
from qrsm_grover.model import QRSM
from qrsm_grover.amplify import hardware_amplified,hardware_iterate,steered_gamma
from qrsm_grover.fastsim import FastPurified,reflection_qubits
from qrsm_grover.predicates import click_at
from qrsm_grover.search import catalog_circuit,demo_catalog,tokenise,tokens_of,phases


def compiled(qc,qubits_initially_zero=True):
    return transpile(qc,basis_gates=['u','cx'],optimization_level=1,seed_transpiler=13,
                     qubits_initially_zero=qubits_initially_zero)

def contact(n,style,rounds):
    if n not in (3,5,7) or style not in ('counter','enumerated') or rounds not in (0,1):raise ValueError('contact rung')
    qc=make_circuit(n,.8,style,rounds)
    width=n+n.bit_length() if style=='counter' else n
    if qc.num_qubits<width:
        pad=QuantumCircuit(width);pad.compose(qc,range(n),inplace=True);qc=pad
    original=np.array([.8**i.bit_count()*.2**(n-i.bit_count()) for i in range(1<<n)])
    marked=np.array([i.bit_count()<2 for i in range(1<<n)]);p=original[marked].sum()
    target_p=np.sin((2*rounds+1)*np.arcsin(np.sqrt(p)))**2
    law=original*np.where(marked,target_p/p,(1-target_p)/(1-p))
    target=np.zeros(1<<width);target[:1<<n]=law
    return qc,{'family':'independent_contact','sites':n,'absorption_probability':.8,'style':style,'rounds':rounds,
        'data_qubits':list(range(n)),'workspace_qubits':list(range(n,width)),
        'marked_data_indices':np.flatnonzero(marked).tolist(),'plain_event_probability':float(p),
        'ideal_event_probability':float(target_p),'conditional_data_target':(original[marked]/p).tolist(),
        'source_paths':['finals-lithography/viability_cost_study.py','finals-lithography/oracle_comparison.py','finals-lithography/lithography.py'],
        'scope':'Synthetic independent sites; no physical lithography. Classical exact conditional sampler has no rejection.'},target


def large_catalog(rounds):
    if rounds not in (0,1,25):raise ValueError('catalog rung')
    n=10;size=1<<n;marks=np.random.default_rng(n).integers(0,2,size)
    diagonal=np.exp(1j*np.pi*marks)
    qc=QuantumCircuit(n);qc.h(range(n))
    for _ in range(rounds):
        qc.append(DiagonalGate(diagonal.tolist()),range(n))
        qc.h(range(n));qc.x(range(n));qc.h(n-1);qc.mcx(list(range(n-1)),n-1);qc.h(n-1);qc.x(range(n));qc.h(range(n))
    p=marks.mean();hit=np.sin((2*rounds+1)*np.arcsin(np.sqrt(p)))**2
    target=np.where(marks,hit/(size*p),(1-hit)/(size*(1-p)))
    return qc,{'family':'catalog_cost_1024','entries':size,'rounds':rounds,'mark_seed':n,
               'marked_indices':np.flatnonzero(marks).tolist(),'marked_fraction':float(p),'ideal_event_probability':float(hit),
               'canonical_cost_round_convention':25,'classical_scan_entries':size,
               'source_paths':['rewindandamplify-main/experiments/e6_catalog.py'],
               'scope':'Exact generic random-diagonal cost benchmark, not1024-entry natural-language retrieval. Classical code already reads all entries; r25 is not optimized for this mark fraction.'},target


def semantic_catalog():
    catalog=demo_catalog(16);request='what do we pay staff per team'
    tokens=tokenise(request,set().union(*(tokens_of(x) for x in catalog)))
    ph=phases(catalog,tokens);state=np.exp(1j*ph)/4;state=2*state.mean()-state
    return catalog_circuit(catalog,request,1),{'family':'semantic_catalog16','entries':16,'rounds':1,
        'catalog':catalog,'request':request,'tokens':tokens,'target_index':catalog.index('employee_payroll_by_department'),
        'source_paths':['rewindandamplify-main/qrsm_grover/search.py'],
        'scope':'Original token-based16-entry semantic reader, classical preprocessing and data loading charged.'},abs(state)**2


def history(T=8,rounds=1,steer=False):
    if T!=8 or rounds not in (0,1,2,3):raise ValueError('history rung')
    model=QRSM();n=model.n_memory;pred=click_at(T);mask=pred.mask(T)
    plain=model.history_probabilities(T);p=plain[mask].sum()
    gammas=None if not steer else [None]*(T-1)+[steered_gamma(p,model.gamma)]
    prep=model.purified(T,gammas=gammas);watch=reflection_qubits(model,T,'memory+last-1' if steer else 'full')
    oracle=pred.oracle(n+T,list(range(n,n+T)))
    qc=hardware_amplified(prep,oracle,rounds,reflect_on=watch)
    fast=FastPurified(model,T,gammas)
    target_state=list(fast.amplify(mask,rounds,watch))[-1][1]
    target=np.zeros(1<<qc.num_qubits);target[:len(target_state)]=abs(target_state)**2
    hist=(abs(target_state)**2).reshape(1<<T,1<<n).sum(1)
    conditional=.5*np.abs(hist[mask]/hist[mask].sum()-plain[mask]/p).sum()
    return qc,{'family':'qrsm_fixed_round_history','steps':T,'rounds':rounds,'steered':steer,
        'history_qubits':list(range(n,n+T)),'memory_qubits':list(range(n)),
        'workspace_qubits':list(range(n+T,qc.num_qubits)),'event_qubit':n+T-1,
        'plain_event_probability':float(p),'ideal_event_probability':float(hist[mask].sum()),
        'ideal_conditional_history_bias_vs_original_tv':float(conditional),
        'source_paths':['rewindandamplify-main/qrsm_grover/model.py','rewindandamplify-main/qrsm_grover/amplify.py','rewindandamplify-main/qrsm_grover/fastsim.py','rewindandamplify-main/qrsm_grover/predicates.py'],
        'scope':'Longer fixed-round QRSM ingredient; not a complete adaptive/unknown-p BBHT implementation. Full reflection exact; local steering circuit approximation separately reported.'},target


def bounded(T=10,window=4,rounds=1):
    if T!=10 or window not in (4,8) or rounds not in (1,2):raise ValueError('horizon rung')
    model=QRSM();n=model.n_memory;data=n+T;work=max(0,window-3);pred=click_at(T);mask=pred.mask(T)
    prep=model.purified(T);segment=QuantumCircuit(data)
    for t in range(T-window,T):model.add_step(segment,0,list(range(1,n)),n+t)
    watch=list(range(n+T-window,n+T));oracle=pred.oracle(data,list(range(n,n+T)))
    iteration=hardware_iterate(segment,oracle,data,work,watch)
    qc=QuantumCircuit(data+work);qc.compose(prep,range(data),inplace=True)
    for _ in range(rounds):qc.compose(iteration,inplace=True)
    fast=FastPurified(model,T);state=list(fast.amplify(mask,rounds,watch,rewind=window))[-1][1]
    target=np.zeros(1<<qc.num_qubits);target[:len(state)]=abs(state)**2
    hist=(abs(state)**2).reshape(1<<T,1<<n).sum(1);plain=model.history_probabilities(T);p=plain[mask].sum()
    conditional=.5*np.abs(hist[mask]/hist[mask].sum()-plain[mask]/p).sum()
    return qc,{'family':'bounded_rewind','steps':T,'window':window,'rounds':rounds,
        'history_qubits':list(range(n,n+T)),'memory_qubits':list(range(n)),
        'workspace_qubits':list(range(data,qc.num_qubits)),'reflection_qubits':watch,'event_qubit':n+T-1,
        'plain_event_probability':float(p),'ideal_event_probability':float(hist[mask].sum()),
        'ideal_conditional_history_bias_vs_original_tv':float(conditional),
        'source_paths':['rewindandamplify-main/qrsm_grover/model.py','rewindandamplify-main/qrsm_grover/amplify.py','rewindandamplify-main/qrsm_grover/fastsim.py','rewindandamplify-main/experiments/e7_resilience.py'],
        'scope':'Original finite-horizon rule: older history is not uniformly reweighted. Agreement with this approximate circuit is separate from bias versus exact global conditioning.'},target


def specs():
    result=[]
    for n in (3,5,7):
        for style in ('enumerated','counter'):
            for r in (0,1):result.append((f'contact_n{n}_{style}_r{r}',contact,(n,style,r)))
    for r in (0,1,25):result.append((f'catalog_cost1024_r{r}',large_catalog,(r,)))
    result.append(('catalog_semantic16_r1',semantic_catalog,()))
    for r in range(4):result.append((f'history_T8_full_r{r}',history,(8,r,False)))
    result.append(('history_T8_steered_local_r1',history,(8,1,True)))
    for w in (4,8):
        for r in (1,2):result.append((f'horizon_T10_w{w}_r{r}',bounded,(10,w,r)))
    return result
