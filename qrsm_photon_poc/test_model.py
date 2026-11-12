"""Numerical tests that do not rely on optional test frameworks."""
from dataclasses import replace
import numpy as np
from qrsm_photon import Parameters, hamiltonian, init_state, instruments, sample_records, record_loglikelihood, tests


def assert_physical(p):
    no, yes, total = instruments(p)
    n=4*p.n_cavity
    assert np.allclose(no+yes,total,atol=1e-9)
    assert np.allclose(hamiltonian(p),hamiltonian(p).conj().T)
    rng=np.random.default_rng(123)
    for _ in range(12):
        psi=rng.normal(size=n)+1j*rng.normal(size=n)
        psi=psi/np.linalg.norm(psi)
        rho=np.outer(psi,psi.conj()).reshape(-1,order='F')
        for channel in [no,yes]:
            res=(channel@rho).reshape((n,n),order='F')
            assert np.max(np.abs(res-res.conj().T)) < 1e-8
            assert np.linalg.eigvalsh(res).min()>-1e-8
        rest=(total@rho).reshape((n,n),order='F')
        assert abs(np.trace(rest)-1)<1e-8


def main():
    assert tests()
    for n in (2,3):
        p=replace(Parameters(),n_cavity=n)
        assert_physical(p)
    p=Parameters()
    a=sample_records(p, n_records=8, steps=12,seed=4)
    b=sample_records(p, n_records=8, steps=12,seed=4)
    assert np.array_equal(a,b)
    assert np.isfinite(record_loglikelihood(a,p))
    assert np.isfinite(record_loglikelihood(a,replace(p,g_defect=0)))
    print('All numerical tests passed (CPTP, CP outcomes, reproducibility, likelihood).')

if __name__=='__main__': main()
