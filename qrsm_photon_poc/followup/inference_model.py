"""Controlled photon instruments and readout-memory likelihoods for fresh studies."""
from __future__ import annotations
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qrsm_photon import Parameters, hamiltonian, operators, lindblad_super, init_state

NAMES=('g_defect','defect_detuning','gamma_phi_emitter','detector_eta','drive')
BOUNDS=np.array([[0.,1.3],[-.8,.8],[.001,.2],[.3,.95],[.6,2.]])
SCALE=BOUNDS[:,1]-BOUNDS[:,0]
# Rabi-frequency scales have mean square 1. Each record resets the physical state.
DRIVE_SCALES=np.array([.8,1.,1.2])/np.sqrt(np.mean(np.array([.8,1.,1.2])**2))
PROTOCOLS={'fixed':[(1.,0.)], 'controlled':list(zip(DRIVE_SCALES,[-.5,0.,.5]))}


@lru_cache(maxsize=12)
def instrument(p:Parameters, control=(1.,0.)):
    """Known emitter detuning control, never direct hidden-defect control."""
    p=replace(p,drive=p.drive*float(control[0]))
    p.validate()
    d,e,a,zd,ze=operators(p)
    H=hamiltonian(p)+float(control[1])*(e.conj().T@e)
    detected=np.sqrt(p.kappa*p.detector_eta)*a
    other=[np.sqrt(p.kappa*(1-p.detector_eta))*a,np.sqrt(p.gamma_emitter)*e,
           np.sqrt(p.gamma_defect)*d,np.sqrt(p.gamma_phi_emitter/2)*ze,
           np.sqrt(p.gamma_phi_defect/2)*zd]
    full=expm(p.dt*lindblad_super(H,[detected]+other))
    eye=np.eye(H.shape[0]); cdc=detected.conj().T@detected
    no_generator=lindblad_super(H,other)-.5*(np.kron(eye,cdc)+np.kron(cdc.T,eye))
    no=np.exp(-p.dark_rate*p.dt)*expm(p.dt*no_generator)
    return no,full-no,full


def traces(states,dim):
    return states[np.arange(dim)*(dim+1)].sum(axis=0).real


def sample(p,controls,n_per_control,steps,seed,dead_bins=0):
    if dead_bins not in (0,1):
        raise ValueError('only zero or one bin dead time is implemented')
    rng=np.random.default_rng(seed)
    batches=[]
    for control in controls:
        no,yes,full=instrument(p,tuple(control)); dim=4*p.n_cavity
        states=np.tile(init_state(p)[:,None],(1,n_per_control))
        unavailable=np.zeros(n_per_control,dtype=bool)
        records=np.zeros((n_per_control,steps),dtype=np.uint8)
        for t in range(steps):
            s0=no@states
            hit=(rng.random(n_per_control)>=np.clip(traces(s0,dim),0,1))&~unavailable
            nxt=np.where(hit[None,:],yes@states,s0)
            if dead_bins:
                nxt[:,unavailable]=(full@states[:,unavailable])
            prob=traces(nxt,dim)
            if np.any(prob<=0):
                raise FloatingPointError('nonpositive sampled branch')
            states=nxt/prob
            records[:,t]=hit
            unavailable=hit if dead_bins else unavailable
        batches.append(records)
    return batches


def logs(records,p,control=(1.,0.),dead_bins=0):
    raw=np.asarray(records)
    if raw.ndim!=2 or not np.all((raw==0)|(raw==1)):
        raise ValueError('binary record matrix required')
    if dead_bins not in (0,1):
        raise ValueError('unsupported dead time')
    records=raw.astype(np.uint8)
    no,yes,full=instrument(p,tuple(control)); dim=4*p.n_cavity
    n,steps=records.shape
    state=np.tile(init_state(p)[:,None],(1,n))
    unavailable=np.zeros(n,dtype=bool); invalid=np.zeros(n,dtype=bool)
    result=np.zeros(n)
    for t in range(steps):
        hit=records[:,t].astype(bool)
        nxt=np.where(hit[None,:],yes@state,no@state)
        if dead_bins:
            invalid|=unavailable&hit
            nxt[:,unavailable]=full@state[:,unavailable]
        prob=traces(nxt,dim)
        if np.any(prob < -1e-8):
            raise FloatingPointError('negative branch')
        prob=np.maximum(prob,1e-300)
        result+=np.log(prob); state=nxt/prob
        unavailable=hit if dead_bins else unavailable
    result[invalid]=-np.inf
    return result


def all_logs(batches,p,controls,dead_bins=0):
    return np.concatenate([logs(x,p,c,dead_bins) for x,c in zip(batches,controls)])


def vector(p):
    return (np.array([getattr(p,n) for n in NAMES])-BOUNDS[:,0])/SCALE


def parameters(x,base):
    return replace(base,**dict(zip(NAMES,BOUNDS[:,0]+SCALE*np.asarray(x))))


def fit(batches,base,controls,*,seed,starts=3,maxfun=900,dead_bins=0,fixed_g=None):
    """Training-only bounded multistart. No truth-derived start is injected."""
    rng=np.random.default_rng(seed)
    dims=np.arange(5) if fixed_g is None else np.arange(1,5)
    n=sum(len(x) for x in batches)
    def expand(x):
        if fixed_g is None:
            return x
        return np.r_[(fixed_g-BOUNDS[0,0])/SCALE[0],x]
    def objective(x):
        return -all_logs(batches,parameters(expand(x),base),controls,dead_bins).sum()/n
    trials=[]
    for i in range(starts):
        start=rng.uniform(.15,.85,len(dims))
        result=minimize(objective,start,method='L-BFGS-B',bounds=[(0.,1.)]*len(dims),
                        options={'maxiter':120,'maxfun':maxfun,'ftol':1e-9,'gtol':2e-5,'finite_diff_rel_step':1e-4})
        full=expand(result.x)
        trials.append({'scaled_parameters':full.tolist(),'negative_loglikelihood':float(result.fun*n),
                       'success':bool(result.success),'message':str(result.message),'evaluations':int(result.nfev),
                       'boundary_parameters':[NAMES[j] for j,x in enumerate(full) if x<.002 or x>.998]})
        print('fit',seed,'start',i,'nll',round(result.fun*n,5),'calls',result.nfev,'success',result.success,flush=True)
    best=min(trials,key=lambda r:r['negative_loglikelihood'])
    return parameters(best['scaled_parameters'],base),{'best':best,'starts':trials}


def exact_distribution(p,control=(1.,0.),steps=8,dead_bins=0):
    bits=((np.arange(2**steps)[:,None]>>np.arange(steps))&1).astype(np.uint8)
    return bits,np.exp(logs(bits,p,control,dead_bins))


def information(p,controls,steps=8):
    """Exact expected Fisher information for short records; scaled coordinates."""
    x=vector(p); eps=1e-4
    total=np.zeros((5,5))
    for c in controls:
        _,probs=exact_distribution(p,c,steps)
        gradient=[]
        for j in range(5):
            dx=np.zeros(5); dx[j]=eps
            a=exact_distribution(parameters(x+dx,p),c,steps)[1]
            b=exact_distribution(parameters(x-dx,p),c,steps)[1]
            gradient.append((a-b)/(2*eps))
        g=np.array(gradient)
        total+=(g/probs)@g.T/len(controls)
    values,vectors=np.linalg.eigh(total)
    return {'record_bins':steps,'parameter_order':list(NAMES),'coordinate_scale':SCALE.tolist(),
            'matrix':total.tolist(),'eigenvalues':values.tolist(),
            'condition_number':float(values[-1]/values[0]) if values[0]>0 else None,
            'weakest_scaled_direction':vectors[:,0].tolist(),
            'scope':'Expected information per equal-weight short record at supplied parameter point; not a global identifiability proof'}
