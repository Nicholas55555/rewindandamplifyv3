"""QRSM-inspired open quantum emitter--defect--cavity photon-counting simulator.

Stand-alone proof of concept: numpy/scipy only. Not an implementation of the
existing QRSM/Grover circuit or a speedup demonstration.

Tensor order: defect (2), emitter (2), cavity (n_cavity).
Angular frequencies and all rates are in arbitrary consistent inverse-time units.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Iterable
import numpy as np
from scipy.linalg import expm

I2 = np.eye(2, dtype=complex)
SM = np.array([[0, 1], [0, 0]], dtype=complex)
SP = SM.T.conj()
SZ = np.diag([1.0, -1.0]).astype(complex)


def kron3(a, b, c):
    return np.kron(np.kron(a, b), c)


@dataclass(frozen=True)
class Parameters:
    # A rotating-frame open quantum system, inspired by the existing QRSM.
    g_defect: float = 0.65       # coherent defect--emitter exchange
    defect_detuning: float = 0.20
    cavity_detuning: float = 0.0
    g_cavity: float = 0.70       # emitter--cavity coherent exchange
    drive: float = 1.30          # coherent emitter driving Rabi frequency
    kappa: float = 1.40          # photon escape from cavity
    detector_eta: float = 0.68  # detection efficiency in [0,1]
    gamma_emitter: float = 0.07 # emitter relaxation NOT counted by cavity detector
    gamma_defect: float = 0.025 # unmonitored defect relaxation
    gamma_phi_emitter: float = 0.035 # pure dephasing: off-diagonal decay rate
    gamma_phi_defect: float = 0.020
    dark_rate: float = 0.018    # independent false-click Poisson rate
    dt: float = 1.0             # photon-count time bin
    n_cavity: int = 3           # photon Fock space |0>, |1>, |2>; convergence check required

    def validate(self):
        if self.n_cavity < 2:
            raise ValueError('n_cavity must be >= 2')
        for name in ['g_defect','g_cavity','drive','kappa','gamma_emitter',
                     'gamma_defect','gamma_phi_emitter','gamma_phi_defect','dark_rate']:
            if getattr(self,name) < 0:
                raise ValueError(f'{name} must be nonnegative')
        if not (0 <= self.detector_eta <= 1):
            raise ValueError('detector_eta must be between 0 and 1')
        if self.dt <= 0:
            raise ValueError('dt must be positive')


def operators(p: Parameters):
    n = p.n_cavity
    ic = np.eye(n, dtype=complex)
    a = np.zeros((n,n), dtype=complex)
    for k in range(1,n):
        a[k-1,k] = np.sqrt(k)
    d = kron3(SM, I2, ic)
    e = kron3(I2, SM, ic)
    cav = kron3(I2, I2, a)
    zd = kron3(SZ, I2, ic)
    ze = kron3(I2, SZ, ic)
    return d,e,cav,zd,ze


def hamiltonian(p: Parameters):
    d,e,a,_,_ = operators(p)
    nd, na = d.conj().T @ d, a.conj().T @ a
    H = (p.defect_detuning * nd + p.cavity_detuning * na
         + 0.5*p.drive*(e + e.conj().T)
         + p.g_defect*(d.conj().T@e + e.conj().T@d)
         + p.g_cavity*(e.conj().T@a + a.conj().T@e))
    assert np.allclose(H,H.conj().T)
    return H


def lindblad_super(H: np.ndarray, collapse: Iterable[np.ndarray]):
    """Column-vectorized density matrix superoperator, vec(A X B)= (B.T kron A) vec(X)."""
    n=H.shape[0]
    eye=np.eye(n, dtype=complex)
    L=-1j*(np.kron(eye,H)-np.kron(H.T,eye))
    for c in collapse:
        cdc=c.conj().T@c
        L+= np.kron(c.conj(),c) - 0.5*(np.kron(eye,cdc)+np.kron(cdc.T,eye))
    return L


def instruments(p: Parameters):
    """Exact binary time-bin instruments: 0 detected photons vs >=1 detected.

    The full Lindblad propagator includes all jumps, while the no-count
    generator omits detected-photon recycling; unobserved losses remain.
    E1 = E_full - E0, which sums all detected-count trajectories >=1.
    Independent detector dark counts multiply E0 by exp(-dark_rate*dt).
    """
    p.validate()
    H=hamiltonian(p)
    d,e,a,zd,ze=operators(p)
    jumps=[np.sqrt(p.kappa*p.detector_eta)*a]
    other=[np.sqrt(p.kappa*(1-p.detector_eta))*a,
           np.sqrt(p.gamma_emitter)*e,
           np.sqrt(p.gamma_defect)*d,
           np.sqrt(p.gamma_phi_emitter/2)*ze,
           np.sqrt(p.gamma_phi_defect/2)*zd]
    Ltotal=lindblad_super(H,jumps+other)
    Lno=lindblad_super(H,other)
    c=jumps[0]
    cdc=c.conj().T@c
    n=H.shape[0]
    eye=np.eye(n, dtype=complex)
    Lno-=0.5*(np.kron(eye,cdc)+np.kron(cdc.T,eye))
    full=expm(p.dt*Ltotal)
    no=np.exp(-p.dark_rate*p.dt)*expm(p.dt*Lno)
    click=full-no
    return no, click, full


def init_state(p: Parameters):
    v=np.zeros(4*p.n_cavity, dtype=complex)
    v[0]=1 # |0_defect 0_emitter 0_cavity>
    return np.outer(v,v.conj()).reshape(-1,order='F')


def _traces(states: np.ndarray, dimension: int) -> np.ndarray:
    # For each column, select diagonal entries in column-major vec(rho).
    return np.real(states[np.arange(dimension)*(dimension+1),:].sum(axis=0))


def sample_records(p: Parameters, n_records=120, steps=34, seed=2026):
    """Sample binary photon detection records from quantum trajectory instruments.

    A click denotes >=1 detected photons in the bin, including dark counts.
    Tracks conditional mixed states without directly measuring emitter/defect.
    """
    rng=np.random.default_rng(seed)
    no, click, _=instruments(p)
    dim=4*p.n_cavity
    state=np.tile(init_state(p)[:,None],(1,n_records))
    history=np.empty((n_records,steps),dtype=np.uint8)
    for t in range(steps):
        s0=no@state
        p0=np.clip(_traces(s0,dim),0,1)
        hit=rng.random(n_records)>=p0
        s1=click@state
        p1=np.clip(_traces(s1,dim),0,1)
        prob=np.where(hit,p1,p0)
        if np.any(prob<1e-14):
            raise FloatingPointError('Sampled near-zero probability branch')
        state=np.where(hit[None,:],s1,s0)/prob[None,:]
        history[:,t]=hit
    return history


def record_loglikelihood(records, p: Parameters):
    """Exact forward likelihood for binary observations under this finite model."""
    records=np.asarray(records,dtype=np.uint8)
    if records.ndim!=2 or not np.all((records==0)|(records==1)):
        raise ValueError('records must be a 2D binary array')
    no,click,_=instruments(p)
    dim=4*p.n_cavity
    n,steps=records.shape
    states=np.tile(init_state(p)[:,None],(1,n))
    logps=np.zeros(n)
    for t in range(steps):
        hits=records[:,t].astype(bool)
        nxt0=no@states
        nxt1=click@states
        nxt=np.where(hits[None,:],nxt1,nxt0)
        probs=_traces(nxt,dim)
        if np.any(probs < -1e-8):
            raise FloatingPointError('Negative observation probability')
        probs=np.maximum(probs,1e-300)
        logps+=np.log(probs)
        states=nxt/probs[None,:]
    return float(logps.sum())


def fit_coupling(records, base:Parameters, grid=None):
    if grid is None:
        grid=np.linspace(0.0,1.25,26)
    grid=np.asarray(grid,dtype=float)
    ll=np.array([record_loglikelihood(records,replace(base,g_defect=float(g))) for g in grid])
    best=int(np.argmax(ll))
    return {'grid':grid,'log_likelihood':ll,'g_hat':float(grid[best]),
            'llr_vs_no_defect':float(ll[best]-ll[0]), 'best_index':best}


def conditional_click_probability(records, max_lag=8):
    """Empirical P(click t+lag | click t), and unconditional click baseline.

    This is a descriptive statistic, not a test proving entanglement.
    """
    records=np.asarray(records,dtype=np.uint8)
    base=float(records.mean())
    x=[]
    for lag in range(1,max_lag+1):
        past=records[:,:-lag].ravel().astype(bool)
        future=records[:,lag:].ravel()
        x.append(float(future[past].mean()) if past.sum() else np.nan)
    return base,np.array(x)


def tests():
    p=Parameters(n_cavity=2)
    no,yes,total=instruments(p)
    assert np.linalg.norm(no+yes-total)<1e-9
    d=4*p.n_cavity
    state=init_state(p)
    norm=_traces(total@state[:,None],d)[0]
    assert abs(norm-1)<1e-9
    for branch in (no,yes):
        out=(branch@state).reshape((d,d),order='F')
        assert np.linalg.norm(out-out.conj().T)<1e-8
        assert np.linalg.eigvalsh(out).min()>-1e-9
    a=sample_records(p,n_records=6,steps=6,seed=12)
    assert a.shape==(6,6) and set(np.unique(a)).issubset({0,1})
    assert np.isfinite(record_loglikelihood(a,p))
    assert np.linalg.norm(hamiltonian(p)-hamiltonian(p).conj().T)<1e-10
    return True

if __name__=='__main__':
    print('self-tests:',tests())
    p=Parameters()
    sample=sample_records(p, n_records=20,steps=20)
    print('click fraction:',float(sample.mean()),'log-likelihood:',record_loglikelihood(sample,p))
