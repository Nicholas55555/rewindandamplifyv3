"""Fresh joint-parameter, control, classical-baseline and dead-time study."""
from __future__ import annotations
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.optimize import minimize, minimize_scalar

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import inference_model as m
sys.path.insert(0,str(HERE.parent/'diagnostics_baselines'))
from compare import fit_hmm,hmm_likelihood_and_stats,paired_comparison,to_jsonable
from refine_replication import refine_hmm

CONFIG={'seeds':[411001,411002], 'train_records':240, 'test_records':240, 'bins':24,
        'cavity_dimension':4, 'joint_starts':3, 'joint_maxfun':900,
        'hmm_states':3, 'hmm_starts':5, 'hmm_iterations':1200,
        'coupling_profile_grid':[0.,.2,.4,.6,.8,1.,1.2],
        'scope':'Exploratory synthetic study. Design informed by earlier numerical cutoff check. Fresh holdouts.'}


def atomic_json(path,payload):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(to_jsonable(payload),indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def telegraph(train,test):
    mean=float(train.mean()); cap=min(mean,1-mean)*(1-1e-8)
    def unpack(x):
        r=.001+.998*x[0]; d=cap*x[1]
        return np.array([.5,.5]),np.array([[1-r,r],[r,1-r]]),np.array([mean-d,mean+d])
    def obj(x):
        return -hmm_likelihood_and_stats(train,*unpack(x)).sum()
    opts=[minimize(obj,start,method='L-BFGS-B',bounds=[(0.,1.),(0.,1.)])
          for start in ([.1,.5],[.5,.8],[.9,.5])]
    best=min(opts,key=lambda r:r.fun)
    return hmm_likelihood_and_stats(test,*unpack(best.x)),{
        'training_mean':mean,'initial':[.5,.5],'transition':unpack(best.x)[1],
        'emissions':unpack(best.x)[2],'train_loglikelihood':-best.fun,
        'success':bool(best.success),'scope':'Symmetric stationary two-state telegraph; mean rate fixed to training mean'}


def fixed_fit(train,p,controls,dead_bins):
    def obj(g):
        return -m.all_logs(train,replace(p,g_defect=float(g)),controls,dead_bins).sum()
    grid=np.linspace(0,1.3,27)
    values=[obj(g) for g in grid]
    k=int(np.argmin(values))
    left=grid[max(0,k-1)]; right=grid[min(len(grid)-1,k+1)]
    result=minimize_scalar(obj,bounds=(left,right),method='bounded',options={'xatol':1e-5})
    return replace(p,g_defect=float(result.x)),{'grid':grid,'negative_loglikelihood':values,
                                              'g_hat':float(result.x),'known_nuisance_oracle':True}


def baselines(train,test,seed):
    hmm_logs=[];tele_logs=[];details=[]
    for k,(x,y) in enumerate(zip(train,test)):
        fitted=fit_hmm(x,states=CONFIG['hmm_states'],starts=CONFIG['hmm_starts'],
                       max_iter=CONFIG['hmm_iterations'],seed=seed+10*k)
        # API fields are inspected and tested before the held-out run.
        initial=np.array(fitted['initial']); transition=np.array(fitted['transition']); emissions=np.array(fitted['emissions'])
        refined,refinement=refine_hmm(x,initial,transition,emissions)
        hl=hmm_likelihood_and_stats(y,*refined)
        tl,td=telegraph(x,y)
        hmm_logs.append(hl);tele_logs.append(tl)
        details.append({'hmm_em':fitted,'hmm_refinement':refinement,
                        'hmm_selected_parameters':{'initial':refined[0],'transition':refined[1],'emissions':refined[2]},'telegraph':td})
    return np.concatenate(hmm_logs),np.concatenate(tele_logs),details


def paired_by_control(first,second,sizes,seed):
    """Hold the fixed control allocation constant while resampling records."""
    delta=np.asarray(first)-np.asarray(second)
    groups=np.split(delta,np.cumsum(sizes)[:-1])
    rng=np.random.default_rng(seed)
    boot=np.zeros(3000)
    variance=0.
    for group in groups:
        weight=len(group)/len(delta)
        boot+=weight*group[rng.integers(0,len(group),size=(len(boot),len(group)))].mean(axis=1)
        variance+=weight**2*group.var(ddof=1)/len(group)
    return {'mean_delta_nats_per_record':float(delta.mean()),'total_delta_nats':float(delta.sum()),
            'standard_error_nats_per_record':float(np.sqrt(variance)),
            'bootstrap_95_percentile_nats_per_record':np.quantile(boot,[.025,.975]),
            'records_per_control':sizes,'seed':seed,'bootstrap_replicates':len(boot),
            'uncertainty_scope':'Independent held-out records stratified by fixed control; conditional on fitted models, not training/optimization uncertainty'}


def run_case(out,protocol,seed,dead_truth=0,dead_fit=0,profile=False):
    label=f'{protocol}_{seed}_dead{dead_truth}_fit{dead_fit}'
    file=out/f'{label}.json'
    if file.exists():
        saved=json.loads(file.read_text())
        if saved['config']!=CONFIG:
            raise ValueError('Existing case has different configuration')
        print('Verified completed case',label,flush=True)
        return
    started=time.perf_counter()
    p=m.Parameters(n_cavity=CONFIG['cavity_dimension'])
    controls=m.PROTOCOLS[protocol]
    train=m.sample(p,controls,CONFIG['train_records']//len(controls),CONFIG['bins'],seed,dead_truth)
    test=m.sample(p,controls,CONFIG['test_records']//len(controls),CONFIG['bins'],seed+100000,dead_truth)
    joint,diagnostics=m.fit(train,p,controls,seed=seed+400000,starts=CONFIG['joint_starts'],
                            maxfun=CONFIG['joint_maxfun'],dead_bins=dead_fit)
    fixed,fixed_diag=fixed_fit(train,p,controls,dead_fit)
    joint_scores=m.all_logs(test,joint,controls,dead_fit)
    fixed_scores=m.all_logs(test,fixed,controls,dead_fit)
    oracle_scores=m.all_logs(test,p,controls,dead_truth)
    hmm_scores,tele_scores,baseline_details=baselines(train,test,seed+300000)
    # No parameter is reselected based on these held-out predictions.
    profile_rows=[]
    if profile:
        for i,g in enumerate(CONFIG['coupling_profile_grid']):
            fitted,report=m.fit(train,p,controls,seed=seed+500000+i,starts=1,maxfun=500,dead_bins=dead_fit,fixed_g=g)
            profile_rows.append({'fixed_g':g,'parameters':asdict(fitted),'fit':report})
    # Evaluate cutoff sensitivity at the already training-selected parameters.
    cutoff_scores=m.all_logs(test,replace(joint,n_cavity=5),controls,dead_fit)
    result={'case':label,'config':CONFIG,'protocol_controls':controls,'generator_parameters':asdict(p),
            'detector_dead_bins_truth':dead_truth,'detector_dead_bins_fit':dead_fit,
            'training_sha256':hashlib.sha256(b''.join(x.tobytes() for x in train)).hexdigest(),
            'test_sha256':hashlib.sha256(b''.join(x.tobytes() for x in test)).hexdigest(),
            'joint_parameters':asdict(joint),'joint_fit':diagnostics,'known_nuisance_fit':fixed_diag,
            'baseline_fits':baseline_details,'coupling_profile':profile_rows,
            'scores':{'joint':joint_scores,'known_nuisance':fixed_scores,'generator_oracle':oracle_scores,
                      'hmm':hmm_scores,'rate_matched_telegraph':tele_scores,'joint_dimension5':cutoff_scores},
            'paired':{'joint_minus_hmm':paired_by_control(joint_scores,hmm_scores,[len(x) for x in test],seed+1),
                      'joint_minus_telegraph':paired_by_control(joint_scores,tele_scores,[len(x) for x in test],seed+2),
                      'known_minus_joint':paired_by_control(fixed_scores,joint_scores,[len(x) for x in test],seed+3),
                      'cutoff5_minus_4':paired_by_control(cutoff_scores,joint_scores,[len(x) for x in test],seed+4)},
            'elapsed_seconds':time.perf_counter()-started}
    atomic_json(file,result)
    print('Completed',label,'seconds',round(result['elapsed_seconds'],1),flush=True)


def main():
    out=HERE/'inference_results'; out.mkdir(exist_ok=True)
    files=[Path(__file__),HERE/'inference_model.py',HERE/'PROTOCOL.md']
    source_hash={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    manifest={'config':CONFIG,'source_sha256':source_hash,
              'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}}
    path=out/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=manifest:
        raise ValueError('Source/configuration changed; use a separate output directory')
    atomic_json(path,manifest)
    p=m.Parameters(n_cavity=4)
    info_path=out/'information.json'
    if not info_path.exists():
        information={name:m.information(p,controls) for name,controls in m.PROTOCOLS.items()}
        for name,controls in m.PROTOCOLS.items():
            information[name]['detuning_sign_max_probability_difference']=max(
                float(np.max(np.abs(m.exact_distribution(p,c)[1]-m.exact_distribution(replace(p,defect_detuning=-p.defect_detuning),c)[1]))) for c in controls)
        atomic_json(info_path,information)
        print('Saved exact short-record information',flush=True)
    for seed in CONFIG['seeds']:
        for protocol in m.PROTOCOLS:
            run_case(out,protocol,seed,profile=seed==CONFIG['seeds'][0] and protocol=='controlled')
    # Fresh mismatch cohort; same training/test records across the two readout models.
    for modeled_dead in [0,1]:
        run_case(out,'fixed',411101,dead_truth=1,dead_fit=modeled_dead)
    print('Inference experiment complete',flush=True)


if __name__=='__main__':
    main()
