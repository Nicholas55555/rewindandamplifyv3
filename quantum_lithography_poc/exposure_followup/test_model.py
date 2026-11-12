"""Independent operator, loss, integration, resource and sampling checks."""
import unittest
from dataclasses import replace
from math import comb
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.stats import poisson
from model import (Setup,METHODS,coefficients,evaluate,transfer,event_rates,
                   photons_per_clock,exposure,simulate_counts,weak_response_bound)


def loss_operators(eta,n=3):
    result=[]
    for lost in range(n):
        k=np.zeros((n,n))
        for initial in range(lost,n):
            k[initial-lost,initial]=np.sqrt(comb(initial,lost)*(1-eta)**lost*eta**(initial-lost))
        result.append(k)
    return result


class ModelTests(unittest.TestCase):
    def test_spatial_mode_columns_are_orthogonal_and_conserve_dose(self):
        s=Setup()
        u=np.c_[np.ones(s.cells),np.exp(1j*s.phases)]/np.sqrt(s.cells)
        np.testing.assert_allclose(u.conj().T@u,np.eye(2),atol=1e-15)
        for eta in [(1,1),(.2,.9),(0,.5),(0,0)]:
            for method in METHODS:
                setup=replace(s,eta_a=eta[0],eta_b=eta[1])
                g1,_=coefficients(method,setup)
                self.assertAlmostEqual(evaluate(g1,setup.phases).sum(),sum(eta))

    def test_quantum_moments_against_independent_loss_kraus_calculation(self):
        destroy=np.diag(np.sqrt([1.,2.]),1)
        a=np.kron(destroy,np.eye(3));b=np.kron(np.eye(3),destroy)
        psi=np.zeros(9,complex);psi[6]=psi[2]=1/np.sqrt(2)
        for method in ['noon','mixture']:
            rho=np.outer(psi,psi.conj())
            if method=='mixture':rho=np.diag(np.diag(rho))
            for ea,eb in [(1,1),(.2,.9),(0,.6),(0,0)]:
                s=Setup(eta_a=ea,eta_b=eb)
                mixed=np.zeros_like(rho,dtype=complex)
                for ka in loss_operators(ea):
                    for kb in loss_operators(eb):
                        k=np.kron(ka,kb);mixed+=k@rho@k.conj().T
                self.assertAlmostEqual(np.trace(mixed).real,1)
                g1,g2=coefficients(method,s)
                for phi in np.linspace(0,2*np.pi,17):
                    c=(a+np.exp(1j*phi)*b)/np.sqrt(s.cells)
                    observed1=np.trace(mixed@c.conj().T@c).real
                    observed2=np.trace(mixed@c.conj().T@c.conj().T@c@c).real
                    self.assertAlmostEqual(observed1,evaluate(g1,[phi])[0])
                    self.assertAlmostEqual(observed2,evaluate(g2,[phi])[0])

    def test_classical_phase_cycle_and_duty_charge_every_exposure(self):
        s=Setup(eta_a=.4,eta_b=.8)
        for method in ['coherent','phase_cycled','phase_cycled_burst']:
            duty=METHODS[method]['duty']
            phases=[0] if method=='coherent' else [0,np.pi]
            intensity=np.array([abs((np.sqrt(s.eta_a)+np.exp(1j*(s.phases+offset))*np.sqrt(s.eta_b))/np.sqrt(s.cells*duty))**2 for offset in phases])
            g1,g2=coefficients(method,s)
            np.testing.assert_allclose(evaluate(g1,s.phases),duty*intensity.mean(axis=0),atol=1e-15)
            np.testing.assert_allclose(evaluate(g2,s.phases),duty*(intensity**2).mean(axis=0),atol=1e-15)

    def test_jitter_matches_independent_gaussian_quadrature(self):
        s=replace(Setup(),jitter_rad=.43,blur_nm=0,pixel_average=False)
        nodes,weights=hermgauss(60)
        for method in METHODS:
            _,g2=coefficients(method,s)
            quadrature=np.array([evaluate(g2,s.phases+np.sqrt(2)*s.jitter_rad*x) for x in nodes])
            np.testing.assert_allclose(weights@quadrature/np.sqrt(np.pi),evaluate(g2*transfer(s),s.phases),atol=1e-14)

    def test_blur_and_pixel_averaging_match_numeric_integrals(self):
        s=replace(Setup(),jitter_rad=0,blur_nm=61)
        x=np.linspace(-8*s.blur_nm,8*s.blur_nm,10001)
        w=np.exp(-x*x/(2*s.blur_nm*s.blur_nm));w/=w.sum()
        offset=np.linspace(-np.pi/s.cells,np.pi/s.cells,10001)
        for h in [0,1,2]:
            blur=w@np.cos(h*2*np.pi*x/s.period_nm)
            pixel=np.trapezoid(np.cos(h*offset),offset)/(2*np.pi/s.cells)
            self.assertAlmostEqual(blur*pixel,transfer(s)[h],places=9)

    def test_old_normalized_output_limit(self):
        s=replace(Setup(),eta_a=1,eta_b=1,jitter_rad=0,blur_nm=0,pixel_average=False)
        _,n=coefficients('noon',s);_,c=coefficients('coherent',s)
        np.testing.assert_allclose(evaluate(n,s.phases)*s.cells**2/4,.5*(1+np.cos(2*s.phases)),atol=1e-14)
        np.testing.assert_allclose(evaluate(c,s.phases)*s.cells**2/4,(1+np.cos(s.phases))**2,atol=1e-14)

    def test_equal_photon_budget_costs_more_attempts_when_preparation_fails(self):
        s=replace(Setup(),quantum_success=.02)
        q=exposure('noon',s,1e7/.02);c=exposure('phase_cycled',s,1e7)
        self.assertEqual(q['sample_incident_photons'],c['sample_incident_photons'])
        self.assertAlmostEqual(q['seconds']/c['seconds'],50)
        qfast=exposure('noon',s,1e7)
        self.assertAlmostEqual(qfast['sample_incident_photons']/c['sample_incident_photons'],.02)

    def test_poisson_statistics_and_threshold_are_independently_correct(self):
        s=Setup();e=exposure('noon',s,1e7)
        bright=np.cos(2*s.phases)>=.7;dark=np.cos(2*s.phases)<=-.7
        tails=poisson.sf(s.threshold_events-1,e['cell_mean_events'])
        expected=np.r_[tails[bright],1-tails[dark]].mean()
        self.assertAlmostEqual(expected,e['guard_cell_accuracy'])
        mc=simulate_counts('noon',s,1e7,20000,12345)
        se=mc['harmonic_empirical_sd']/np.sqrt(20000)
        self.assertLess(abs(mc['harmonic_empirical_mean']-e['second_harmonic_events_per_cell']),5*se)
        self.assertLess(abs(mc['harmonic_empirical_sd']/e['second_harmonic_poisson_sd']-1),.03)
        self.assertLess(abs(mc['guard_accuracy_empirical']-expected),5*mc['guard_accuracy_mean_mc_se'])

    def test_loss_limits_and_weak_response(self):
        for method in METHODS:
            s=replace(Setup(),eta_a=0,eta_b=0)
            self.assertTrue(np.all(event_rates(method,s)[0]==0))
            self.assertTrue(weak_response_bound(method,Setup())['weak_regime_pass'])
        s=replace(Setup(),linear_per_photon=0,jitter_rad=0,blur_nm=0,pixel_average=False)
        self.assertAlmostEqual(exposure('noon',s,1e7)['event_visibility'],1)
        self.assertAlmostEqual(exposure('phase_cycled',s,1e7)['event_visibility'],1/3)
        self.assertAlmostEqual(exposure('mixture',s,1e7)['event_visibility'],0)

    def test_invalid_inputs(self):
        for changes in [dict(eta_a=-.1),dict(cells=7),dict(quantum_success=0),dict(blur_nm=-1),dict(jitter_rad=np.nan)]:
            with self.assertRaises(ValueError):coefficients('noon',replace(Setup(),**changes))


if __name__=='__main__':unittest.main()
