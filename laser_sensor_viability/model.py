"""Optical Ramsey and conventional receiver surrogate, entirely synthetic.

The source is a classical coherent drive. Atoms are unentangled, reset each
cycle, and sampled from Bloch-model Born probabilities. No QPU is used.
"""
from dataclasses import dataclass, asdict, replace
import numpy as np


@dataclass(frozen=True)
class Config:
    wavelength_nm: float = 698.0
    atoms: int = 64
    pulse_s: float = .0025
    dark_s: float = .020
    cycle_s: float = 1.0
    cycles: int = 128
    t1_s: float = 100.0
    t2_s: float = .200
    preparation_error: float = .01
    readout_01: float = .02
    readout_10: float = .04
    source_photons_per_cycle: float = 2e10
    diode_fraction: float = .10
    detector_efficiency: float = .8
    diode_dark_electrons: float = 100.0
    diode_electronic_noise_electrons: float = 300.0
    phase_electronics_rad: float = .003
    pulse_lightshift_hz_per_relative_power: float = 3.0
    coherent_amplitude_coupling_hz: float = .20
    source_frequency_ou_sd_hz: float = .08
    source_frequency_ou_time_s: float = 8.0
    primary_reference_rw_hz_per_sqrt_s: float = .04
    secondary_reference_rw_hz_per_sqrt_s: float = .01
    atomic_reference_rw_hz_per_sqrt_s: float = .01
    common_path_ou_sd_hz: float = .025
    intensity_ou_sd: float = .015
    diode_gain_ou_sd: float = .002
    fault_step_hz: float = .5

    @property
    def interrogation_s(self):
        return 2 * self.pulse_s + self.dark_s

    def validate(self):
        if not (self.atoms >= 1 and self.cycles >= 4 and self.cycles % 2 == 0):
            raise ValueError('positive atom count and even cycle count >=4 required')
        if not 0 < self.interrogation_s <= self.cycle_s:
            raise ValueError('cycle must contain both pulses and dark evolution')
        if not (0 < self.t2_s <= 2 * self.t1_s):
            raise ValueError('T2 must be positive and <=2*T1')
        if not (0 <= self.preparation_error <= 1 and
                0 <= self.readout_01 <= 1 and 0 <= self.readout_10 <= 1):
            raise ValueError('invalid preparation/readout probability')
        if not (0 < self.detector_efficiency <= 1 and
                0 < self.diode_fraction < 1 and self.source_photons_per_cycle > 0):
            raise ValueError('invalid optical resource')


def decay(r, duration, t1, t2):
    out = np.array(r, dtype=float, copy=True)
    out[..., :2] *= np.exp(-duration / t2)
    out[..., 2] = -1 + (out[..., 2] + 1) * np.exp(-duration / t1)
    return out


def rotate(r, omega_x, omega_y, omega_z, duration):
    """Exact coherent Bloch rotation for a constant Hamiltonian H=hbar*w.s/2."""
    shape = np.broadcast_shapes(np.shape(omega_x), np.shape(omega_y), np.shape(omega_z))
    w = np.stack([np.broadcast_to(x, shape) for x in (omega_x, omega_y, omega_z)], axis=-1)
    norm = np.linalg.norm(w, axis=-1)
    u = np.divide(w, norm[..., None], out=np.zeros_like(w), where=norm[..., None] != 0)
    angle = norm * duration
    cosine, sine = np.cos(angle)[..., None], np.sin(angle)[..., None]
    return r * cosine + np.cross(u, r) * sine + u * np.sum(u * r, axis=-1)[..., None] * (1 - cosine)


def pulse(r, detuning_hz, relative_power, phase, config, subdivisions=16):
    """Strang split of coherent drive and Markov T1/T2 damping.

    Sixteen substeps per pulse; independently compared with a full affine Bloch
    matrix exponential in tests. Omega scales with sqrt(optical intensity).
    """
    omega = np.pi / (2 * config.pulse_s) * np.sqrt(relative_power)
    dt = config.pulse_s / subdivisions
    for _ in range(subdivisions):
        r = decay(r, dt / 2, config.t1_s, config.t2_s)
        r = rotate(r, omega * np.cos(phase), omega * np.sin(phase),
                   2 * np.pi * detuning_hz, dt)
        r = decay(r, dt / 2, config.t1_s, config.t2_s)
    return r


def ramsey_probability(detuning_hz, relative_power=1., config=Config(), subdivisions=16):
    """Measured excitation probability, with a quadrature final pi/2 pulse.

    detuning=laser frequency minus atomic transition frequency. The assumed
    probe light shift acts only during the pulses, not during the dark time.
    """
    config.validate()
    delta, power = np.broadcast_arrays(np.asarray(detuning_hz, float),
                                       np.asarray(relative_power, float))
    if not np.isfinite(delta).all() or not np.isfinite(power).all() or np.any(power <= 0):
        raise ValueError('finite detuning and positive relative intensity required')
    r = np.zeros(delta.shape + (3,))
    r[..., 2] = -1 + 2 * config.preparation_error
    pulse_delta = delta - config.pulse_lightshift_hz_per_relative_power * (power - 1)
    r = pulse(r, pulse_delta, power, 0., config, subdivisions)
    r = rotate(r, np.zeros_like(delta), np.zeros_like(delta), 2*np.pi*delta, config.dark_s)
    r = decay(r, config.dark_s, config.t1_s, config.t2_s)
    r = pulse(r, pulse_delta, power, np.pi/2, config, subdivisions)
    born = np.clip((1 + r[..., 2]) / 2, 0, 1)
    return config.readout_01 + (1 - config.readout_01 - config.readout_10) * born


def ou(rng, n, steps, sd, time_s, cycle_s):
    """Stationary sampled Ornstein-Uhlenbeck process with stated marginal SD."""
    rho = np.exp(-cycle_s / time_s)
    out = np.empty((n, steps))
    out[:, 0] = rng.normal(0, sd, n)
    noise = sd * np.sqrt(1-rho*rho)
    for j in range(1, steps):
        out[:, j] = rho * out[:, j-1] + rng.normal(0, noise, n)
    return out


def random_walk(rng, n, steps, sd_per_sqrt_s, cycle_s):
    out = np.cumsum(rng.normal(0, sd_per_sqrt_s*np.sqrt(cycle_s), (n, steps)), axis=1)
    return out - out[:, :1]


def coherent_frequency(rng, detuning, power, photons, config):
    """Strong-LO phase-difference receiver, shot-noise Gaussian approximation.

    Each of two independent phase samples has variance 1/(eta*N) for N total
    signal photons, giving phase-difference variance 2/(eta*N). Electronic
    phase noise is included. This is a specified receiver model, not an
    optimality claim. The independent LO's frequency noise enters detuning.
    """
    phase_sd = np.sqrt(2 / (config.detector_efficiency * photons * power)
                       + config.phase_electronics_rad**2)
    phase = 2*np.pi*config.interrogation_s*(
        detuning + config.coherent_amplitude_coupling_hz*(power-1))
    noisy_phase = phase + rng.normal(size=phase.shape) * phase_sd
    wrapped = np.angle(np.exp(1j*noisy_phase))
    return wrapped / (2*np.pi*config.interrogation_s)


def photodiode(rng, power, gain, config):
    mean_scale = config.source_photons_per_cycle*config.diode_fraction*config.detector_efficiency
    # Huge expected counts: exact Poisson sampling is efficient in NumPy.
    electrons = rng.poisson(mean_scale*power*gain + config.diode_dark_electrons)
    electrons = electrons + rng.normal(0, config.diode_electronic_noise_electrons, power.shape)
    return (electrons-config.diode_dark_electrons)/mean_scale


def difference(y):
    k = y.shape[-1] // 2
    return y[..., k:].mean(axis=-1) - y[..., :k].mean(axis=-1)


def response_calibration(config, seed=511901, repetitions=256):
    """Independent finite calibration of local frequency/power response.

    Known applied calibration detunings and intensities, not heldout latent
    states. Linear response fit is deliberately local, +/-1 Hz and +/-10%.
    """
    rng = np.random.default_rng(seed)
    f, intensity = np.meshgrid(np.linspace(-1, 1, 9), np.linspace(.9, 1.1, 5))
    f, intensity = f.ravel(), intensity.ravel()
    p = ramsey_probability(f, intensity, config)
    observed = rng.binomial(config.atoms*repetitions, p)/(config.atoms*repetitions)
    x = np.column_stack([np.ones(len(f)), f, intensity-1])
    beta = np.linalg.lstsq(x, observed, rcond=None)[0]
    coherent = coherent_frequency(rng, np.repeat(f, repetitions),
                                  np.repeat(intensity, repetitions),
                                  config.source_photons_per_cycle*.45, config)
    coherent = coherent.reshape(len(f), repetitions).mean(axis=1)
    beta_h = np.linalg.lstsq(x, coherent, rcond=None)[0]
    return {'seed':seed, 'repetitions_per_grid_point': repetitions,
            'grid_points':len(f), 'equivalent_quantum_cycles':len(f)*repetitions,
            'equivalent_quantum_scan_duration_s':len(f)*repetitions*config.cycle_s,
            'q_intercept':float(beta[0]),
            'q_slope_per_hz':float(beta[1]), 'q_power_coefficient':float(beta[2]),
            'h_intercept_hz':float(beta_h[0]), 'h_slope':float(beta_h[1]),
            'h_power_coefficient_hz':float(beta_h[2]),
            'calibration_detuning_range_hz':[-1,1], 'calibration_relative_power_range':[.9,1.1]}


def simulate(n, seed, config, response, amplitudes=0., scenario=None, keep_trace=False):
    """Generate paired hypothetical architectures from one set of source paths.

    Features contain observations only. Hidden frequency/reference paths are
    retained exclusively for scoring/visualization, never passed to estimators.
    The source is constant during each 25ms interrogation; no high-frequency
    spectrum or Dick-effect correction is claimed by this low-bandwidth model.
    """
    scenario = scenario or {}
    true_config = replace(config, **scenario.get('config_changes', {}))
    true_config.validate()
    children = np.random.SeedSequence(seed).spawn(12)
    rs = [np.random.default_rng(child) for child in children]
    m = config.cycles
    a = np.broadcast_to(np.asarray(amplitudes, float), (n,))
    waveform = np.zeros(m); waveform[m//2:] = 1
    if scenario.get('ramp', False):
        waveform = np.clip((np.arange(m)-m/4)/(m/2), 0, 1)
    source = ou(rs[0], n,m,config.source_frequency_ou_sd_hz,
                config.source_frequency_ou_time_s,config.cycle_s) + a[:,None]*waveform
    power = np.exp(ou(rs[1], n,m,config.intensity_ou_sd,5.,config.cycle_s)
                   -config.intensity_ou_sd**2/2)
    power *= 1+scenario.get('power_step',0.)*waveform
    primary = random_walk(rs[2],n,m,config.primary_reference_rw_hz_per_sqrt_s,config.cycle_s)
    secondary = random_walk(rs[3],n,m,config.secondary_reference_rw_hz_per_sqrt_s,config.cycle_s)
    atom = random_walk(rs[4],n,m,config.atomic_reference_rw_hz_per_sqrt_s,config.cycle_s)
    rho = scenario.get('primary_atom_reference_correlation',0.)
    if rho:
        # Preserve atomic marginal random-walk variance while correlating it.
        atom = rho*primary*(config.atomic_reference_rw_hz_per_sqrt_s /
                           config.primary_reference_rw_hz_per_sqrt_s)+np.sqrt(1-rho*rho)*atom
    for key, arr in [('primary_step_hz',primary),('atom_step_hz',atom)]:
        arr += rs[5].choice([-1.,1.],n)[:,None]*scenario.get(key,0.)*waveform
    common = ou(rs[6],n,m,config.common_path_ou_sd_hz,5.,config.cycle_s)
    common += rs[5].choice([-1.,1.],n)[:,None]*scenario.get('common_path_step_hz',0.)*waveform
    sampled_source = source+common
    gain = np.exp(ou(rs[7],n,m,config.diode_gain_ou_sd,10.,config.cycle_s)
                  -config.diode_gain_ou_sd**2/2)
    gain *= 1+scenario.get('diode_gain_step',0.)*waveform
    pd = photodiode(rs[7],power,gain,config)
    non_diode_photons = config.source_photons_per_cycle*(1-config.diode_fraction)
    h_full_raw = coherent_frequency(rs[8],sampled_source-primary,power,non_diode_photons,config)
    h_half_raw = coherent_frequency(rs[9],sampled_source-primary,power,non_diode_photons/2,config)
    h_second_raw = coherent_frequency(rs[10],sampled_source-secondary,power,non_diode_photons/2,config)
    qprob = ramsey_probability(sampled_source-atom,power,true_config)
    qfraction = rs[11].binomial(true_config.atoms,qprob)/true_config.atoms
    qhz = (qfraction-response['q_intercept']-response['q_power_coefficient']*(pd-1))/response['q_slope_per_hz']
    def calibrated_h(h):
        return (h-response['h_intercept_hz']-response['h_power_coefficient_hz']*(pd-1))/response['h_slope']
    hfull,hhalf,hsecond = map(calibrated_h,(h_full_raw,h_half_raw,h_second_raw))
    obs = np.column_stack([difference(x) for x in [pd,hfull,hhalf,qhz,hsecond]])
    target = a*difference(waveform)
    trace = None
    if keep_trace:
        trace = {'time_s':(np.arange(m)*config.cycle_s).tolist(),
                 'laser_frequency_hz':source[0].tolist(),
                 'laser_relative_power':power[0].tolist(),
                 'primary_heterodyne_hz':hhalf[0].tolist(),
                 'primary_heterodyne_full_budget_hz':hfull[0].tolist(),
                 'secondary_heterodyne_hz':hsecond[0].tolist(),
                 'quantum_frequency_hz':qhz[0].tolist(),
                 'quantum_excited_fraction':qfraction[0].tolist(),
                 'quantum_excitation_probability':qprob[0].tolist(),
                 'photodiode_relative_power':pd[0].tolist(),
                 'primary_reference_hz':primary[0].tolist(),
                 'secondary_reference_hz':secondary[0].tolist(),
                 'atomic_reference_hz':atom[0].tolist(),
                 'common_path_frequency_hz':common[0].tolist(),
                 'target_frequency_difference_hz':float(target[0]),
                 'feature_vector':obs[0].tolist(),
                 'note':'One fixed positive-injection realization; hidden source/reference paths shown only as simulation truth.'}
    return obs,target,trace


METHODS = [
    {'id':'power_only','label':'Power photodiode','columns':[0],
     'channels':['power'],'resource_note':'10% source photon allocation; frequency-blind negative control.'},
    {'id':'classical','label':'Conventional C','columns':[0,1],
     'channels':['power','primary coherent reference'],
     'resource_note':'10% photodiode +90% primary heterodyne; one external LO.'},
    {'id':'quantum','label':'Atomic Q + power','columns':[0,3],
     'channels':['power','atomic Ramsey'],
     'resource_note':'10% photodiode +45% atomic probe; remaining45% unused; atomic support optics uncounted.'},
    {'id':'classical_quantum','label':'C + atomic Q','columns':[0,2,3],
     'channels':['power','primary coherent reference','atomic Ramsey'],
     'resource_note':'10% photodiode +45% primary heterodyne +45% atomic probe; atomic support optics uncounted.'},
    {'id':'two_classical','label':'C + independent C','columns':[0,2,4],
     'channels':['power','primary coherent reference','independent coherent reference'],
     'resource_note':'10% photodiode +45% primary heterodyne +45% secondary heterodyne; independent LO uncounted.'}]


SCENARIOS = [
    {'id':'nominal','label':'Calibrated laboratory surrogate','description':'Independent references and matched calibrated response.','parameters':{}},
    {'id':'short_coherence','label':'Atomic coherence deteriorates','description':'T2 falls from200ms to12ms; readout errors rise. Frozen calibration is deliberately not updated.',
     'parameters':{'config_changes':{'t2_s':.012,'readout_01':.10,'readout_10':.14}}},
    {'id':'atomic_reference_drift','label':'Atomic reference also drifts','description':'Unknown +/-0.7Hz atomic-transition step occurs in null and fault records. A false alarm means misattributing sensor drift.',
     'parameters':{'atom_step_hz':.7}},
    {'id':'primary_reference_drift','label':'Primary optical reference drifts','description':'Unknown +/-0.7Hz primary-LO step occurs in null and fault records.',
     'parameters':{'primary_step_hz':.7}},
    {'id':'shared_path_drift','label':'Shared optical-path confounder','description':'Unknown +/-0.7Hz sampled-path shift affects every frequency channel; these observations cannot isolate source from common path.',
     'parameters':{'common_path_step_hz':.7}},
    {'id':'power_only_disturbance','label':'Power changes by10%','description':'A10% intensity increase occurs in both null and frequency-fault records. Calibrated cross-sensitivity correction uses observed photodiode data.',
     'parameters':{'power_step':.1}},
    {'id':'correlated_references','label':'Atomic and primary-reference noise correlate','description':'Reference random-walk increments have correlation0.95; frozen nominal fusion assumes the calibration covariance.',
     'parameters':{'primary_atom_reference_correlation':.95}},
    {'id':'gradual_source_change','label':'Unseen gradual source change','description':'Source ramps over the middle half of the record; the estimator and decision boundary remain fixed. Target RMSE is for mean post-minus-pre frequency.',
     'parameters':{'ramp':True}},
]
