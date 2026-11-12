"""Relate finite capped/lattice circuits to the original 7x7 process."""
from pathlib import Path
import sys
import numpy as np
from scipy.stats import poisson
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'followup'))
from spatial_coverage import response_weights,lattice_cdf
from circuit_model import capped_poisson


def integer_weights(threshold_bits=18,threshold=.8):
    weights=response_weights()
    scaled=weights/threshold*(2**threshold_bits)
    return weights,{'floor':np.floor(scaled).astype(int),'ceil':np.ceil(scaled).astype(int)}


def capped_cdf(weights,rate,cutoff,bits=4):
    """Exact dynamic program for the finite encoded independent process.

    Only scores >=cutoff are discarded. All weights are nonnegative, so such
    states cannot later re-enter the event. The count15 tail is kept exactly.
    """
    pmf=capped_poisson(rate,bits)
    mass=np.zeros(cutoff);mass[0]=1
    for weight in weights:
        new=np.zeros_like(mass)
        for count,p in enumerate(pmf):
            shift=int(weight)*count
            if shift>=cutoff:break
            new[shift:]+=p*mass[:cutoff-shift]
        mass=new
    return float(mass.sum())


def bounds(rate,threshold_bits=18,bits=4):
    real,weights=integer_weights(threshold_bits)
    cutoff=2**threshold_bits;cap=2**bits-1
    tail=float(poisson.sf(cap,rate))  # difference requires original N>cap
    union=min(1.,len(real)*tail)
    exact_union=float(-np.expm1(len(real)*np.log1p(-tail)))
    uncapped={name:lattice_cdf(w,np.full(len(w),rate),cutoff) for name,w in weights.items()}
    finite={name:capped_cdf(w,rate,cutoff,bits) for name,w in weights.items()}
    low=max(0.,uncapped['ceil'],finite['ceil']-union)
    high=min(1.,uncapped['floor'],finite['floor'])
    for name in weights:
        assert -1e-13<=finite[name]-uncapped[name]<=union+1e-13
    return {'dose':rate,'count_cap':cap,'overflow_category_probability':float(poisson.sf(cap-1,rate)),
            'per_cell_probability_count_value_changes':tail,
            'union_bound_any_count_value_changes':union,
            'exact_independent_any_count_value_changes':exact_union,
            'uncapped_integer_lattice_cdf':uncapped,'finite_capped_integer_lattice_cdf':finite,
            'original_process_probability_bracket':[low,high],
            'bracket_width':high-low,'relative_bracket_width':(high-low)/((high+low)/2),
            'finite_circuit_event_absolute_error_upper':{name:max(abs(p-low),abs(p-high)) for name,p in finite.items()},
            'ideal_one_round_analytic_prediction_not_statevector':{name:float(np.sin(3*np.arcsin(np.sqrt(p)))**2) for name,p in finite.items()}}
