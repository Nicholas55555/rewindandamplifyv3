"""Resolve uncertainty behavior in the ORIGINAL independent-Poisson 7x7 model.

This is a classical follow-up, separate from the correlated 2x2 quantum
bridge. The original blur/ROI response is linear in the 49 counts. Rounding
its positive weights down/up gives computable bounds on the true event
probability via a compound-Poisson recurrence (no sampled reference truth).
Double-precision roundoff is separately checked; these are mathematical
discretization bounds evaluated numerically, not interval-arithmetic proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import brentq
from scipy.fft import fft, ifft
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spatial_model import response, proposal_rates


def response_weights():
    impulses = np.eye(49).reshape(49,7,7)
    return response(impulses)[1]


def lattice_cdf(integer_weights, rates, cutoff, dtype=np.float64):
    """P(sum a_i*Poisson(rate_i)<cutoff), computed without Poisson truncation.

    From the PGF exp(sum_i rate_i*(x**a_i-1)):
    p[0]=exp(-sum rates with a_i>0),
    k*p[k]=sum_i a_i*rate_i*p[k-a_i].
    Zero-weight counts are marginalized, including their unlimited tails.
    """
    a=np.asarray(integer_weights,dtype=int)
    rates=np.asarray(rates,dtype=dtype)
    if len(a)!=len(rates) or np.any(a<0) or np.any(rates<0) or cutoff<1:
        raise ValueError('invalid compound-Poisson inputs')
    unique=np.unique(a[a>0])
    intensities=np.array([rates[a==v].sum() for v in unique],dtype=dtype)
    coefficients=unique.astype(dtype)*intensities
    pmf=np.zeros(cutoff,dtype=dtype)
    pmf[0]=np.exp(-intensities.sum())
    active=0
    for k in range(1,cutoff):
        while active<len(unique) and unique[active]<=k: active+=1
        if active:
            pmf[k]=np.dot(coefficients[:active],pmf[k-unique[:active]])/k
    return float(pmf.sum())


def reference_bounds(dose, cutoff=200000, threshold=.8, weights=None):
    weights=response_weights() if weights is None else np.asarray(weights)
    # Scale by integer cutoff so strict inequalities map to integer < cutoff.
    scaled=weights/threshold*cutoff
    lower_weights=np.floor(scaled).astype(int)
    upper_weights=np.ceil(scaled).astype(int)
    rates=np.full(len(weights),dose)
    lower=lattice_cdf(upper_weights,rates,cutoff)
    upper=lattice_cdf(lower_weights,rates,cutoff)
    return {'lower':lower,'upper':upper,'width':upper-lower,
            'relative_width':(upper-lower)/((upper+lower)/2),
            'lattice_cutoff':cutoff,'response_grid_step':threshold/cutoff,
            'integer_weight_count_lower':int(len(np.unique(lower_weights))),
            'integer_weight_count_upper':int(len(np.unique(upper_weights)))}


def fft_check(dose,cutoff=10000,threshold=.8,size=262144):
    """Independent PGF inversion; bound positive wraparound using Chernoff.

    The inverse DFT gives P(S=k mod size). Its CDF can exceed the true CDF by
    at most P(S>=size), bounded by exp(K(t)-t*size), t>0. Numerical FFT error
    is diagnostic here, not rigorously interval-bounded.
    """
    weights=response_weights()
    a=np.floor(weights/threshold*cutoff).astype(int)
    rates=np.full(49,dose)
    jump_intensities=np.bincount(a,weights=rates,minlength=size)
    pmf=ifft(np.exp(fft(jump_intensities)-rates.sum())).real
    t=brentq(lambda x:float(np.sum(rates*a*np.exp(x*a)))-size,0,.01)
    log_tail=float(np.sum(rates*np.expm1(t*a))-t*size)
    value=float(pmf[:cutoff].sum())
    recurrence=lattice_cdf(a,rates,cutoff)
    return {'fft_probability':value,'recurrence_probability':recurrence,
            'absolute_disagreement':abs(value-recurrence),
            'log_chernoff_upper_bound_on_wraparound':log_tail,
            'fft_size':size,'lattice_cutoff':cutoff,
            'minimum_fft_mass':float(pmf.min())}


def wilson(k,n):
    z=1.959963984540054;p=k/n;c=1+z*z/n
    center=(p+z*z/(2*n))/c
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/c
    return [max(0.,center-radius),min(1.,center+radius)]


def sample(rates,dose,weights,shots,seed,threshold=.8,direct=False):
    rng=np.random.default_rng(seed)
    counts=rng.poisson(rates,size=(shots,49))
    scores=counts@weights
    hit=scores<threshold
    logw=np.sum(rates-dose)+counts@np.log(dose/rates)
    values=np.exp(logw)*hit
    mean=float(values.mean())
    sd=float(values.std(ddof=1));se=sd/math.sqrt(shots)
    interval=wilson(int(hit.sum()),shots) if direct else [max(0.,mean-1.959963984540054*se),mean+1.959963984540054*se]
    if not direct and sd==0: interval=None
    sq=float(np.square(values).sum())
    return {'estimate':mean,'se':se if sd else None,'interval95':interval,
            'interval_method':'Wilson binomial' if direct else 'normal approximation from weighted sample variance',
            'hits':int(hit.sum()),'event_weight_ess':float(values.sum()**2/sq) if sq else 0.,
            'second_moment':float(sq/shots)}


def tune(dose,weights,pilot_shots=10000,seed=701000,threshold=.8):
    # The root matches the proposal mean response to the boundary. Pilot data
    # choose among four fixed multiples by sample second moment, before all
    # evaluation runs. No evaluation information is used in selection.
    root=brentq(lambda t:float(np.dot(weights,dose*np.exp(-t*weights)))-threshold,0,10000)
    rows=[]
    for i,multiplier in enumerate((.75,1.,1.25,1.5)):
        t=root*multiplier;rates=dose*np.exp(-t*weights)
        row=sample(rates,dose,weights,pilot_shots,seed+i,threshold=threshold)
        rows.append({'tilt_parameter':t,'root_multiplier':multiplier,'seed':seed+i,**row})
    winner=min(rows,key=lambda x:x['second_moment'])
    return dose*np.exp(-winner['tilt_parameter']*weights),{
        'boundary_mean_matching_tilt':root,'selected_tilt':winner['tilt_parameter'],
        'criterion':'minimum pilot second moment; fixed candidate grid, held-out evaluation',
        'pilot_maps_per_candidate':pilot_shots,'total_pilot_maps':4*pilot_shots,'candidates':rows}


def coverage_summary(rows,reference):
    low,high=reference['lower'],reference['upper'];mid=(low+high)/2
    estimates=np.array([x['estimate'] for x in rows])
    ses=[x['se'] for x in rows if x['se'] is not None]
    intervals=[x['interval95'] for x in rows]
    certain=sum(x is not None and x[0]<=low and x[1]>=high for x in intervals)
    possible=sum(x is not None and x[0]<=high and x[1]>=low for x in intervals)
    return {'runs':len(rows),'mean_estimate':float(estimates.mean()),
            'empirical_sd':float(estimates.std(ddof=1)),
            'mean_reported_se':float(np.mean(ses)) if ses else None,
            'rmse_against_reference_midpoint':float(np.sqrt(np.mean((estimates-mid)**2))),
            'reference_midpoint_uncertainty':(high-low)/2,
            'coverage95_certain_count':int(certain),'coverage95_possible_count':int(possible),
            'coverage95_fraction_bounds':[certain/len(rows),possible/len(rows)],
            'coverage_sampling_wilson95_outer':[wilson(certain,len(rows))[0],wilson(possible,len(rows))[1]],
            'unavailable_intervals':sum(x is None for x in intervals),
            'zero_hit_runs':sum(x['hits']==0 for x in rows),
            'median_event_weight_ess':float(np.median([x['event_weight_ess'] for x in rows]))}


def study(output,repeats=100,shots=20000):
    start=time.monotonic();weights=response_weights()
    # Fresh numerical equivalence check using original 7x7 Gaussian function.
    maps=np.random.default_rng(1881).poisson(1.5,size=(101,7,7))
    error=float(np.max(np.abs(response(maps)[1]-maps.reshape(-1,49)@weights)))
    result={'scope':'Original independent 7x7 Poisson/blur/central-3x3 threshold model; classical only, arbitrary units.',
            'weights':weights.reshape(7,7).tolist(),'linear_response_parity_max_abs_error':error,
            'original_source_sha256':hashlib.sha256((Path(__file__).resolve().parent.parent/'spatial_model.py').read_bytes()).hexdigest(),
            'threshold':.8,'blur_sigma':.8,'shots_per_evaluation_run':shots,'independent_evaluation_runs':repeats,
            'reference_note':'Mathematical floor/ceil discretization bounds in double precision, not certified interval arithmetic. No truncated photon-count tails.',
            'coverage_note':'Coverage lower/upper count handles finite deterministic reference bracket. Wilson interval additionally describes finite-repeat uncertainty, conditional on the frozen pilot-selected proposal.',
            'doses':[]}
    def save():output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for dindex,dose in enumerate((1.5,1.8)):
        print(f'7x7 dose={dose}: reference bounds',flush=True)
        refs=[reference_bounds(dose,k,weights=weights) for k in (10000,50000,200000,2000000)]
        rates,tuning=tune(dose,weights,seed=701000+100*dindex)
        row={'dose':dose,'reference_refinements':refs,'reference':refs[-1],
             'independent_fft_reference_check':fft_check(dose),
             'tuning':tuning,'selected_proposal_rates':rates.reshape(7,7).tolist(),'methods':{}}
        configs={'direct':np.full(49,dose),'original_fixed_tilt':proposal_rates(dose,.6).ravel(),
                 'pilot_tuned_exponential':rates}
        for methodid,(name,qrates) in enumerate(configs.items()):
            print(f'7x7 dose={dose}: {name}, {repeats} held-out runs',flush=True)
            rows=[]
            base=810000+100000*dindex+10000*methodid
            for k in range(repeats):
                item=sample(qrates,dose,weights,shots,base+k,direct=name=='direct')
                item['seed']=base+k;rows.append(item)
            row['methods'][name]={'summary':coverage_summary(rows,refs[-1]),'runs':rows,
                                  'evaluation_maps':repeats*shots,
                                  'setup_pilot_maps':tuning['total_pilot_maps'] if name=='pilot_tuned_exponential' else 0}
        result['doses'].append(row);save()
    result['elapsed_seconds']=time.monotonic()-start
    result['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save()
    print(json.dumps([{'dose':r['dose'],'reference':r['reference'],
                      'methods':{k:v['summary'] for k,v in r['methods'].items()}} for r in result['doses']]))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path(__file__).with_name('spatial_coverage_results.json'))
    p.add_argument('--repeats',type=int,default=100);p.add_argument('--shots',type=int,default=20000)
    a=p.parse_args()
    if a.output.exists():p.error('output exists; choose a fresh path')
    study(a.output,a.repeats,a.shots)
