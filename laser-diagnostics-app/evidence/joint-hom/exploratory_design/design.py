"""Exact finite-block design and simple-hypothesis resource bounds."""
from dataclasses import replace
import itertools
import math
from pathlib import Path
import sys

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from physical_model import (Parameters, branch_states, probabilities, bosonic_instrument,
                            gap_superoperator, apply)


def distribution(parameters, controls, independent_bosonic=False):
    if not independent_bosonic:
        return np.array(list(probabilities(branch_states(parameters, controls, observed=True)).values()))
    gap=gap_superoperator(parameters)
    branches=[np.eye(2)/2]
    for t,control in enumerate(controls):
        symmetric,anti=bosonic_instrument(parameters,control)
        mu=parameters.mode_overlap
        coin=(1+mu)/2*anti+(1-mu)/2*symmetric
        bunch=(1+mu)/2*symmetric+(1-mu)/2*anti
        maps=[(1-parameters.eta**2)*(symmetric+anti),
              parameters.eta**2*((1-parameters.e01)*bunch+parameters.e10*coin),
              parameters.eta**2*(parameters.e01*bunch+(1-parameters.e10)*coin)]
        branches=[apply(m,apply(gap,rho) if t else rho) for rho in branches for m in maps]
    return np.array([np.trace(rho).real for rho in branches])


def information(p,q,alpha=.05,beta=.20):
    p,q=np.array(p),np.array(q)
    if min(p.min(),q.min()) < -1e-12 or max(abs(p.sum()-1),abs(q.sum()-1))>1e-10:
        raise ValueError('Invalid probability law')
    p=np.maximum(p,0);q=np.maximum(q,0);p/=p.sum();q/=q.sum()
    support=(p>1e-15)|(q>1e-15)
    if np.any((p[support]==0)|(q[support]==0)):
        raise ValueError('Power moments require common support')
    logratio=np.log(p[support]/q[support]);p1=p[support];q1=q[support]
    muq=float(p1@logratio);muc=float(q1@logratio)
    varq=float(p1@(logratio-muq)**2);varc=float(q1@(logratio-muc)**2)
    b=float(np.sqrt(p*q).sum());b=min(1.,max(0.,b))
    inf=-math.log(b) if b else math.inf
    if inf<1e-14:
        sufficient=None;normal=None
    else:
        sufficient=math.ceil(-math.log(math.sqrt(alpha*beta))/inf)
        normal=max(1,math.ceil(((norm.ppf(1-alpha)*math.sqrt(varc)+norm.ppf(1-beta)*math.sqrt(varq))/(muq-muc))**2))
    return {'bhattacharyya_coefficient':b,'bhattacharyya_information_nats':inf,
            'kl_quantum_to_classical_nats':muq,'kl_classical_to_quantum_nats':-muc,
            'total_variation':float(.5*abs(p-q).sum()),'llr_mean_quantum':muq,
            'llr_mean_classical':muc,'llr_variance_quantum':varq,'llr_variance_classical':varc,
            'sufficient_independent_blocks_alpha05_power80':sufficient,
            'approximate_normal_independent_blocks_alpha05_power80':normal,
            'rigorous_llr_threshold':math.log(beta/alpha)}


def setting(parameters,controls):
    p=distribution(parameters,controls);q=distribution(replace(parameters,gap_dephasing=1.),controls)
    stats=information(p,q)
    return {'theta_radians':parameters.theta,'shift_pattern_over_gamma':list(controls),
            'parameters':vars(parameters),'information':stats,
            'score_nats_per_attempted_pair':stats['bhattacharyya_information_nats']/len(controls),
            'probabilities_quantum':p.tolist(),'probabilities_classical':q.tolist()}


def settings():
    angles=[j*np.pi/16 for j in range(17)]+[np.pi/3]
    amplitudes=[0.,.25,.5,.75,1.,1.5,2.,3.,4.]
    for theta in angles:
        for a in amplitudes:
            for label,controls in [('constant',[a]*4),('alternating',[a,-a,a,-a]),
                                   ('original_pattern',[0.,a,-a,0.]),('separated',[a,0.,-a,0.])]:
                yield theta,a,label,controls
