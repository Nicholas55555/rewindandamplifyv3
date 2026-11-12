"""Raw hardware counts -> atomic observables and decoded photon moments.

No optical readout correction, accepted-event filtering, or artificial coherent
tail renormalization. Calibration corrections, if later added, require separate
explicit evidence and uncertainty; they must preserve these raw summaries.
"""
import math
import numpy as np
from models import decode_photon, photon_moments


def parsed_counts(counts,width):
    out={}
    for key,value in counts.items():
        if isinstance(value,bool) or int(value)!=value or value<0:raise ValueError('nonnegative integer counts required')
        if isinstance(key,str):
            text=key.replace(' ','')
            idx=int(text,16) if text.startswith('0x') else int(text,2)
        else:idx=int(key)
        if not 0<=idx<(1<<width):raise ValueError('count key outside logical register')
        out[idx]=out.get(idx,0)+int(value)
    if not sum(out.values()):raise ValueError('empty counts')
    return out


def wilson(k,n):
    z=1.959963984540054;p=k/n;denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return [float(max(0,center-half)),float(min(1,center+half))]


def observable_summary(counts,function):
    n=sum(counts.values());total=sum(function(k)*v for k,v in counts.items())
    mean=total/n
    second=sum(function(k)**2*v for k,v in counts.items())/n
    se=np.sqrt(max(0,second-mean*mean)/(n-1)) if n>1 else None
    return {'mean':float(mean),'shot_standard_error':float(se) if se is not None else None}


def score_counts(counts,row):
    raw=parsed_counts(counts,row['num_qubits']);shots=sum(raw.values())
    meta=row['metadata'];ref=row['reference']
    if meta['family']=='atomic_finite_pulse':
        zeros=sum(v for k,v in raw.items() if k&1==0)
        p=zeros/shots;interval=wilson(zeros,shots)
        return {'name':row['name'],'family':meta['family'],'shots':shots,'basis':meta['basis'],
                'raw_system_zero_probability':p,'raw_system_zero_wilson95':interval,
                'raw_pauli_expectation':2*p-1,
                'raw_pauli_interval95':[2*interval[0]-1,2*interval[1]-1],
                'ideal_system_zero_probability':ref['system_probability_zero_in_measurement_basis'],
                'absolute_probability_error':abs(p-ref['system_probability_zero_in_measurement_basis']),
                'scope':'Raw emulated channel output; no physical atomic sensor or optical readout correction.'}
    n=meta['photons_if_prepared'];occ={}
    for index,count in raw.items():
        key=decode_photon(index,n);occ[key]=occ.get(key,0)+count
    target={tuple(map(int,k.split(','))):v for k,v in ref['occupancy_probabilities'].items()}
    support=set(occ)|set(target)
    moments={}
    functions={'mean_a':lambda x:x[0],'mean_b':lambda x:x[1],
               'factorial2_a':lambda x:x[0]*(x[0]-1),'factorial2_b':lambda x:x[1]*(x[1]-1),
               'cross_ab':lambda x:x[0]*x[1]}
    for key,function in functions.items():
        moments[key]=observable_summary(occ,function)
        moments[key]['ideal']=ref['moments'][key]
    return {'name':row['name'],'family':meta['family'],'shots':shots,
            'raw_occupancy_counts':{f'{a},{b}':v for (a,b),v in sorted(occ.items())},
            'occupancy_tv':float(.5*sum(abs(occ.get(k,0)/shots-target.get(k,0)) for k in support)),
            'raw_moments':moments,'source_flag_failure_fraction':sum(v for k,v in raw.items() if not (k>>(2*n))&1)/shots,
            'scope':'Aggregated simulated photon occupations; all source failures/losses charged. TV includes shot noise; not quantum-state fidelity.'}


def aggregate_coherent_sector_scores(scores,rows,accounting):
    """Stratified hardware estimates with original Poisson sector weights.

    Conditional N shots are measurement allocations, not source photon budgets.
    Independent-sector shot standard errors are propagated; missing sectors and
    unmodeled hardware correlations are not silently filled with exact values.
    """
    indexed={s['name']:s for s in scores};groups={}
    for row in rows:
        meta=row['metadata']
        if meta['family']=='photon_coherent_sector':groups.setdefault(meta['phase_rad'],[]).append(row)
    result=[]
    for phase,group in sorted(groups.items()):
        available=[r for r in group if r['name'] in indexed]
        missing=[r['metadata']['photons_if_prepared'] for r in group if r['name'] not in indexed]
        weight_missing=sum(r['metadata']['poisson_weight'] for r in group if r['name'] not in indexed)
        weighted={};variances={};occupancy={(0,0):accounting['weights'][0]}
        for row in available:
            score=indexed[row['name']];w=row['metadata']['poisson_weight']
            for key,value in score['raw_moments'].items():
                weighted[key]=weighted.get(key,0.)+w*value['mean']
                se=value['shot_standard_error']
                variances[key]=variances.get(key,0.)+(w*se)**2 if se is not None else float('nan')
            for key,count in score['raw_occupancy_counts'].items():
                pair=tuple(map(int,key.split(',')));occupancy[pair]=occupancy.get(pair,0.)+w*count/score['shots']
        result.append({'phase_rad':phase,'eta':.81,'sectors_measured':len(available),'missing_requested_sectors':missing,
            'unmeasured_requested_weight':weight_missing,'omitted_high_N_probability':accounting['omitted_probability'],
            'retained_occupancy_mass':sum(occupancy.values()),
            'raw_occupancy_subprobabilities':{f'{a},{b}':v for (a,b),v in sorted(occupancy.items())},
            'raw_weighted_moments':{k:{'mean':v,'independent_shot_standard_error':math.sqrt(variances[k])} for k,v in weighted.items()},
            'incident_mean_photons_full_reference':2.,
            'source_cost_scope':'Two mean photons before object in the full coherent model; vacuum/tail not discarded. Hardware stratified sample counts are not optical acquisition time.',
            'tail_bounds':accounting})
    return result
