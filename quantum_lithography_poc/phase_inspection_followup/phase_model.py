"""Exact finite-trial two-photon/coherent phase measurement model.

Sample dose is counted BEFORE object transmission. BOTH spatial modes illuminate
the object, with relative-phase generator (n_a-n_b)/2; neither bypasses it as an
external reference arm. Both modes' photons are charged; no uncounted bright
local oscillator is used. A calibrated
phase-bias reference is assumed equally for both methods. It does not reveal
the unknown object phase. Photon-number-resolving detection is assumed.
"""
from dataclasses import dataclass
import numpy as np

BIASES=np.array([0,np.pi/4,np.pi/2,3*np.pi/4])
OUTCOMES=np.array([[0,0],[1,0],[0,1],[2,0],[0,2],[1,1]])


@dataclass(frozen=True)
class Setup:
    object_transmission:float=0.9
    detection_efficiency:float=0.9
    preparation_success:float=1.0
    attempted_clock_hz:float=1e6

    def validate(self):
        if not all(np.isfinite(x) and 0<=x<=1 for x in [self.object_transmission,self.detection_efficiency]):
            raise ValueError('loss factors must be in [0,1]')
        if not np.isfinite(self.preparation_success) or not 0<self.preparation_success<=1:
            raise ValueError('preparation success must be in (0,1]')
        if not np.isfinite(self.attempted_clock_hz) or self.attempted_clock_hz<=0:
            raise ValueError('clock rate must be positive')

    @property
    def eta(self):return self.object_transmission*self.detection_efficiency


def quantum_probabilities(phi,setup):
    """Shape (phase, bias, six outcomes); all loss/vacuum outcomes included."""
    setup.validate();phase=np.atleast_1d(phi)[:,None]+BIASES[None,:]
    eta=setup.eta;p=setup.preparation_success
    c=np.cos(2*phase)
    probs=np.zeros((*phase.shape,6))
    probs[:,:,0]=1-p+p*(1-eta)**2
    probs[:,:,1]=probs[:,:,2]=p*eta*(1-eta)
    probs[:,:,3]=probs[:,:,4]=p*eta**2*(1+c)/4
    probs[:,:,5]=p*eta**2*(1-c)/2
    return np.maximum(probs,0)


def coherent_means(phi,setup):
    setup.validate();phase=np.atleast_1d(phi)[:,None]+BIASES[None,:]
    c=np.cos(phase)
    return setup.eta*np.stack((1+c,1-c),axis=-1)


def draw_records(method,truth,setup,attempts,rng):
    if attempts<4 or attempts%4:raise ValueError('attempts must be a positive multiple of four')
    n=attempts//4
    if method=='noon':
        probs=quantum_probabilities(truth,setup)
        return np.array([[rng.multinomial(n,row) for row in trial] for trial in probs])
    if method=='coherent':return rng.poisson(n*coherent_means(truth,setup))
    raise ValueError('unknown method')


def estimate(method,records,setup,domain,grid_size=512):
    """Grid MLE with local parabolic refinement; no access to true phase.

    Local: same calibrated [.15,.55] prior for both. Global: coherent searches
    a full 2π, NOON searches one representative π branch. Its missing branch
    is never recovered from the supplied true phase.
    """
    if domain=='local':lo,hi,periodic=.15,.55,False
    elif domain=='global':lo,hi,periodic=(0,np.pi,True) if method=='noon' else (-np.pi,np.pi,True)
    else:raise ValueError('domain')
    grid=np.linspace(lo,hi,grid_size,endpoint=not periodic)
    if method=='noon':weights=np.log(np.maximum(quantum_probabilities(grid,setup),1e-300))
    else:
        # Total expected counts are independent of phase, so the omitted -mu
        # contribution is a constant even after aggregation over all settings.
        weights=np.log(np.maximum(coherent_means(grid,setup),1e-300))
    likelihood=records.reshape(len(records),-1)@weights.reshape(grid_size,-1).T
    return refine_peak(likelihood,grid,lo,hi,periodic)


def estimate_hybrid(quantum_records,classical_records,setup,domain,grid_size=512):
    """Joint likelihood: a charged coherent coarse record resolves the π branch."""
    if domain=='local':lo,hi,periodic=.15,.55,False
    elif domain=='global':lo,hi,periodic=-np.pi,np.pi,True
    else:raise ValueError('domain')
    grid=np.linspace(lo,hi,grid_size,endpoint=not periodic)
    q=np.log(np.maximum(quantum_probabilities(grid,setup),1e-300)).reshape(grid_size,-1)
    c=np.log(np.maximum(coherent_means(grid,setup),1e-300)).reshape(grid_size,-1)
    likelihood=quantum_records.reshape(len(quantum_records),-1)@q.T+classical_records.reshape(len(classical_records),-1)@c.T
    return refine_peak(likelihood,grid,lo,hi,periodic)


def refine_peak(likelihood,grid,lo,hi,periodic):
    grid_size=len(grid)
    k=np.argmax(likelihood,axis=1);rows=np.arange(len(likelihood));step=grid[1]-grid[0]
    kl=(k-1)%grid_size;kr=(k+1)%grid_size
    yl,y0,yr=likelihood[rows,kl],likelihood[rows,k],likelihood[rows,kr]
    denom=yl-2*y0+yr
    shift=np.divide(.5*(yl-yr),denom,out=np.zeros_like(denom),where=abs(denom)>1e-20)
    shift=np.clip(shift,-.5,.5)
    if not periodic:shift[(k==0)|(k==grid_size-1)]=0
    estimates=grid[k]+step*shift
    if periodic:estimates=lo+(estimates-lo)%(hi-lo)
    return estimates


def fisher_information(method,setup,phi=.35):
    """Finite-difference FI per clock at a regular calibrated phase (default .35).

    Exactly dark outcomes have zero probability and are omitted by this numeric
    routine. At such nonregular nodes its pointwise result need not equal the
    continuous-limit reference formulas 2*eta and 4*p*eta**2.
    """
    step=1e-6
    fun=quantum_probabilities if method=='noon' else coherent_means
    probs=fun(phi,setup)[0];derivative=(fun(phi+step,setup)[0]-fun(phi-step,setup)[0])/(2*step)
    return float(np.divide(derivative**2,probs,out=np.zeros_like(probs),where=probs>1e-15).sum(axis=1).mean())


def resources(method,setup,attempts):
    p=setup.preparation_success if method=='noon' else 1.
    photons=2*p*attempts
    return {'attempted_clocks':attempts,'sample_incident_mean_photons_before_object':photons,
            'mean_photons_after_object':photons*setup.object_transmission,
            'mean_detected_photons':photons*setup.eta,
            'elapsed_seconds_at_assumed_clock':attempts/setup.attempted_clock_hz,
            'classical_fisher_information_per_attempt':fisher_information(method,setup),
            'local_unbiased_cramer_rao_sd':1/np.sqrt(attempts*fisher_information(method,setup)) if setup.eta>0 else None}


def wrap(error,period=2*np.pi):return (np.asarray(error)+period/2)%period-period/2


def errors_report(estimates,truth):
    err=wrap(estimates-truth);squared=err**2;n=len(err)
    mse=float(squared.mean());se=float(squared.std(ddof=1)/np.sqrt(n));z=1.959963984540054
    branch=float(np.mean(abs(err)>np.pi/2));center=(branch+z*z/(2*n))/(1+z*z/n)
    half=z*np.sqrt(branch*(1-branch)/n+z*z/(4*n*n))/(1+z*z/n)
    return {'rmse_full_2pi_rad':float(np.sqrt(mse)),
        'rmse_mc_interval95_rad':[float(np.sqrt(max(0,mse-z*se))),float(np.sqrt(mse+z*se))],
        'mean_signed_wrapped_error_rad':float(err.mean()),'mae_full_2pi_rad':float(abs(err).mean()),
        'rmse_modulo_pi_rad':float(np.sqrt(np.mean(wrap(estimates-truth,np.pi)**2))),
        'wrong_pi_branch_rate':branch,'wrong_pi_branch_wilson95':[max(0,center-half),min(1,center+half)],
        'error_quantiles_rad':np.quantile(err,[.025,.5,.975]).tolist(),
        'boundary_rate_local_interval':float(np.mean((estimates<=.1500001)|(estimates>=.5499999)))}
