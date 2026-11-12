"""Finite, weak-response quantum-light exposure model; no material calibration.

Rates are expected activation EVENTS per attempted source clock, not photon
probabilities. The M equal spatial cells form a two-input passive multiport:
u_a[j]=1/sqrt(M), u_b[j]=exp(i*phi_j)/sqrt(M). Extra vacuum inputs complete
the unitary and do not contribute to normally ordered moments. Thus G1 sums
to the surviving mean photons; local G2 correctly includes a 1/M^2 factor.
M and the effective per-cell response coefficient belong to the chosen toy
geometry and may not be varied independently to infer physical resolution.
"""
from dataclasses import asdict, dataclass
import math
import numpy as np
from scipy.special import gammainc
from scipy.optimize import minimize_scalar


@dataclass(frozen=True)
class Setup:
    cells: int = 32
    wavelength_nm: float = 800.0
    half_angle_deg: float = 30.0
    eta_a: float = 0.8
    eta_b: float = 0.8
    jitter_rad: float = 0.15
    blur_nm: float = 40.0
    pixel_average: bool = True
    linear_per_photon: float = 2e-5
    pair_per_factorial_moment: float = 1e-3
    background_per_cell_clock: float = 0.0
    clock_hz: float = 1e6
    quantum_success: float = 1.0
    threshold_events: int = 20

    def validate(self):
        values=asdict(self)
        if not all(np.isfinite(v) for v in values.values()):
            raise ValueError('all parameters must be finite')
        if self.cells < 8 or self.cells % 4 or int(self.cells)!=self.cells:
            raise ValueError('cells must be an integer multiple of four, at least eight')
        if not 0 < self.half_angle_deg < 90 or self.wavelength_nm <= 0:
            raise ValueError('invalid optical geometry')
        if not all(0<=x<=1 for x in (self.eta_a,self.eta_b)):
            raise ValueError('transmission must be in [0,1]')
        if not 0<self.quantum_success<=1 or self.clock_hz<=0:
            raise ValueError('invalid source success or clock rate')
        if any(x<0 for x in (self.jitter_rad,self.blur_nm,self.linear_per_photon,
                             self.pair_per_factorial_moment,self.background_per_cell_clock)):
            raise ValueError('noise and response coefficients must be nonnegative')
        if self.threshold_events<1 or int(self.threshold_events)!=self.threshold_events:
            raise ValueError('threshold must be a positive integer')

    @property
    def period_nm(self):
        return self.wavelength_nm/(2*math.sin(math.radians(self.half_angle_deg)))

    @property
    def phases(self):
        return 2*np.pi*np.arange(self.cells)/self.cells


METHODS={
    'noon': {'label':'Two-photon NOON','quantum':True,'duty':1.0},
    'mixture': {'label':'Incoherent two-photon mixture','quantum':True,'duty':1.0},
    'coherent': {'label':'Single-phase coherent','quantum':False,'duty':1.0},
    'phase_cycled': {'label':'Phase-cycled coherent','quantum':False,'duty':1.0},
    'phase_cycled_burst': {'label':'Phase-cycled coherent, 10% duty','quantum':False,'duty':0.1},
}


def coefficients(method, setup):
    """Cosine coefficients [DC, first, second] per successfully delivered slot.

Duty cycling preserves average photons (2 before propagation) and clock time,
but raises active-slot mean photon number by 1/duty. Its G2 rises by 1/duty.
Phase cycling allocates HALF the active slots to phase 0 and HALF to pi.
No subtraction of deposited dose is permitted.
"""
    setup.validate()
    if method not in METHODS:
        raise ValueError('unknown method')
    a,b,m=setup.eta_a,setup.eta_b,setup.cells
    if method in ('noon','mixture'):
        g1=np.array([(a+b)/m,0,0.])
        g2=np.array([(a*a+b*b)/m**2,0,2*a*b/m**2 if method=='noon' else 0.])
    else:
        g1=np.array([(a+b)/m,2*np.sqrt(a*b)/m,0.])
        g2=np.array([((a+b)**2+2*a*b)/m**2,4*(a+b)*np.sqrt(a*b)/m**2,2*a*b/m**2])
        if method.startswith('phase_cycled'):
            g1[1]=g2[1]=0
        g2/=METHODS[method]['duty']
    return g1,g2


def transfer(setup, include_blur=True):
    """Gaussian phase jitter; optional post-activation Gaussian spatial blur.

Box averaging is a declared phenomenological pixel aperture. Blur redistributes
activation events, preserving their sum. Neither is a calibrated resist model.
"""
    harmonics=np.arange(3,dtype=float)
    factor=np.exp(-0.5*(harmonics*setup.jitter_rad)**2)
    if include_blur:
        factor*=np.exp(-0.5*(harmonics*2*np.pi*setup.blur_nm/setup.period_nm)**2)
    if setup.pixel_average:
        factor*=np.sinc(harmonics/setup.cells)
    return factor


def evaluate(coeff, phases):
    return np.asarray(coeff) @ np.cos(np.arange(3)[:,None]*np.atleast_1d(phases))


def event_rates(method, setup):
    g1,g2=coefficients(method,setup)
    success=setup.quantum_success if METHODS[method]['quantum'] else 1.0
    response=(setup.linear_per_photon*g1+setup.pair_per_factorial_moment*g2)*transfer(setup)
    response*=success
    response[0]+=setup.background_per_cell_clock
    rates=evaluate(response,setup.phases)
    if rates.min() < -1e-14:
        raise ArithmeticError('negative response')
    return np.maximum(rates,0),response


def photons_per_clock(method,setup):
    p=setup.quantum_success if METHODS[method]['quantum'] else 1.0
    return {'before_propagation':2*p,'incident_on_sample':p*(setup.eta_a+setup.eta_b)}


def exposure(method,setup,clocks):
    if not np.isfinite(clocks) or clocks<=0:
        raise ValueError('positive finite clocks required')
    rates,c=event_rates(method,setup)
    photons=photons_per_clock(method,setup)
    mean=clocks*rates
    phi=setup.phases
    weight=2*np.cos(2*phi)/setup.cells
    amplitude=float(weight@mean)
    variance=float(weight**2@mean)
    bright=np.cos(2*phi)>=0.7
    dark=np.cos(2*phi)<=-0.7
    # For integer threshold K, gammainc(K, mu)=P(Poisson(mu)>=K).
    exposed=gammainc(setup.threshold_events,mean)
    correct=np.r_[exposed[bright],1-exposed[dark]]
    return {
        'source_clocks':float(clocks),'seconds':float(clocks/setup.clock_hz),
        'prepared_successes_mean':float(clocks*(setup.quantum_success if METHODS[method]['quantum'] else 1)),
        'before_propagation_photons':float(clocks*photons['before_propagation']),
        'sample_incident_photons':float(clocks*photons['incident_on_sample']),
        'expected_events_total':float(mean.sum()),'mean_events_per_cell':float(mean.mean()),
        'event_visibility':float((mean.max()-mean.min())/(mean.max()+mean.min())) if mean.max()>0 else 0.,
        'second_harmonic_events_per_cell':amplitude,
        'second_harmonic_poisson_sd':float(np.sqrt(variance)),
        'second_harmonic_snr':float(amplitude/np.sqrt(variance)) if variance>0 else 0.,
        'guard_cell_accuracy':float(correct.mean()),
        'all_guard_cells_correct_probability':float(np.prod(correct)),
        'bright_cell_success':float(exposed[bright].mean()),
        'dark_cell_success':float((1-exposed[dark]).mean()),
        'cell_mean_events':mean.tolist(),
        'response_cosine_coefficients_per_clock':c.tolist(),
    }


def optimized_threshold_exposure(method,setup):
    """Model-informed exposure duration, same absolute threshold for every method.

    Optimization does not calibrate a material. It gives each method its best
    chance in the declared guard-band task and charges the resulting photon dose.
    """
    objective=lambda z:1-exposure(method,setup,10**z)['guard_cell_accuracy']
    grid=np.linspace(2,13,150)
    values=np.array([objective(z) for z in grid])
    k=int(np.argmin(values))
    lo,hi=grid[max(k-1,0)],grid[min(k+1,len(grid)-1)]
    opt=minimize_scalar(objective,bounds=(lo,hi),method='bounded',options={'xatol':1e-8})
    result=exposure(method,setup,10**opt.x)
    result['optimizer_log10_clocks_bounds']=[float(lo),float(hi)]
    return result


def simulate_counts(method,setup,clocks,repetitions,seed):
    analytic=exposure(method,setup,clocks)
    rng=np.random.default_rng(seed)
    samples=rng.poisson(analytic['cell_mean_events'],size=(repetitions,setup.cells))
    phi=setup.phases
    amplitude=samples@(2*np.cos(2*phi)/setup.cells)
    bright=np.cos(2*phi)>=.7;dark=np.cos(2*phi)<=-.7
    decisions=samples>=setup.threshold_events
    correctness=np.c_[decisions[:,bright],~decisions[:,dark]]
    score=correctness.mean(axis=1)
    all_correct=correctness.all(axis=1)
    success_rate=float(all_correct.mean())
    z=1.959963984540054
    center=(success_rate+z*z/(2*repetitions))/(1+z*z/repetitions)
    half=z*np.sqrt(success_rate*(1-success_rate)/repetitions+z*z/(4*repetitions**2))/(1+z*z/repetitions)
    return {'seed':seed,'repetitions':repetitions,
        'harmonic_empirical_mean':float(amplitude.mean()),
        'harmonic_empirical_sd':float(amplitude.std(ddof=1)),
        'harmonic_empirical_interval95':np.quantile(amplitude,[.025,.975]).tolist(),
        'guard_accuracy_empirical':float(score.mean()),
        'guard_accuracy_mean_mc_se':float(score.std(ddof=1)/np.sqrt(repetitions)),
        'all_guard_cells_correct_empirical':success_rate,
        'all_guard_cells_correct_mc_se':float(all_correct.std(ddof=1)/np.sqrt(repetitions)),
        'all_guard_cells_correct_wilson95':[float(max(0,center-half)),float(min(1,center+half))],
        'example_counts':samples[0].tolist()}


def weak_response_bound(method,setup):
    """Conservative max local active-slot expected events and summed photon drain.

    A pair event consumes two photons; response coefficients use n(n-1), so no
    missing factorial factor is implied. This is a chosen weak-coupling model,
    not a validated absorber or exact joint photon-count distribution.
    """
    m=setup.cells;a=setup.eta_a;b=setup.eta_b
    d=METHODS[method]['duty']
    if METHODS[method]['quantum']:
        peak1=(a+b)/m;peak2=(a+b)**2/m**2
    else:
        peak1=(np.sqrt(a)+np.sqrt(b))**2/(m*d);peak2=peak1**2
    active_local=setup.linear_per_photon*peak1+setup.pair_per_factorial_moment*peak2
    g1,g2=coefficients(method,setup)
    drain=m*(setup.linear_per_photon*g1[0]+2*setup.pair_per_factorial_moment*g2[0])
    return {'max_active_local_event_mean':float(active_local),
        'mean_absorbed_photon_fraction_upper_model':float(drain/(a+b)) if a+b>0 else 0.,
        'weak_regime_pass':bool(active_local<.01 and (drain/(a+b) if a+b else 0)<.01)}
