"""Bounded29-qubit extension with exact MPS flag/memory references."""
import math
import time
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit_aer import AerSimulator
from design import Parameters
from physical_model import photon_modes,branch_states
from circuits import append_emission


def build(parameters,controls):
    if parameters.gap_dephasing not in (0.,1.):raise ValueError('Gap must be coherent or fully dephased')
    modes=[photon_modes(parameters,c) for c in controls]
    sizes=[int(math.log2(m.shape[0])) for m,_ in modes]
    bath_count=2*len(controls)-1 if parameters.gap_dephasing else 0
    width=2+sum(2*n+1 for n in sizes)+bath_count
    if width>29:raise ValueError('Selected-design logical circuit cap is29qubits')
    qc=QuantumCircuit(width);qc.h(0);qc.cx(0,1)
    cursor=2;flags=[];baths=[];registers=[]
    def gap():
        nonlocal cursor
        qc.ry(parameters.theta,0)
        if parameters.gap_dephasing:
            qc.cx(0,cursor);baths.append(cursor);cursor+=1
    for t,((m,info),n) in enumerate(zip(modes,sizes)):
        if t:gap()
        first=list(range(cursor,cursor+n));cursor+=n
        second=list(range(cursor,cursor+n));cursor+=n
        flag=cursor;cursor+=1;flags.append(flag)
        append_emission(qc,0,first,m[:,:2]);gap();append_emission(qc,0,second,m[:,2:])
        qc.h(flag)
        for a,b in zip(first,second):qc.cswap(flag,a,b)
        qc.h(flag)
        registers.append({'first':first,'second':second,'gram_rank':info['rank']})
    assert cursor==width
    qc.metadata={'kind':'selected_design_four_pair_joint_photon_instrument','memory_qubit':0,
                 'initial_memory_purifier':1,'flag_qubits':flags,'memory_readout_basis':'Z',
                 'photon_mode_registers':registers,'dephasing_bath_qubits':baths,
                 'controls_over_gamma':list(controls),'gap_dephasing':parameters.gap_dephasing,
                 'theta':parameters.theta,'delta_over_gamma':parameters.delta_over_gamma,
                 'all_other_registers_retained_until_final_measurement':True,
                 'optical_scope':'Digitally encoded exponential photon modes and SWAP symmetry. Optical collection and confusion excluded.'}
    return qc


def marginal_reference(parameters,controls):
    branches=branch_states(parameters,controls)
    size=1<<len(controls);reference=np.zeros(2*size)
    for bits,rho in branches.items():
        flag_index=sum(bit<<j for j,bit in enumerate(bits))
        for memory in [0,1]:reference[flag_index+memory*size]=rho[memory,memory].real
    return reference,branches


def compile_and_verify(qc,parameters,controls):
    begin=time.perf_counter()
    compiled=transpile(qc,basis_gates=['u','cx'],optimization_level=1,seed_transpiler=31)
    selected=qc.metadata['flag_qubits']+[0]
    simulation=compiled.copy();simulation.save_density_matrix(selected,label='flag_memory_density')
    backend=AerSimulator(method='matrix_product_state',matrix_product_state_truncation_threshold=1e-16,
                         matrix_product_state_max_bond_dimension=None,max_memory_mb=4096,
                         max_parallel_threads=1,max_parallel_experiments=1,mps_log_data=True)
    result=backend.run(simulation,shots=1,seed_simulator=20261112).result()
    if not result.success:raise RuntimeError(result.status)
    density=np.asarray(result.data(0)['flag_memory_density'])
    expected,branches=marginal_reference(parameters,controls)
    actual=density.diagonal().real
    marginal_error=float(np.max(abs(actual-expected)))
    size=1<<len(controls);errors=[]
    for bits,rho in branches.items():
        index=sum(bit<<j for j,bit in enumerate(bits));ind=[index,index+size]
        errors.append(float(np.linalg.norm(density[np.ix_(ind,ind)]-rho)))
    if max(errors+[marginal_error])>2e-10:raise AssertionError('MPS differs from exact conditional CP maps')
    report={'qubits':compiled.num_qubits,'cx_gates':int(compiled.count_ops().get('cx',0)),
            'u_gates':int(compiled.count_ops().get('u',0)),'depth':compiled.depth(),
            'basis':['u','cx'],'routing':'none; generic all-to-all synthesis',
            'mps_method':'matrix_product_state','mps_truncation_threshold':1e-16,'mps_bond_cap':None,
            'max_memory_mb':4096,'runtime_s':time.perf_counter()-begin,
            'marginal_max_abs_error':marginal_error,'conditional_unnormalized_branch_frobenius_error_max':max(errors),
            'simulator_metadata':result.results[0].metadata}
    return compiled,expected,branches,report
