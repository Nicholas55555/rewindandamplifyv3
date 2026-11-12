"""Physics, observation-statistics, and inference checks for the surrogate."""
from dataclasses import replace
import unittest
import numpy as np
from model import (Config, decay, rotate, ramsey_probability, ou, random_walk,
                   coherent_frequency, response_calibration, simulate, difference)
from run_experiment import order_threshold, fit_estimators, estimate


class PhysicsTests(unittest.TestCase):
    def test_unitary_limit_matches_ideal_instantaneous_ramsey(self):
        c=replace(Config(),pulse_s=1e-8,t1_s=np.inf,t2_s=np.inf,
                  preparation_error=0,readout_01=0,readout_10=0,
                  pulse_lightshift_hz_per_relative_power=0)
        delta=np.linspace(-20,20,41)
        expected=(1+np.sin(2*np.pi*delta*c.dark_s))/2
        np.testing.assert_allclose(ramsey_probability(delta,config=c),expected,atol=8.1e-7)

    def test_finite_pulse_frequency_slope(self):
        c=replace(Config(),t1_s=np.inf,t2_s=np.inf,
                  preparation_error=0,readout_01=0,readout_10=0)
        eps=1e-4
        numerical=(ramsey_probability(eps,config=c)-ramsey_probability(-eps,config=c))/(2*eps)
        self.assertAlmostEqual(float(numerical),np.pi*c.dark_s+4*c.pulse_s,places=8)

    def test_readout_confusion_matrix_is_affine(self):
        c=Config(); ideal=replace(c,readout_01=0,readout_10=0)
        d=np.array([-8.,-.5,0,.5,8.])
        np.testing.assert_allclose(ramsey_probability(d,config=c),
                                   c.readout_01+(1-c.readout_01-c.readout_10)*ramsey_probability(d,config=ideal),atol=1e-14)

    def test_completely_random_readout_has_no_detuning_information(self):
        c=replace(Config(),readout_01=.5,readout_10=.5)
        np.testing.assert_array_equal(ramsey_probability(np.linspace(-25,25,100),config=c),np.full(100,.5))

    def test_bloch_decay_relaxes_to_ground_and_keeps_ball(self):
        r=np.array([[0,0,1],[1,0,0],[0,1,0],[0,0,-1.]])
        d=decay(r,5,1,1)
        self.assertTrue(np.all(np.linalg.norm(d,axis=1)<=1+1e-12))
        np.testing.assert_array_equal(d[-1],[0,0,-1])
        self.assertLess(d[0,2],-.98)

    def test_rotation_preserves_norm(self):
        rng=np.random.default_rng(40); r=rng.normal(size=(500,3));r/=np.linalg.norm(r,axis=1)[:,None]
        out=rotate(r,rng.normal(size=500),rng.normal(size=500),rng.normal(size=500),2.2)
        np.testing.assert_allclose(np.linalg.norm(out,axis=1),1,atol=1e-14)

    def test_probability_domain_under_finite_pulse_stress(self):
        c=replace(Config(),t2_s=.012)
        p=ramsey_probability(np.linspace(-50,50,101),np.linspace(.1,2,101),c)
        self.assertTrue(np.all((p>=c.readout_01)&(p<=1-c.readout_10)))

    def test_invalid_decoherence_rejected(self):
        with self.assertRaises(ValueError): replace(Config(),t1_s=.1,t2_s=.3).validate()

    def test_common_frequency_shift_is_unidentifiable(self):
        laser=np.array([-.2,.1,.5]);atom=np.array([.1,-.1,.3]);shift=2.2
        np.testing.assert_allclose(ramsey_probability(laser-atom),ramsey_probability((laser+shift)-(atom+shift)),atol=1e-14)


class SamplingTests(unittest.TestCase):
    def test_projection_noise_variance(self):
        rng=np.random.default_rng(32);n=64;p=.37
        samples=rng.binomial(n,p,100000)/n
        self.assertLess(abs(samples.var()-p*(1-p)/n),.00005)

    def test_coherent_receiver_shot_variance_and_budget_scaling(self):
        c=replace(Config(),phase_electronics_rad=0)
        rng=np.random.default_rng(99);n=150000;photons=1000.
        y=coherent_frequency(rng,np.zeros(n),np.ones(n),photons,c)
        expected=2/(c.detector_efficiency*photons)/(2*np.pi*c.interrogation_s)**2
        self.assertLess(abs(y.var()/expected-1),.015)
        rng=np.random.default_rng(99)
        y2=coherent_frequency(rng,np.zeros(n),np.ones(n),2*photons,c)
        np.testing.assert_allclose(y2,y/np.sqrt(2),atol=1e-14)

    def test_stationary_ou_variance_and_lag(self):
        x=ou(np.random.default_rng(43),10000,20,.2,5.,1.)
        self.assertLess(abs(x.var()/.04-1),.025)
        lag=np.mean(x[:,:-1]*x[:,1:])/.04
        self.assertLess(abs(lag-np.exp(-.2)),.025)

    def test_random_walk_increment_variance(self):
        x=random_walk(np.random.default_rng(19),10000,20,.04,1.)
        self.assertLess(abs(np.diff(x).var()/.04**2-1),.015)
        np.testing.assert_array_equal(x[:,0],0)

    def test_photodiode_frequency_blind_on_paired_source(self):
        c=replace(Config(),cycles=8)
        response=response_calibration(c,repetitions=32)
        a,_,trace0=simulate(10,78,c,response,0.,keep_trace=True)
        b,_,trace1=simulate(10,78,c,response,.5,keep_trace=True)
        np.testing.assert_array_equal(a[:,0],b[:,0])
        np.testing.assert_array_equal(trace0['photodiode_relative_power'],trace1['photodiode_relative_power'])
        np.testing.assert_allclose(np.array(trace1['laser_frequency_hz'])-trace0['laser_frequency_hz'],[0,0,0,0,.5,.5,.5,.5])


class InferenceTests(unittest.TestCase):
    def test_order_statistic_rank(self):
        self.assertEqual(order_threshold(np.arange(99),.05),94)
        self.assertEqual(sum(np.arange(100)>94),5)

    def test_difference_metric(self):
        self.assertEqual(difference(np.array([1.,1.,3.,3.])),2)

    def test_estimator_is_unbiased_under_its_calibrated_response(self):
        rng=np.random.default_rng(8);null=rng.normal(size=(4000,5))
        amplitude=rng.choice([-1.,1.],4000)
        injected=rng.normal(size=(4000,5))+amplitude[:,None]*np.array([0.,1,1,1,1])
        models=fit_estimators(null,injected,amplitude)
        for key,model in models.items():
            if key=='power_only': continue
            self.assertAlmostEqual(np.dot(model['weights'],model['calibrated_response']),1,places=12)
            mu=np.zeros((2,5));mu[:,model['columns']]=np.asarray(model['mean'])
            mu[1,model['columns']]+=np.asarray(model['calibrated_response'])*.5
            np.testing.assert_allclose(estimate(mu,model),[0,.5],atol=1e-14)


if __name__=='__main__':unittest.main()
