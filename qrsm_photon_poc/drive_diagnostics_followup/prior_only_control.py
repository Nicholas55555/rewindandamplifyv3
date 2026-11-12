"""Post-holdout descriptive no-observation estimation control.

This was motivated by inspected main results. It changes no records, trained
models, alarms, thresholds or claimed confirmatory tests. The prior predictor
uses the exact same schedule/class assumptions and training-selected parameters,
but ignores the per-record detector bits.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import model as m
import run_study as r


def prior_fraction(steps,fraction):
    step=np.array([1.,0.]);tele=np.array([1.,0.]);values=[]
    for t in range(steps):
        step=step@m.schedule_transition('step',t)
        tele=tele@m.schedule_transition('telegraph',t)
        values.append(.25*fraction*(step[1]+tele[1]))
    return np.array(values)


def main(directory):
    result=json.loads((directory/'results.json').read_text())
    provenance=json.loads((directory/'provenance_start.json').read_text())
    seed=r.named_seed(982211,'post_holdout_prior_only_descriptive')
    assert seed not in {x['seed'] for x in provenance['random_stream_namespaces']}
    rng=np.random.default_rng(seed)
    collected={name:[] for name in result['cases']}; hashes={};traces={}
    for index,detail in enumerate(result['pipeline_calibrations']):
        path=directory/f'pipeline_{index}_raw.npz'
        assert r.sha(path)==detail['raw_sha256'];hashes[path.name]=r.sha(path)
        prior=detail['calibrated_parameters']['drive']*(1+prior_fraction(result['config']['steps'],detail['selected_fraction']))
        traces[str(index)]={'selected_fraction':detail['selected_fraction'],'effective_drive_prior':prior.tolist()}
        with np.load(path) as raw:
            for name in collected:
                truth=detail['truth']['drive']*(1+raw[name+'__fraction'])
                error=(prior[None,:]-truth)/detail['truth']['drive']
                prior_mse=(error[:,16:]**2).mean(axis=1)
                actual_mse=raw[name+'__estimate_metric__mse']
                # Independent re-evaluation of the observation-based estimate.
                check=((raw[name+'__effective_drive_estimate']-truth)/detail['truth']['drive'])[:,16:]
                np.testing.assert_allclose((check**2).mean(axis=1),actual_mse,atol=1e-14)
                collected[name].append({'prior_mse':prior_mse,'prior_bias':error[:,16:].mean(axis=1),
                                        'observation_mse':actual_mse,'prior_minus_observation_mse':prior_mse-actual_mse})
    def metric(values,root=False):
        a=np.stack(values);clusters=rng.integers(len(a),size=(3000,len(a)))
        rows=rng.integers(a.shape[1],size=(*clusters.shape,a.shape[1]));boot=a[clusters[:,:,None],rows].mean(axis=(1,2))
        value=a.mean();ci=np.quantile(boot,[.025,.975]);per=a.mean(axis=1)
        if root:value=np.sqrt(value);ci=np.sqrt(ci);per=np.sqrt(per)
        return {'value':float(value),'hierarchical_bootstrap_95':ci.tolist(),'pipeline_values':per.tolist()}
    cases={}
    for name,rows in collected.items():
        cases[name]={'prior_only_rmse':metric([x['prior_mse'] for x in rows],True),
                     'observation_based_rmse':metric([x['observation_mse'] for x in rows],True),
                     'prior_only_bias':metric([x['prior_bias'] for x in rows]),
                     'paired_prior_minus_observation_mse':metric([x['prior_minus_observation_mse'] for x in rows])}
    output={'scope':__doc__.strip(),'source_sha256':r.sha(Path(__file__)),
            'main_results_sha256':r.sha(directory/'results.json'),'raw_sha256':hashes,
            'bootstrap_seed':seed,'bootstrap_replicates':3000,
            'uncertainty_scope':'Descriptive four-pipeline hierarchical bootstrap, no calibrated coverage or multiplicity-adjusted discovery claims.',
            'formula':'E[Omega_t] = fitted_Omega * (1 + fitted_fraction * .25 * [P_step(z_t=1)+P_telegraph(z_t=1)]); no observation update.',
            'prior_traces':traces,'cases':cases}
    r.write(directory/'prior_only_estimation_control.json',output)
    names=list(cases);x=np.arange(len(names))
    labels=['Stable','20% step','20% telegraph','10% step','Fast telegraph','Efficiency loss','Dark counts','Emitter detuning','Cavity loss','Dead time','Afterpulse','Combined detector','Step + loss']
    fig,ax=plt.subplots(figsize=(13,6))
    ax.bar(x-.25,[cases[n]['observation_based_rmse']['value'] for n in names],.25,label='Uses recorded bits',color='#137177')
    ax.bar(x,[cases[n]['prior_only_rmse']['value'] for n in names],.25,label='Same fitted prior; ignores these bits',color='#d18841')
    ax.bar(x+.25,[result['cases'][n]['zero_change_fraction_rmse']['value'] for n in names],.25,label='Keep fitted baseline unchanged',color='#869497')
    ax.set_xticks(x,labels,rotation=30,ha='right');ax.set_ylabel('RMS effective-drive error / true baseline')
    ax.set_title('Does the record add estimation value beyond the prior?')
    ax.legend(fontsize=9);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.text(.5,.015,'Post-holdout descriptive control. Frozen records, training and thresholds unchanged; no general inference or sensing advantage established.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(directory/'prior_only_comparison.png',dpi=160);plt.close(fig)
    print(json.dumps({'output':str(directory/'prior_only_estimation_control.json'),'main_unchanged':True,'cases':len(cases)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args();main(args.run)
