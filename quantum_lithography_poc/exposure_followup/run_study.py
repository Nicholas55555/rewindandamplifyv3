"""Reproducible finite sensitivity study. Writes only this new followup directory."""
from dataclasses import asdict,replace
from pathlib import Path
import csv,hashlib,json,platform,sys
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import (Setup,METHODS,coefficients,transfer,evaluate,event_rates,
                   exposure,optimized_threshold_exposure,simulate_counts,
                   photons_per_clock,weak_response_bound)

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
SEED=2026111009
REPETITIONS=6000
BASE_CLOCKS=10_000_000


def compact(row):
    return {k:v for k,v in row.items() if k not in ('cell_mean_events','response_cosine_coefficients_per_clock')}


def build():
    base=Setup()
    variants={
        'ideal_pair_only':replace(base,eta_a=1,eta_b=1,jitter_rad=0,blur_nm=0,pixel_average=False,linear_per_photon=0),
        'finite_nominal':base,
        'low_transmission':replace(base,eta_a=.2,eta_b=.2),
        'asymmetric_arms':replace(base,eta_a=.8,eta_b=.1),
        'large_blur':replace(base,blur_nm=120),
        'phase_instability':replace(base,jitter_rad=.6),
        'linear_dominated':replace(base,linear_per_photon=2e-4),
        'one_percent_source':replace(base,quantum_success=.01),
        'one_percent_source_with_background':replace(base,quantum_success=.01,background_per_cell_clock=1e-7),
    }
    cases=[]
    for index,(name,s) in enumerate(variants.items()):
        item={'id':name,'setup':asdict(s),'classical_fringe_period_nm':s.period_nm,
              'second_harmonic_period_nm':s.period_nm/2,'methods':{}}
        for j,method in enumerate(METHODS):
            success=s.quantum_success if METHODS[method]['quantum'] else 1.
            # Same photons at source AND sample within each case; may differ in elapsed time.
            equal_dose=exposure(method,s,BASE_CLOCKS/success)
            equal_time=exposure(method,s,BASE_CLOCKS)
            rate=event_rates(method,s)[0].mean()
            matched_activation=exposure(method,s,s.threshold_events/rate)
            optimum=optimized_threshold_exposure(method,s)
            mc=simulate_counts(method,s,equal_dose['source_clocks'],REPETITIONS,SEED+index*100+j)
            mc_opt=simulate_counts(method,s,optimum['source_clocks'],REPETITIONS,SEED+10000+index*100+j)
            weak=weak_response_bound(method,s)
            assert weak['weak_regime_pass'],(name,method,weak)
            item['methods'][method]={'equal_sample_photons':equal_dose,
                'equal_attempt_clocks':equal_time,'equal_mean_activation_20':matched_activation,
                'best_threshold_accuracy':optimum,'finite_count_check':mc,
                'optimized_duration_count_check':mc_opt,'weak_response':weak}
        cases.append(item)
    sweeps=[]
    for param,values in [('eta',[1,.8,.5,.2,.05]),('blur_nm',[0,20,40,80,120,200]),
                         ('jitter_rad',[0,.15,.3,.6,1]),('linear_per_photon',[0,2e-6,2e-5,2e-4]),
                         ('quantum_success',[1,.1,.01,.001]),
                         ('background_per_cell_clock',[0,1e-8,1e-7,1e-6])]:
        for value in values:
            s=replace(base,**({'eta_a':value,'eta_b':value} if param=='eta' else {param:value}))
            for method in METHODS:
                success=s.quantum_success if METHODS[method]['quantum'] else 1
                dose=exposure(method,s,BASE_CLOCKS/success)
                timed=exposure(method,s,BASE_CLOCKS)
                sweeps.append({'parameter':param,'value':value,'method':method,
                    'visibility':dose['event_visibility'],'harmonic_snr_equal_sample_photons':dose['second_harmonic_snr'],
                    'harmonic_snr_equal_time':timed['second_harmonic_snr'],
                    'sample_photons':dose['sample_incident_photons'],'source_clocks':dose['source_clocks'],
                    'seconds':dose['seconds'],'total_events':dose['expected_events_total'],
                    'guard_cell_accuracy':dose['guard_cell_accuracy']})
    tracked=[HERE/'model.py',HERE/'test_model.py',HERE/'run_study.py',HERE.parent/'fringe_compare.py',HERE.parent/'README.md',ROOT/'QUANTUM_PHOTOLITHOGRAPHY_ROADMAP.md']
    return {'schema':'quantum-light-exposure-followup-v1','seed':SEED,'base_clocks':BASE_CLOCKS,
        'repetitions_per_case_method':REPETITIONS,'environment':{'python':sys.version,'platform':platform.platform(),
        'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked},
        'scope':'Finite classical numerical quantum-optics sensitivity study, not physical exposure, material calibration or quantum-computing advantage.',
        'normalization':'Two mean emitted photons per successful quantum trial or classical clock, M=32 fixed cells; all source attempts and both phase exposures charged. Failed quantum source trials emit vacuum; pump/herald resources unknown.',
        'response_units':'alpha events per incident photon; beta events per local n(n-1) moment per active slot, with mode/cell temporal overlap absorbed in uncalibrated beta. Clock Hz only a declared scheduling scale.',
        'poisson_scope':'Independent weak-event approximation after phase/pixel averaging and postactivation Gaussian displacement; not an exact joint quantum counting simulation or reaction-diffusion resist.',
        'cases':cases,'sweeps':sweeps}


def figures(data):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'noon':'#157e95','mixture':'#8b9296','coherent':'#b1a27e','phase_cycled':'#be7621','phase_cycled_burst':'#6d54a3'}
    names={'noon':'NOON','mixture':'Incoherent pair','coherent':'Coherent, one phase','phase_cycled':'Coherent, phase cycled','phase_cycled_burst':'Phase cycled, 10% duty'}
    nominal=next(x for x in data['cases'] if x['id']=='finite_nominal')
    s=Setup(**nominal['setup']);x=s.phases/(2*np.pi)*s.period_nm
    fig,ax=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for method in METHODS:
        e=nominal['methods'][method]['equal_sample_photons'];y=np.array(e['cell_mean_events'])
        ax[0].plot(x,y,label=names[method],color=colors[method])
        ax[1].plot(x,y/y.mean(),label=names[method],color=colors[method])
    ax[0].axhline(20,color='k',ls=':',lw=1);ax[0].set(title='Equal incident photons; absolute activation',xlabel='Position in toy period (nm)',ylabel='Expected events / cell')
    ax[0].legend(fontsize=8,loc='upper right')
    ax[1].set(title='Shape only: divide each curve by its mean',xlabel='Position (nm)',ylabel='Relative expected activation')
    selected=['noon','phase_cycled','phase_cycled_burst']
    for i,method in enumerate(selected):
        e=nominal['methods'][method]['equal_sample_photons'];mc=nominal['methods'][method]['finite_count_check'];lo,hi=mc['harmonic_empirical_interval95']
        ax[2].errorbar(i,e['second_harmonic_events_per_cell'],yerr=[[e['second_harmonic_events_per_cell']-lo],[hi-e['second_harmonic_events_per_cell']]],fmt='o',capsize=6,color=colors[method])
    ax[2].set_xticks(range(3),['NOON','Phase\ncycled','10% duty']);ax[2].set(title='Finite event counts: 95% realized range',ylabel='Estimated second harmonic (events/cell)')
    fig.suptitle('Quantum-light exposure sensitivity — assumed geometry and response, no fabrication',fontsize=13)
    fig.savefig(HERE/'exposure_tradeoffs.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(1,3,figsize=(15,4.4),layout='constrained')
    for method in selected:
        for k,param in enumerate(['eta','blur_nm','quantum_success']):
            rows=[r for r in data['sweeps'] if r['parameter']==param and r['method']==method]
            ax[k].plot([r['value'] for r in rows],[r['harmonic_snr_equal_time' if k==2 else 'visibility'] for r in rows],'-o',label=names[method],color=colors[method])
    ax[0].set(xlabel='Equal arm transmission',ylabel='Activation visibility',title='Loss makes linear background more important')
    ax[1].set(xlabel='Gaussian material blur σ (nm)',ylabel='Activation visibility',title='High spatial frequencies wash out')
    ax[2].set(xlabel='Quantum preparation success',ylabel='Second-harmonic SNR, same clock time',xscale='log',title='All failed preparations count')
    ax[2].legend(fontsize=8);fig.suptitle('Matched resources change the apparent benefit',fontsize=13)
    fig.savefig(HERE/'loss_blur_preparation.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(10.8,4.5),layout='constrained')
    for method in selected:
        ns=np.logspace(5,8,150)
        values=[exposure(method,s,n) for n in ns]
        ax[0].plot([e['sample_incident_photons'] for e in values],[e['guard_cell_accuracy'] for e in values],label=names[method],color=colors[method])
        opt=nominal['methods'][method]['best_threshold_accuracy']
        ax[1].scatter(opt['sample_incident_photons'],opt['guard_cell_accuracy'],s=80,color=colors[method],label=names[method])
    ax[0].set(xlabel='Mean photons incident on sample',ylabel='Expected correct bright/dark guard cells',xscale='log',ylim=(.45,1.01),title='Same fixed 20-event activation threshold')
    ax[1].set(xlabel='Mean incident photons at best duration',ylabel='Best guard-cell accuracy',xscale='log',ylim=(.45,1.01),title='Model-informed duration; dose still charged')
    ax[0].legend(fontsize=8);fig.suptitle('Phenomenological pattern task — not printed linewidth or yield',fontsize=13)
    fig.savefig(HERE/'threshold_dose_tradeoff.png',dpi=180);plt.close(fig)


def main():
    data=build()
    (HERE/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    with (HERE/'sensitivity.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(data['sweeps'][0]));writer.writeheader();writer.writerows(data['sweeps'])
    figures(data)
    print(json.dumps({'cases':len(data['cases']),'method_case_pairs':sum(len(c['methods']) for c in data['cases']),
        'poisson_replicates':len(data['cases'])*len(METHODS)*REPETITIONS*2,'sweep_rows':len(data['sweeps']),
        'nominal':{k:compact(v['equal_sample_photons']) for k,v in data['cases'][1]['methods'].items()}},indent=2))


if __name__=='__main__':main()
