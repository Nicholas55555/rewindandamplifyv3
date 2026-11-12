"""Render frozen forward-model and held-out evidence, without rerunning fits."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    r=json.loads((HERE/'main/results.json').read_text(encoding='utf-8'))
    bundle=json.loads((HERE/'hardware_bundle_v2/manifest.json').read_text(encoding='utf-8'))
    reg=r['regimes'][1]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(15.5,5.8),gridspec_kw={'width_ratios':[1,1.35,1]})
    a=next(x for x in bundle['circuits'] if x['name']=='controlled_two_coherent_Z')['exact_flag_history_probabilities']
    b=next(x for x in bundle['circuits'] if x['name']=='controlled_two_classical_Z')['exact_flag_history_probabilities']
    x=np.arange(4)
    axes[0].bar(x-.18,list(a.values()),width=.35,color='#237aa5',label='Coherent gap model')
    axes[0].bar(x+.18,list(b.values()),width=.35,color='#d78c35',label='Dephased classical gap')
    axes[0].set(xticks=x,xticklabels=list(a),ylabel='Ideal joint-record probability',xlabel='Two-pair history;1 = coincidence',title='The controlled joint effect is small')
    axes[0].legend(frameon=False,fontsize=8.5)
    axes[0].text(.98,.66,'Same single-pair probability:\n0.275 for both hypotheses',transform=axes[0].transAxes,ha='right',fontsize=9)
    names=['Coherent\nsource','Classical\nnull','Readout\nshift','Lower\ncollection','Mode\nmismatch','Partial\ndephasing']
    colors=['#237aa5','#77838d','#d78c35','#d78c35','#d78c35','#237aa5']
    for i,(case,color) in enumerate(zip(reg['cases'],colors)):
        value=100*case['flag_rate'];ci=100*np.array(case['flag_rate_wilson95'])
        axes[1].errorbar(i,value,yerr=[[value-ci[0]],[ci[1]-value]],fmt='o',color=color,capsize=4,ms=6)
    axes[1].axhline(5,color='#77838d',ls='--',lw=1)
    axes[1].set(xticks=np.arange(6),xticklabels=names,ylabel='Records favoring coherent hypothesis (%)',ylim=(-.4,9),title='64 attempted pairs: weak discrimination')
    axes[1].tick_params(axis='x',labelsize=8.5)
    axes[1].text(.97,.96,'2,000 held-out records / case\n95% conditional Wilson intervals',transform=axes[1].transAxes,ha='right',va='top',fontsize=8.5)
    labels=['Specified\nclassical','Previous\noutcome','2-state\nHMM','4-state\nHMM']
    keys=['physical_classical_calibrated','markov_previous_outcome','hmm_2','hmm_4']
    for i,key in enumerate(keys):
        value=reg['heldout_prediction_scores'][key]['paired_gain_vs_physical_coherent_nats_per_trial']
        mean=1e4*value['mean'];ci=1e4*np.array(value['approximate_interval95'])
        axes[2].errorbar(i,mean,yerr=[[mean-ci[0]],[ci[1]-mean]],fmt='o',color='#58794c',capsize=4,ms=6)
    axes[2].axhline(0,color='#77838d',ls='--',lw=1)
    axes[2].set(xticks=np.arange(4),xticklabels=labels,ylabel='Log-score gain vs coherent model (×10⁻⁴ nats/trial)',title='Classical prediction is close')
    axes[2].tick_params(axis='x',labelsize=8.5)
    for ax in axes:ax.grid(axis='y',alpha=.16)
    fig.suptitle('A joint-photon instrument is implemented; useful diagnosis is not established',fontsize=17,fontweight='bold',y=.96)
    fig.text(.5,.075,'Passive measurement is exactly uninformative for these hypotheses. Controlled nominal flag rates:5.60% coherent versus4.50% classical null.\n'
             'All data here are synthetic. Known physical parameters favor the specified model; HMMs learn from1,000 records. Intervals exclude model and calibration drift uncertainty.',ha='center',fontsize=9,color='#4b555d')
    fig.subplots_adjust(left=.06,right=.985,top=.82,bottom=.25,wspace=.37)
    outputs={}
    for ext in ['png','pdf']:
        path=HERE/f'joint_photon_results.{ext}'
        fig.savefig(path,dpi=180,facecolor='white',metadata={'CreationDate':None,'ModDate':None} if ext=='pdf' else None)
        outputs[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    plt.close(fig)
    record={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'results_sha256':hashlib.sha256((HERE/'main/results.json').read_bytes()).hexdigest(),
            'hardware_manifest_sha256':hashlib.sha256((HERE/'hardware_bundle_v2/manifest.json').read_bytes()).hexdigest(),
            'artifacts':outputs,'scope':'Saved ideal digital-model probabilities and synthetic held-out results, not physical-device performance'}
    (HERE/'plot_manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
