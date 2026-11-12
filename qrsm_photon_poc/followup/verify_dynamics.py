"""Cavity cutoff and independent QuTiP verification of the photon companion."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))
import qrsm_photon as original


def trace(state, dim):
    return float(np.real(state[np.arange(dim)*(dim+1)].sum()))


def summary(p, steps=40):
    no, yes, full = original.instruments(p)
    dim = 4*p.n_cavity
    state = original.init_state(p)
    _, _, a, _, _ = original.operators(p)
    number = a.conj().T@a
    top = np.kron(np.eye(4), np.diag([0.]*(p.n_cavity-1)+[1.]))
    out = {'click':[], 'mean_cavity_photons':[], 'top_level_probability':[]}
    for t in range(steps):
        out['click'].append(trace(yes@state, dim))
        state = full@state
        rho = state.reshape((dim,dim), order='F')
        out['mean_cavity_photons'].append(float(np.trace(number@rho).real))
        out['top_level_probability'].append(float(np.trace(top@rho).real))
        if t == 1:
            before_third = state.copy()
    state = yes@before_third
    out['p_step3'] = trace(state,dim)
    state /= out['p_step3']
    out['after_step3'] = []
    for t in range(3,steps):
        out['after_step3'].append(trace(yes@state,dim))
        state = full@state
    return out


def independent_qutip(p):
    import qutip as qt
    d = qt.tensor(qt.destroy(2),qt.qeye(2),qt.qeye(p.n_cavity))
    e = qt.tensor(qt.qeye(2),qt.destroy(2),qt.qeye(p.n_cavity))
    a = qt.tensor(qt.qeye(2),qt.qeye(2),qt.destroy(p.n_cavity))
    zd = qt.tensor(qt.sigmaz(),qt.qeye(2),qt.qeye(p.n_cavity))
    ze = qt.tensor(qt.qeye(2),qt.sigmaz(),qt.qeye(p.n_cavity))
    H = (p.defect_detuning*d.dag()*d+p.cavity_detuning*a.dag()*a
         +p.drive/2*(e+e.dag())+p.g_defect*(d.dag()*e+e.dag()*d)
         +p.g_cavity*(e.dag()*a+a.dag()*e))
    jumps = [np.sqrt(p.kappa*p.detector_eta)*a,
             np.sqrt(p.kappa*(1-p.detector_eta))*a,
             np.sqrt(p.gamma_emitter)*e,np.sqrt(p.gamma_defect)*d,
             np.sqrt(p.gamma_phi_emitter/2)*ze,np.sqrt(p.gamma_phi_defect/2)*zd]
    psi = qt.tensor(qt.basis(2,0),qt.basis(2,0),qt.basis(p.n_cavity,0))
    return qt,H,jumps,psi


def master_check(p):
    qt,H,jumps,psi = independent_qutip(p)
    times = np.arange(41)*p.dt
    result = qt.mesolve(H,psi,times,jumps,options={'atol':1e-11,'rtol':1e-10,'store_states':True})
    full = original.instruments(p)[2]
    state = original.init_state(p)
    errors=[]
    for rho in result.states:
        errors.append(float(np.linalg.norm(rho.full().reshape(-1,order='F')-state)))
        state=full@state
    return {'max_density_frobenius_error':max(errors), 'times':times.tolist(),
            'errors':errors, 'passed':max(errors)<2e-7}


def wilson(k,n,z):
    q=k/n
    den=1+z*z/n
    center=(q+z*z/(2*n))/den
    half=z*np.sqrt(q*(1-q)/n+z*z/(4*n*n))/den
    return [float(center-half),float(center+half)]


def trajectory_check(p,ntraj=6000,seed=811107):
    qt,H,jumps,psi = independent_qutip(p)
    jumps.append(np.sqrt(p.dark_rate)*qt.qeye(psi.dims[0]))
    steps=12
    result=qt.mcsolve(H,psi,np.arange(steps+1)*p.dt,jumps,ntraj=ntraj,seeds=seed,
                      options={'atol':1e-10,'rtol':1e-9,'progress_bar':'',
                               'store_states':False,'keep_runs_results':False})
    records=np.zeros((ntraj,steps),dtype=np.uint8)
    for i,(times,which) in enumerate(zip(result.col_times,result.col_which)):
        for t,j in zip(times,which):
            if j in (0,len(jumps)-1):
                b=min(int(t/p.dt),steps-1)
                records[i,b]=1
    expected=summary(p,steps)
    candidates=[]
    for t,value in enumerate(expected['click']):
        candidates.append((f'click_step_{t+1}',records[:,t],value))
    for lag,value in enumerate(expected['after_step3']):
        t=lag+3
        candidates.append((f'joint_step3_step{t+1}',records[:,2]*records[:,t],value*expected['p_step3']))
    z=float(norm.ppf(1-.01/(2*len(candidates))))
    checks=[]
    for name,values,value in candidates:
        k=int(values.sum())
        interval=wilson(k,ntraj,z)
        se=np.sqrt(value*(1-value)/ntraj)
        checks.append({'statistic':name,'successes':k,'trials':ntraj,'exact':value,
                       'observed':k/ntraj,'simultaneous_approx_99pct_interval':interval,
                       'z_from_exact':float((k/ntraj-value)/se),
                       'inside_interval':interval[0]<=value<=interval[1]})
    return {'seed':seed,'trajectories':ntraj,'bins':steps,
            'interval_method':'Wilson with Bonferroni 1% family error across 21 fixed statistics; approximate coverage',
            'record_sha256':hashlib.sha256(records.tobytes()).hexdigest(),
            'checks':checks,'all_inside_intervals':all(x['inside_interval'] for x in checks)}


def run(out):
    if out.exists():
        raise FileExistsError(out)
    started=time.perf_counter()
    settings=[('default',original.Parameters()),('high_drive',replace(original.Parameters(),drive=2.1)),
              ('high_coupling',replace(original.Parameters(),g_defect=1.05))]
    cutoff={}
    for name,p in settings:
        rows={n:summary(replace(p,n_cavity=n)) for n in range(2,7)}
        ref=rows[6]
        for n,row in rows.items():
            row['max_click_difference_vs_dimension6']=float(np.max(np.abs(np.array(row['click'])-ref['click'])))
            row['max_conditional_difference_vs_dimension6']=float(np.max(np.abs(np.array(row['after_step3'])-ref['after_step3'])))
        cutoff[name]={'parameters':asdict(p),'dimensions':rows}
        print(name,[(n,round(rows[n]['max_click_difference_vs_dimension6'],7)) for n in rows],flush=True)
    import qutip
    checks={str(n):master_check(replace(original.Parameters(),n_cavity=n)) for n in (2,3,4)}
    trajectory=trajectory_check(original.Parameters())
    payload={'scope':'Synthetic finite-cavity model numerical verification; no physical source data',
             'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'qutip':qutip.__version__},
             'cutoff':cutoff,'independent_master_equation':checks,'independent_quantum_jumps':trajectory,
             'elapsed_seconds':time.perf_counter()-started,
             'source_sha256':{str(x.relative_to(PARENT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [PARENT/'qrsm_photon.py',Path(__file__),HERE/'PROTOCOL.md']}}
    out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print('Saved',out,'ODE passed',all(x['passed'] for x in checks.values()),'MC intervals',trajectory['all_inside_intervals'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'dynamics_results.json')
    run(parser.parse_args().output)
