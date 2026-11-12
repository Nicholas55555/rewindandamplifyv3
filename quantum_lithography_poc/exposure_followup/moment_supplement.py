"""Derived raw-moment report; reads frozen exposure results without changing them.

G1/G2 here are local normally ordered optical moments before material response.
The optional averaging includes fast phase jitter and the declared cell aperture;
post-activation material blur is deliberately not called an optical moment.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from model import Setup, METHODS, coefficients, transfer, evaluate, photons_per_clock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUTPUTS = ['moments_supplement.json', 'moments_supplement.csv',
           'raw_moments.png', 'MOMENT_SUPPLEMENT.txt']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extremes(c):
    """Continuous phase extrema of c0+c1*cos(phi)+c2*cos(2*phi)."""
    points = [-1., 1.]
    if abs(c[2]) > 1e-30:
        vertex = -c[1] / (4*c[2])
        if -1 < vertex < 1:
            points.append(vertex)
    values = [c[0] + c[1]*x + c[2]*(2*x*x-1) for x in points]
    return max(0., float(min(values))), float(max(values))


def stats(c, source_photons, sample_photons):
    low, high = extremes(c)
    result = {'cosine_coefficients_per_attempt_clock': c.tolist(),
              'phase_mean_per_cell_per_clock': float(c[0]),
              'continuous_phase_peak_per_cell_per_clock': high,
              'continuous_phase_min_per_cell_per_clock': low,
              'visibility': (high-low)/(high+low) if high+low else None}
    for resource, denominator in [('source', source_photons), ('sample', sample_photons)]:
        result[f'per_total_{resource}_photon'] = {
            'mean': float(c[0]/denominator), 'peak': high/denominator,
            'first_harmonic': float(abs(c[1])/denominator),
            'second_harmonic': float(abs(c[2])/denominator)}
    return result


def build(data):
    rows = []
    checks = {'moment_records': 0, 'maximum_photon_conservation_error': 0.,
              'maximum_discrete_fourier_coefficient_error': 0.,
              'maximum_frozen_response_reconstruction_error': 0.,
              'maximum_phase_cycle_identity_error': 0.,
              'maximum_duty_cycle_identity_error': 0.}
    for case in data['cases']:
        s = Setup(**case['setup'])
        # Phase cycling must charge both positive exposures, with half the budget each.
        c1, c2 = coefficients('coherent', s)
        pc1, pc2 = coefficients('phase_cycled', s)
        reversal = np.array([1., -1., 1.])
        cycle_error = max(np.max(abs(pc1-.5*(c1+c1*reversal))),
                          np.max(abs(pc2-.5*(c2+c2*reversal))))
        b1, b2 = coefficients('phase_cycled_burst', s)
        duty_error = max(np.max(abs(b1-pc1)), np.max(abs(b2-10*pc2)))
        checks['maximum_phase_cycle_identity_error'] = max(checks['maximum_phase_cycle_identity_error'], float(cycle_error))
        checks['maximum_duty_cycle_identity_error'] = max(checks['maximum_duty_cycle_identity_error'], float(duty_error))
        assert cycle_error < 1e-14 and duty_error < 1e-14
        for method in METHODS:
            success = s.quantum_success if METHODS[method]['quantum'] else 1.
            budget = photons_per_clock(method, s)
            g1, g2 = coefficients(method, s)
            for stage in ['raw_after_loss', 'fast_jitter_and_pixel_averaged']:
                factor = np.ones(3) if stage == 'raw_after_loss' else transfer(s, include_blur=False)
                a, b = success*g1*factor, success*g2*factor
                y1, y2 = evaluate(a, s.phases), evaluate(b, s.phases)
                assert min(y1.min(), y2.min()) > -1e-13
                conservation_error = abs(y1.sum()-budget['incident_on_sample'])
                checks['maximum_photon_conservation_error'] = max(checks['maximum_photon_conservation_error'], float(conservation_error))
                assert conservation_error < 1e-12
                for c, y in [(a, y1), (b, y2)]:
                    inferred = np.array([y.mean(), 2*np.mean(y*np.cos(s.phases)),
                                         2*np.mean(y*np.cos(2*s.phases))])
                    error = float(np.max(abs(inferred-c)))
                    checks['maximum_discrete_fourier_coefficient_error'] = max(checks['maximum_discrete_fourier_coefficient_error'], error)
                    assert error < 1e-12
                row = {'case': case['id'], 'method': method, 'stage': stage,
                       'success_probability_per_attempt': success,
                       'duty_fraction': METHODS[method]['duty'],
                       'mean_source_photons_per_clock': budget['before_propagation'],
                       'mean_sample_photons_per_clock': budget['incident_on_sample'],
                       'G1': stats(a, budget['before_propagation'], budget['incident_on_sample']),
                       'G2': stats(b, budget['before_propagation'], budget['incident_on_sample']),
                       'cell_G1_per_attempt': y1.tolist(), 'cell_G2_per_attempt': y2.tolist()}
                rows.append(row)
                if stage == 'fast_jitter_and_pixel_averaged':
                    # Only response, not G2 itself, receives the post-activation blur.
                    h = np.arange(3)
                    blur = np.exp(-.5*(h*2*np.pi*s.blur_nm/s.period_nm)**2)
                    response = (s.linear_per_photon*a+s.pair_per_factorial_moment*b)*blur
                    response[0] += s.background_per_cell_clock
                    frozen = case['methods'][method]['equal_sample_photons']['response_cosine_coefficients_per_clock']
                    error = float(np.max(abs(response-frozen)))
                    checks['maximum_frozen_response_reconstruction_error'] = max(checks['maximum_frozen_response_reconstruction_error'], error)
                    assert error < 1e-19
                    # Failed vacuum preparations scale moments and photons equally.
                    assert np.allclose(a/budget['incident_on_sample'], g1*factor/(s.eta_a+s.eta_b), rtol=1e-12, atol=1e-14)
                    assert np.allclose(b/budget['incident_on_sample'], g2*factor/(s.eta_a+s.eta_b), rtol=1e-12, atol=1e-14)
    checks['moment_records'] = len(rows)
    checks['passed'] = True
    return rows, checks


def plot(rows, data):
    colors = {'noon':'#157e95', 'mixture':'#777e82', 'coherent':'#a98b42',
              'phase_cycled':'#be7621', 'phase_cycled_burst':'#6d54a3'}
    labels = {'noon':'NOON', 'mixture':'Incoherent pair', 'coherent':'Coherent, one phase',
              'phase_cycled':'Coherent, phase cycled', 'phase_cycled_burst':'Phase cycled, 10% duty'}
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    fig, axes = plt.subplots(2, 3, figsize=(15.6, 8.2))
    for row_i, (case_id, stage, title) in enumerate([
        ('ideal_pair_only', 'raw_after_loss', 'Unit transmission; no averaging'),
        ('finite_nominal', 'fast_jitter_and_pixel_averaged', 'Nominal: 80% transmission; fast jitter + pixel averaging')]):
        case = next(c for c in data['cases'] if c['id']==case_id)
        s = Setup(**case['setup'])
        phase = np.linspace(0, 2*np.pi, 801)
        x = phase*s.period_nm/(2*np.pi)
        subset = {r['method']: r for r in rows if r['case']==case_id and r['stage']==stage}
        for method in ['noon', 'coherent']:
            r = subset[method]
            y = evaluate(r['G1']['cosine_coefficients_per_attempt_clock'], phase)/r['mean_sample_photons_per_clock']
            label = 'NOON = mixture = both phase cycles' if method=='noon' else labels[method]
            axes[row_i,0].plot(x, y, lw=2, color=colors[method], label=label)
        for col, methods in [(1, ['noon','mixture','coherent','phase_cycled']),
                             (2, ['noon','phase_cycled','phase_cycled_burst'])]:
            for method in methods:
                r = subset[method]
                y = 1000*evaluate(r['G2']['cosine_coefficients_per_attempt_clock'], phase)/r['mean_sample_photons_per_clock']
                axes[row_i,col].plot(x, y, lw=2, color=colors[method],
                                     ls='--' if method=='mixture' else '-', label=labels[method])
        axes[row_i,0].set_ylabel('G1 / total sample photons')
        for col in [1,2]:
            axes[row_i,col].set_ylabel('10³ × G2 / total sample photons')
        for col in range(3):
            axes[row_i,col].set_xlabel('Position within the assumed 800 nm period (nm)')
            axes[row_i,col].set_ylim(bottom=0)
            axes[row_i,col].set_xlim(0,800)
            axes[row_i,col].grid(alpha=.14)
            axes[row_i,col].legend(fontsize=8, loc='upper right')
        axes[row_i,0].text(0,1.20,title,transform=axes[row_i,0].transAxes,
                          fontsize=11,weight='bold')
    for col, title in enumerate(['First-order intensity', 'Pair moment: same average photons', 'Higher allowed peak brightness']):
        axes[0,col].set_title(title, pad=10)
    fig.suptitle('Optical moments before material response — fixed 32-cell geometry',fontsize=15,y=.985)
    fig.text(.5,.022,'Per-photon normalization divides each local moment by photons incident on all 32 cells. G2 is not an event probability.\n'
             'Phase cycling charges both exposures. The 10% duty reference uses 10× peak brightness. No material blur, resist model or fabrication result is plotted.',
             ha='center',fontsize=10)
    fig.subplots_adjust(left=.065,right=.985,top=.85,bottom=.13,wspace=.27,hspace=.50)
    fig.savefig(HERE/'raw_moments.png',dpi=180)
    plt.close(fig)


def write_csv(rows):
    flat = []
    for r in rows:
        out = {k:r[k] for k in ['case','method','stage','success_probability_per_attempt',
                               'duty_fraction','mean_source_photons_per_clock','mean_sample_photons_per_clock']}
        for name in ['G1','G2']:
            m = r[name]
            for i, c in enumerate(m['cosine_coefficients_per_attempt_clock']):
                out[f'{name}_cosine_h{i}_per_clock'] = c
            out[f'{name}_visibility'] = m['visibility']
            for resource in ['source','sample']:
                for metric,value in m[f'per_total_{resource}_photon'].items():
                    out[f'{name}_{metric}_per_total_{resource}_photon'] = value
        flat.append(out)
    with (HERE/'moments_supplement.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)


def main():
    for name in OUTPUTS:
        if (HERE/name).exists():
            raise FileExistsError(f'Refusing to replace supplementary output: {name}')
    frozen = HERE/'results.json'
    frozen_hash = sha(frozen)
    data = json.loads(frozen.read_text(encoding='utf-8'))
    rows, checks = build(data)
    provenance = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
                  for p in [Path(__file__).resolve(), HERE/'model.py', HERE/'test_model.py', frozen]}
    plot(rows,data)
    write_csv(rows)
    text = '''RAW OPTICAL-MOMENT SUPPLEMENT (derived only)

This supplement reads the nine frozen exposure setups and all five source methods.
No experiment was rerun, no finite-count data added, and no original file changed.
The 90 rows are 9 cases x 5 methods x 2 averaging conventions, not new trials.

G1=<n> and G2=<n(n-1)> describe one of the 32 fixed spatial cells. They are
dimensionless number moments per attempted clock, not photon probabilities or
material activation counts. Harmonic h is the coefficient of cos(h*phase).
The tables give raw-after-loss coefficients and fast-jitter/pixel-averaged ones.
Material blur acts AFTER activation and is excluded from the plotted moments.
Its contribution to the saved activation field was independently reconstructed.

The source denominator counts all mean emitted photons before propagation loss;
the sample denominator counts mean incident photons summed over all 32 cells.
Consequently G1/sample_photons sums to one across cells. G2/sample_photons is a
response-relevant ratio, NOT a pair-event probability or a universal efficiency.
The per-cell mean is a spatial/phase mean; peak is the continuous phase maximum.
The raw JSON also stores the actual 32 cell values and both cosine coefficients.

For p<1, failed quantum preparation emits vacuum but still charges clock time.
Per-clock moments and photons both scale with p; their ratio cancels p. This
does NOT mean source inefficiency is free: matching photon dose takes longer,
and a per-clock material background accumulates longer, as the original study
shows. Pump/herald energy is unknown and excluded. Both positive phase-cycle
exposures are charged at half the budget; there is no dose subtraction.
The 10%-duty comparator retains the mean photons but uses 10x peak intensity;
its pair moment is 10x larger. This is a declared extra peak-power allowance,
not an optimized bound over all classical sources.

The figure's first row uses unit transmission, no jitter and no aperture average;
the second uses 0.8 transmission in each arm, 0.15 rad fast Gaussian jitter and
one-cell aperture averaging. The 40 nm post-activation blur is intentionally not
shown as optical G2. Slow correlated phase drift is outside the mean-rate model.
The assumed wavelength is 800 nm and the illustrative period is 800 nm, not EUV.

Numerical checks: positivity, summed G1 conservation, independent discrete
Fourier recovery, two-exposure phase averaging, duty-factor accounting, source
success normalization, and exact reconstruction of all 45 frozen response
coefficient sets. The original ten tests include independent loss/Fock checks.
No new scientific claim or fabrication validation follows from this supplement.

Reproduce with the study's recorded environment: python moment_supplement.py
The script refuses to overwrite its four outputs. Copy the input directory or
use a fresh output destination to rerun; original results and source stay fixed.
'''
    (HERE/'MOMENT_SUPPLEMENT.txt').write_text(text,encoding='utf-8')
    result = {'schema':'exposure-raw-moment-supplement-v1',
              'scope':'Derived moments from frozen cases; no new experimental or Monte Carlo evidence.',
              'environment':{'python':sys.version,'numpy':np.__version__,'matplotlib':matplotlib.__version__},
              'units':{'G1':'local mean photons per attempted clock',
                       'G2':'local factorial moment per attempted clock, not an event probability',
                       'harmonics':'signed cosine coefficients; amplitude columns take absolute value',
                       'denominator':'total mean source or sample photons over all cells per attempted clock'},
              'checks':checks,'source_sha256':provenance,
              'artifact_sha256':{n:sha(HERE/n) for n in OUTPUTS if n!='moments_supplement.json'},
              'records':rows}
    (HERE/'moments_supplement.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert sha(frozen)==frozen_hash
    print(json.dumps({'checks':checks,'unchanged_original_results_sha256':frozen_hash,
                      'supplement_sha256':sha(HERE/'moments_supplement.json')},indent=2))


if __name__=='__main__':
    main()
