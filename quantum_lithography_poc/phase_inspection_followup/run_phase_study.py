"""Finite-shot local/global phase comparison with separate dose/time budgets."""
from dataclasses import asdict
from pathlib import Path
import hashlib,json,platform,sys
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from phase_model import Setup,draw_records,estimate,estimate_hybrid,resources,errors_report,wrap

HERE=Path(__file__).resolve().parent
SEED=2026111017
REPEATS=2000
CLOCKS=10000


def hybrid_resources(setup,qn,cn):
    q=resources('noon',setup,qn);c=resources('coherent',setup,cn)
    total=qn+cn;fi=qn*q['classical_fisher_information_per_attempt']+cn*c['classical_fisher_information_per_attempt']
    out={key:q[key]+c[key] for key in ['attempted_clocks','sample_incident_mean_photons_before_object','mean_photons_after_object','mean_detected_photons','elapsed_seconds_at_assumed_clock']}
    out.update({'quantum_attempts':qn,'coherent_attempts':cn,'classical_fisher_information_per_attempt':fi/total,
        'local_unbiased_cramer_rao_sd':1/np.sqrt(fi),'allocation':'10% coherent + 90% NOON in the chosen primary budget (sample photons or attempted clocks)'})
    return out


def build():
    cases={'ideal':Setup(1,1,1),'high_efficiency':Setup(.9,.9,1),'moderate_loss':Setup(.6,.8,1),
        'severe_loss':Setup(.2,.6,1),'ten_percent_preparation':Setup(.9,.9,.1),
        'one_percent_preparation':Setup(.9,.9,.01),'detector_loss':Setup(.9,.3,1)}
    global_truth=np.random.default_rng(SEED).uniform(-np.pi,np.pi,REPEATS)
    local_truth=np.full(REPEATS,.35)
    rows=[]
    for i,(name,s) in enumerate(cases.items()):
        case={'id':name,'setup':asdict(s),'budgets':{}}
        for b,budget in enumerate(['equal_sample_photons','equal_attempt_clocks']):
            qclocks=int(CLOCKS/s.preparation_success) if b==0 else CLOCKS
            result={}
            for j,method in enumerate(['noon','coherent','hybrid']):
                if method=='hybrid':
                    qn=int(.9*qclocks);cn=int(.1*CLOCKS)
                    info=hybrid_resources(s,qn,cn)
                else:
                    attempts=qclocks if method=='noon' else CLOCKS
                    info=resources(method,s,attempts)
                methods={'resources':info}
                for k,(domain,truth) in enumerate([('local',local_truth),('global',global_truth)]):
                    seed=SEED+10000+i*100+b*20+j*2+k
                    rng=np.random.default_rng(seed)
                    grid=512 if domain=='local' else 2048
                    if method=='hybrid':
                        qr=draw_records('noon',truth,s,qn,rng);cr=draw_records('coherent',truth,s,cn,rng)
                        fitted=estimate_hybrid(qr,cr,s,domain,grid)
                        finer=estimate_hybrid(qr[:50],cr[:50],s,domain,grid*2)
                    else:
                        records=draw_records(method,truth,s,attempts,rng)
                        fitted=estimate(method,records,s,domain,grid)
                        finer=estimate(method,records[:50],s,domain,grid*2)
                    result_row=errors_report(fitted,truth)
                    if domain=='global':result_row.pop('boundary_rate_local_interval')
                    result_row.update({'seed':seed,'repetitions':REPEATS,'grid_points':grid,
                        'max_estimator_difference_to_double_grid_rad_first50':float(np.max(abs(wrap(finer-fitted[:50],np.pi if method=='noon' and domain=='global' else 2*np.pi)))),
                        'grid_difference_period_rad':float(np.pi if method=='noon' and domain=='global' else 2*np.pi),
                        'examples':[{'true_phase':float(t),'estimated_phase':float(v)} for t,v in zip(truth[:8],fitted[:8])]})
                    methods[domain]=result_row
                result[method]=methods
            dose=[d['resources']['sample_incident_mean_photons_before_object'] for d in result.values()]
            clocks=[d['resources']['attempted_clocks'] for d in result.values()]
            assert (max(dose)-min(dose)<1e-8) if b==0 else (max(clocks)==min(clocks))
            case['budgets'][budget]=result
        rows.append(case)
    sources=['phase_model.py','test_phase_model.py','run_phase_study.py']
    return {'schema':'phase-inspection-followup-v1','seed':SEED,'repetitions_per_record_type':REPEATS,
        'estimation_trials':len(cases)*2*3*2*REPEATS,'base_classical_clocks':CLOCKS,
        'sampling_dependence':'Independently drawn outcomes conditional on truth; the same 2000 uniformly sampled global phases are reused across methods/cases. Trials within each combination are independent, combinations share the phase cohort.',
        'sample_dose_definition':'Expected photons arriving in TWO object-illuminated modes BEFORE object transmission or detection loss; neither mode bypasses the object. Relative-phase generator(n_a-n_b)/2; no conditioning on successful detections.',
        'global_prior':'Uniform phase on [-pi,pi); pure NOON returns one representative branch in [0,pi). Modulo-pi error is separately labeled and cannot recover the missing branch.',
        'local_prior':'Both methods know calibrated [.15,.55] rad interval; independent benchmark truth .35 rad. No prior supplied to only one method.',
        'reference':'Known independent phase-bias calibration at 0, pi/4, pi/2, 3pi/4 for all methods. Both illumination-arm photons counted. Calibration control energy unknown; no extra uncounted bright local oscillator.',
        'assumptions':'Identical symmetric arm transmission, ideal PNR discrimination conditional on detection, known losses, no phase jitter/dark counts/reference drift. Exact quantum multinomial and coherent Poisson records. Hybrid coarse record fully charged.',
        'environment':{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},
        'source_sha256':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in sources},'cases':rows}


def plot(r):
    names=['Ideal','High\nefficiency','Moderate\nloss','Severe\nloss','10%\npreparation','1%\npreparation','Detector\nloss']
    colors={'noon':'#157e95','coherent':'#be7621','hybrid':'#6d54a3'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(13,4.6),layout='constrained')
    for ax,budget in zip(axs,['equal_sample_photons','equal_attempt_clocks']):
        for i,method in enumerate(colors):
            y=np.array([c['budgets'][budget][method]['local']['rmse_full_2pi_rad'] for c in r['cases']])
            cis=np.array([c['budgets'][budget][method]['local']['rmse_mc_interval95_rad'] for c in r['cases']])
            ax.errorbar(np.arange(7)+(i-1)*.12,y,yerr=[y-cis[:,0],cis[:,1]-y],fmt='o',capsize=3,label=method,color=colors[method])
        ax.set_xticks(range(7),names,fontsize=8);ax.set_yscale('log');ax.set_ylabel('Local phase RMSE (rad)')
        ax.set_title('20,000 mean photons before object' if budget=='equal_sample_photons' else '10,000 attempted source clocks')
        ax.grid(axis='y',alpha=.2)
    axs[0].legend(title='Probe');fig.suptitle('Calibrated local phase: finite-shot error and loss/preparation cost',fontsize=13)
    fig.savefig(HERE/'local_phase_tradeoffs.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4.6),layout='constrained')
    data=r['cases'][1]['budgets']['equal_sample_photons']
    for i,method in enumerate(colors):
        g=data[method]['global'];axs[0].bar(i-.17,g['rmse_full_2pi_rad'],.32,color=colors[method],alpha=.95)
        axs[0].bar(i+.17,g['rmse_modulo_pi_rad'],.32,color=colors[method],alpha=.4)
        axs[1].bar(i,g['wrong_pi_branch_rate'],color=colors[method])
    axs[0].set_xticks(range(3),['NOON','Coherent','10/90 hybrid']);axs[0].set_yscale('log')
    axs[0].set_ylabel('Global phase RMSE (rad)');axs[0].set_title('Solid: full 2π error; pale: modulo-π error')
    axs[1].set_xticks(range(3),['NOON','Coherent','10/90 hybrid']);axs[1].set_ylabel('Fraction with error > π/2');axs[1].set_ylim(0,.6)
    axs[1].set_title('A fine fringe leaves an unresolved branch')
    fig.suptitle('Unknown global phase: coarse classical records resolve ambiguity',fontsize=13)
    fig.savefig(HERE/'global_phase_ambiguity.png',dpi=180);plt.close(fig)


def main():
    result=build();(HERE/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');plot(result)
    print(json.dumps({'estimation_trials':result['estimation_trials'],
        'local':{c['id']:{b:{m:round(v['local']['rmse_full_2pi_rad'],6) for m,v in d.items()} for b,d in c['budgets'].items()} for c in result['cases']},
        'global_high_efficiency':{m:v['global'] for m,v in result['cases'][1]['budgets']['equal_sample_photons'].items()}},indent=2))


if __name__=='__main__':main()
