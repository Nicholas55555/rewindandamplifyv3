"""Reproduce the synthetic sensor comparison specified before first testing.

No fitting or threshold tuning occurs on any saved held-out scenario.
"""
from pathlib import Path
from dataclasses import asdict
import argparse
import hashlib
import json
import math
import platform
import numpy as np
from model import Config, METHODS, SCENARIOS, simulate, response_calibration, ramsey_probability


BASE_SEED = 770214
N_FIT = 4000
N_THRESHOLD = 6000
N_TEST = 4000
FALSE_ALARM_TARGET = .05


def wilson(k, n):
    z = 1.959963984540054
    p = k/n; d = 1+z*z/n
    center = (p+z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,center-half),min(1,center+half)]


def mean_ci(x):
    x=np.asarray(x,float)
    mean=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x)))
    return [mean-1.959963984540054*se,mean+1.959963984540054*se]


def order_threshold(scores, alpha=FALSE_ALARM_TARGET):
    """Upper order statistic, strict > decision; exchangeability rank rule.

    k=ceil((n+1)(1-alpha)); a future IID continuous null has unconditional
    exceedance probability <=alpha over calibration and that future sample.
    This is not a confidence guarantee on realized conditional FPR, nor does
    it survive a distribution shift. We separately report test-set FPR.
    """
    values=np.sort(np.asarray(scores,float))
    if values.ndim!=1 or not len(values) or not np.isfinite(values).all():
        raise ValueError('finite nonempty score vector required')
    k=int(np.ceil((len(values)+1)*(1-alpha)))
    return float(values[k-1]) if k<=len(values) else math.inf


def fit_estimators(null, injected, amplitude):
    mean=null.mean(axis=0)
    covariance=np.cov(null,rowvar=False)
    response=np.mean((injected-mean)*amplitude[:,None],axis=0)/np.mean(amplitude**2)
    response[0]=0. # The physical model has no photodiode response to frequency.
    models={}
    for method in METHODS:
        key=method['id']; cols=method['columns']
        if key=='power_only':
            models[key]={'columns':cols,'weights':[0.], 'mean':mean[cols].tolist(),
                         'note':'Always predicts zero frequency change; absolute power change is its alarm score.'}
            continue
        cov=covariance[np.ix_(cols,cols)]; r=response[cols]
        raw=np.linalg.solve(cov,r)
        weights=raw/(r@raw)
        models[key]={'columns':cols,'weights':weights.tolist(),
                     'mean':mean[cols].tolist(),
                     'calibrated_response':r.tolist(),
                     'null_covariance':cov.tolist(),
                     'note':'Linear minimum-variance unbiased estimate under the fitted local response/covariance.'}
    return models


def estimate(features, fitted):
    x=features[:,fitted['columns']]-np.asarray(fitted['mean'])
    return x@np.asarray(fitted['weights'])


def score(features, fitted, key):
    if key=='power_only':
        return np.abs(features[:,0]-fitted['mean'][0])
    return np.abs(estimate(features,fitted))


def evaluate(null,alt,continuous,target,models,thresholds):
    methods={}; predictions={}; alarms={}
    for method in METHODS:
        key=method['id']; model=models[key]
        positive=score(alt,model,key)>thresholds[key]
        false=score(null,model,key)>thresholds[key]
        prediction=estimate(continuous,model)
        squared=(prediction-target)**2
        mse=float(squared.mean())
        interval=mean_ci(squared)
        methods[key]={'detection_count':int(positive.sum()),
                      'false_alarm_count':int(false.sum()),
                      'records_per_class':len(null),
                      'detection_rate':float(positive.mean()),
                      'false_alarm_rate':float(false.mean()),
                      'detection_ci95':wilson(int(positive.sum()),len(positive)),
                      'false_alarm_ci95':wilson(int(false.sum()),len(false)),
                      'estimation_records':len(target),
                      'rmse_hz':math.sqrt(mse),
                      'rmse_ci95':[math.sqrt(max(0,x)) for x in interval],
                      'bias_hz':float((prediction-target).mean()),
                      'mse_hz2':mse,
                      'alarm_threshold':thresholds[key]}
        predictions[key]=prediction
        alarms[key]=positive.astype(float)
    paired={}
    for reference,added in [('classical','classical_quantum'),
                            ('classical','two_classical'),
                            ('classical_quantum','two_classical')]:
        delta=(predictions[reference]-target)**2-(predictions[added]-target)**2
        detect=alarms[added]-alarms[reference]
        paired[reference+'_to_'+added]={
            'mse_reduction_hz2':float(delta.mean()),
            'mse_reduction_ci95':mean_ci(delta),
            'relative_mse_reduction':float(delta.mean()/methods[reference]['mse_hz2']),
            'detection_increase':float(detect.mean()),
            'detection_increase_ci95':mean_ci(detect),
            'interpretation':'Positive favors added channel. Paired intervals conditional on synthetic model; no multiplicity correction.'}
    return methods,paired


def create_plots(result,traces,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False})
    colors={'power_only':'#9ba3ae','classical':'#348cb0','quantum':'#8469bf',
            'classical_quantum':'#e99c50','two_classical':'#399d84'}
    nominal=result['scenarios'][0]
    keys=['classical','quantum','classical_quantum','two_classical']
    labels=['Conventional C','Atomic Q + power','C + atomic Q','C + independent C']
    fig,axes=plt.subplots(1,3,figsize=(14,4.3),layout='constrained')
    for ax,metric,ci,title in zip(axes,['detection_rate','false_alarm_rate','rmse_hz'],
                                 ['detection_ci95','false_alarm_ci95','rmse_ci95'],
                                 ['Detect a 0.5 Hz source step','False alarms with no injected step','Estimate unknown change (RMSE)']):
        y=np.array([nominal['methods'][k][metric] for k in keys]); factor=100 if 'rate' in metric else 1
        err=np.array([nominal['methods'][k][ci] for k in keys])
        ax.bar(np.arange(4),y*factor,color=[colors[k] for k in keys],width=.62)
        ax.errorbar(np.arange(4),y*factor,yerr=np.stack([y-err[:,0],err[:,1]-y])*factor,
                    fmt='none',ecolor='#25334b',capsize=4,lw=1)
        ax.set_xticks(range(4),labels,rotation=25,ha='right',fontsize=9)
        ax.set_title(title,fontsize=12)
        ax.set_ylabel('Percent' if factor==100 else 'Hz')
        if metric=='false_alarm_rate': ax.axhline(5,color='#687589',ls='--',lw=1)
        if metric=='detection_rate': ax.set_ylim(0,105)
    fig.suptitle('Synthetic optical-sensor study | independent calibration and held-out tests',fontsize=14)
    fig.savefig(out/'comparison.png',dpi=180,facecolor='white'); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,6.5),layout='constrained')
    for key in ['classical','classical_quantum','two_classical']:
        x=[100*s['methods'][key]['detection_rate'] for s in result['scenarios']]
        f=[100*s['methods'][key]['false_alarm_rate'] for s in result['scenarios']]
        label=next(m['label'] for m in METHODS if m['id']==key)
        axes[0].plot(range(len(x)),x,'o-',color=colors[key],label=label)
        axes[1].plot(range(len(f)),f,'o-',color=colors[key],label=label)
    axes[0].set(ylabel='Detection (%)',ylim=(0,103),title='Frozen calibration under disturbances')
    axes[0].legend(ncol=3,fontsize=10)
    axes[1].set(ylabel='False alarms (%)',ylim=(0,103))
    axes[1].axhline(5,color='#687589',ls='--',label='Nominal target5%')
    labels=['Nominal','Short T2','Atom drift','LO drift','Shared path','Power step','Correlated refs','Ramp']
    for ax in axes: ax.set_xticks(range(len(labels)),labels,rotation=25,ha='right',fontsize=9)
    fig.savefig(out/'stress_tests.png',dpi=180,facecolor='white'); plt.close(fig)
    trace=traces['scenarios']['nominal']; t=trace['time_s']
    fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True,layout='constrained')
    axes[0].plot(t,trace['photodiode_relative_power'],color='#748394',label='Photodiode relative intensity')
    axes[0].set_ylabel('Relative power'); axes[0].legend(loc='upper left')
    axes[1].plot(t,trace['laser_frequency_hz'],color='#27394c',lw=2,label='Hidden source (simulation truth)')
    axes[1].plot(t,trace['primary_heterodyne_hz'],color=colors['classical'],alpha=.8,label='Primary coherent receiver')
    axes[1].set_ylabel('Hz'); axes[1].legend(loc='upper left',fontsize=9)
    axes[2].plot(t,trace['quantum_frequency_hz'],color=colors['quantum'],alpha=.5,lw=1,label='Atomic readout, locally calibrated')
    q=np.array(trace['quantum_frequency_hz']); axes[2].plot(np.array(t).reshape(-1,8).mean(1),q.reshape(-1,8).mean(1),
                  color=colors['classical_quantum'],lw=2,label='8-cycle average (display only)')
    axes[2].plot(t,trace['laser_frequency_hz'],color='#27394c',lw=2)
    axes[2].set(xlabel='Time (s)',ylabel='Hz'); axes[2].legend(loc='upper left',fontsize=9)
    for ax in axes: ax.axvline(64,color='#687589',ls='--',alpha=.5)
    fig.suptitle('One simulated 128-cycle record: frequency can move while power stays stable',fontsize=13)
    fig.savefig(out/'example_trace.png',dpi=170,facecolor='white'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    for key in ['power_only','classical','classical_quantum','two_classical']:
        ax.plot([s['amplitude_hz'] for s in result['amplitude_sweep']],
                [100*s['methods'][key]['detection_rate'] for s in result['amplitude_sweep']],
                'o-',label=next(m['label'] for m in METHODS if m['id']==key),color=colors[key])
    ax.set(xlabel='Programmed frequency-step magnitude (Hz)',ylabel='Detection (%)',ylim=(0,103),
           title='A fixed decision rule across different step sizes')
    ax.legend();fig.savefig(out/'amplitude_sweep.png',dpi=180,facecolor='white');plt.close(fig)


def run(out,n_fit=N_FIT,n_threshold=N_THRESHOLD,n_test=N_TEST):
    config=Config();config.validate()
    response=response_calibration(config)
    print('Response calibration complete',flush=True)
    null,_,_=simulate(n_fit,BASE_SEED,config,response)
    amplitude=np.random.default_rng(BASE_SEED+1).choice([-config.fault_step_hz,config.fault_step_hz],n_fit)
    injected,_,_=simulate(n_fit,BASE_SEED+2,config,response,amplitude)
    models=fit_estimators(null,injected,amplitude)
    threshold_data,_,_=simulate(n_threshold,BASE_SEED+3,config,response)
    thresholds={key:order_threshold(score(threshold_data,model,key)) for key,model in models.items()}
    reference_difference_center=float(np.mean(null[:,3]-null[:,2]))
    disagreement_threshold=order_threshold(np.abs(threshold_data[:,3]-threshold_data[:,2]-reference_difference_center),.01)
    print('Estimator and independent null threshold calibrations complete',flush=True)
    result={'schema_version':1,'evidence_type':'synthetic physically motivated surrogate; no measured laser or QPU data',
            'config':asdict(config),'methods':METHODS,
            'numerics':{'pulse_integrator':'Strang split coherent rotation and Markov damping',
                        'substeps_per_pulse':16,
                        'refinement_record':'numerical_refinement.json preserves first4-substep results; refinement used unchanged seeds and scientific parameters.'},
            'seed':BASE_SEED,'nominal_false_alarm_target':FALSE_ALARM_TARGET,
            'calibration':{'response':response,'fit_null_records':n_fit,'fit_injected_records':n_fit,
                           'independent_threshold_records':n_threshold,
                           'fit_seed':BASE_SEED,'injection_seed':BASE_SEED+2,
                           'threshold_seed':BASE_SEED+3,'estimators':models,'thresholds':thresholds,
                           'test_retuning':False,
                           'synthetic_model_calibration_equivalent_acquisition_s':(2*n_fit+n_threshold)*config.cycles*config.cycle_s,
                           'calibration_cost_note':'Monte Carlo under an assumed model, not physically acquired. Directly collecting this many128s histories would take20.74days at default counts, plus3.2h response scan. A practical laboratory calibration protocol is still needed.',
                           'decision':'abs(calibrated linear estimate)>independently calibrated threshold; power uses abs(relative-power change)',
                           'event_time_known':True,'assumed_event_cycle':64},
            'resource_ledger':{'source_photons_per_cycle':config.source_photons_per_cycle,
                               'cycles_per_record':config.cycles,'duration_s':config.cycles*config.cycle_s,
                               'interrogation_s':config.interrogation_s,
                               'dead_time_s':config.cycle_s-config.interrogation_s,
                               'optical_probe_duty_fraction':2*config.pulse_s/config.cycle_s,
                               'same_bookkept_source_allotment_for_C_CQ_CC':True,
                               'matched':'acquisition duration, source paths and target task; assumed photon allotment bookkeeping only',
                               'not_matched':['LO power and stability cost','atomic cooling, trapping, readout and reset light',
                                              'hardware complexity and operating cost','independent reference apparatus'],
                               'atomic_probe_power_during_pulses_w':config.source_photons_per_cycle*.45*(6.62607015e-34*299792458/(config.wavelength_nm*1e-9))/(2*config.pulse_s),
                               'coupling_assumption':'The atomic geometry/coupling is assumed calibrated to a pi/2 pulse in2.5ms at its45% allocation. Dipole/beam-area coupling and apparatus are unmodeled; varying allotted photons alone does not change Omega. No measured device/coupling validation.',
                               'photon_accounting_limit':'A source-photon-allocation check is not total-resource fairness or proof of quantum advantage.'},
            'scenarios':[],'amplitude_sweep':[],
            'scope':['Low-frequency narrow-line698nm laboratory surrogate, not193nm DUV, CO2 drive or13.5nm EUV.',
                     '64 independent atoms with classical optical drive, no squeezing/entanglement.',
                     'Interrogation samples once per second; source frequency is quasi-static within each25ms window.',
                     'No phase-noise spectrum reconstruction, wafer outcome, real sensor performance or end-to-end quantum advantage established.'],
            'sources':[
                {'title':'Bishof et al., Optical spectrum analyzer with quantum limited noise floor (2013)',
                 'url':'https://arxiv.org/html/1303.6741v2','role':'Established atomic laser-noise spectroscopy; quadrature Ramsey, finite pulses and dead-time precedent. Our numerical values/results are synthetic.'},
                {'title':'Day et al., Limits on atomic qubit control from laser noise (2022)',
                 'url':'https://www.nature.com/articles/s41534-022-00586-4','role':'Laser noise can limit atomic-qubit control; not validation of this surrogate.'},
                {'title':'ASML, Light and lasers in lithography',
                 'url':'https://www.asml.com/en/technology/lithography-principles/light-and-lasers','role':'Distinguishes lithography source architectures and wavelengths.'}],
            'runtime':{'python':platform.python_version(),'numpy':np.__version__}}
    traces={'schema_version':1,'evidence_type':result['evidence_type'],'scenarios':{}}
    for i,scenario in enumerate(SCENARIOS):
        seed=BASE_SEED+100+10*i
        pars=scenario['parameters']
        null,_,_=simulate(n_test,seed,config,response,scenario=pars)
        amplitudes=np.random.default_rng(seed+1).choice([-config.fault_step_hz,config.fault_step_hz],n_test)
        alt,_,_=simulate(n_test,seed+2,config,response,amplitudes,pars)
        continuous_amplitudes=np.random.default_rng(seed+3).uniform(-1,1,n_test)
        continuous,target,_=simulate(n_test,seed+4,config,response,continuous_amplitudes,pars)
        metrics,paired=evaluate(null,alt,continuous,target,models,thresholds)
        entry={**scenario,'seeds':{'null':seed,'alt':seed+2,'estimation':seed+4,'trace':seed+5},
               'methods':metrics,'paired_comparisons':paired,
               'null_definition':'No injected source-frequency change; scenario disturbances and stochastic background remain.',
               'fault_definition':'Random-sign0.5Hz source change; same scenario disturbances as null.',
               'rmse_target':'Injected mean post-minus-pre frequency for independently drawn Uniform(-1,1)Hz amplitudes.'}
        entry['reference_disagreement_check']={
            'nominal_target':.01,'threshold_hz':disagreement_threshold,
            'no_injected_source_step_flag_rate':float(np.mean(np.abs(null[:,3]-null[:,2]-reference_difference_center)>disagreement_threshold)),
            'injected_source_step_flag_rate':float(np.mean(np.abs(alt[:,3]-alt[:,2]-reference_difference_center)>disagreement_threshold)),
            'meaning':'Atomic and primary-reference paths disagree; this cannot identify which reference changed. Diagnostic flag only, not used to improve saved detection metrics.'}
        if i==0:
            result['nominal_operating_points']=[]
            for target_fpr in [.01,.05,.10]:
                op={'calibration_target':target_fpr,'methods':{}}
                for method in METHODS:
                    key=method['id'];model=models[key]
                    threshold=order_threshold(score(threshold_data,model,key),target_fpr)
                    pos=score(alt,model,key)>threshold;false=score(null,model,key)>threshold
                    op['methods'][key]={'threshold':threshold,'detection_rate':float(pos.mean()),
                                        'false_alarm_rate':float(false.mean()),
                                        'detection_ci95':wilson(int(pos.sum()),len(pos)),
                                        'false_alarm_ci95':wilson(int(false.sum()),len(false))}
                result['nominal_operating_points'].append(op)
        result['scenarios'].append(entry)
        _,_,trace=simulate(1,seed+5,config,response,config.fault_step_hz,pars,True)
        trace.update({'label':scenario['label'],'parameters':pars,
                      'seed':seed+5,'simulated_source_step_hz':config.fault_step_hz})
        for method in METHODS:
            key=method['id']
            features=np.array([trace['feature_vector']])
            trace.setdefault('record_estimates',{})[key]={'estimated_change_hz':float(estimate(features,models[key])[0]),
                                                         'alarm':bool(score(features,models[key],key)[0]>thresholds[key])}
        traces['scenarios'][scenario['id']]=trace
        print(scenario['id']+': '+', '.join(k+' detection='+str(round(100*metrics[k]['detection_rate'],2))+'% FPR='+str(round(100*metrics[k]['false_alarm_rate'],2))+'%' for k in ['classical','classical_quantum','two_classical']),flush=True)
    for i,size in enumerate([0.,.15,.30,.50,.75,1.]):
        seed=BASE_SEED+1000+3*i
        n=max(2000,n_test//2)
        amplitudes=np.random.default_rng(seed).choice([-size,size],n)
        samples,_,_=simulate(n,seed+1,config,response,amplitudes)
        metrics={}
        for method in METHODS:
            key=method['id']; successes=int((score(samples,models[key],key)>thresholds[key]).sum())
            metrics[key]={'detection_rate':successes/n,'ci95':wilson(successes,n),'count':successes,'n':n}
        result['amplitude_sweep'].append({'amplitude_hz':size,'seed':seed+1,'methods':metrics})
    detuning=np.linspace(-25,25,501)
    result['response_curve']={'detuning_hz':detuning.tolist(),
                              'probability':ramsey_probability(detuning,1.,config).tolist(),
                              'short_coherence_probability':ramsey_probability(detuning,1.,
                                    __import__('dataclasses').replace(config,t2_s=.012,readout_01=.10,readout_10=.14)).tolist(),
                              'physical_model':'finite pulse Bloch dynamics; calibrated response local only'}
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path(__file__),Path(__file__).with_name('model.py')]}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    (out/'example_traces.json').write_text(json.dumps(traces,indent=2)+'\n',encoding='utf8')
    create_plots(result,traces,out)
    print('Saved results, traces and four figures to '+str(out),flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=Path(__file__).parent)
    p.add_argument('--overwrite',action='store_true')
    p.add_argument('--test-records',type=int,default=N_TEST)
    args=p.parse_args()
    if args.test_records<100: raise ValueError('Use at least100 test records.')
    args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'results.json').exists() and not args.overwrite:
        raise FileExistsError('Results exist; use --overwrite or choose a new --out directory.')
    run(args.out,n_test=args.test_records)


if __name__=='__main__':main()
