"""Render saved exact-design and prospective-validation evidence."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    r=json.loads((HERE/'validation_run/results.json').read_text(encoding='utf-8'))
    d=json.loads((HERE/'design_results.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'font.family':'DejaVu Sans'})
    fig,axes=plt.subplots(2,2,figsize=(14.5,9.0))
    fig.subplots_adjust(left=.075,right=.975,top=.87,bottom=.13,hspace=.52,wspace=.28)
    blue='#217f9e';gray='#747f87';orange='#dc8b30';purple='#815593';green='#577c50'
    x=np.array([b['attempted_pairs'] for b in r['power_trials']])
    a=axes[0,0]
    for name,label,color in [('coherent_nominal','Coherent nominal',blue),('classical_nominal','Classical nominal false flags',gray)]:
        rows=[next(c for c in b['cases'] if c['name']==name) for b in r['power_trials']]
        y=np.array([c['flag_rate']*100 for c in rows]);ci=np.array([c['wilson95'] for c in rows]).T*100
        a.errorbar(x,y,yerr=np.maximum(0,[y-ci[0],ci[1]-y]),color=color,marker='o',label=label,capsize=2,lw=1.7)
    a.axhline(80,color=blue,ls=':',lw=.8);a.set(xscale='log',ylim=(-2,104),xlabel='Attempted pairs per record (log scale)',ylabel='Flag rate (%)',title='Nominal power grows with a larger reset-block budget')
    a.legend(frameon=False,loc='upper left');a.grid(axis='y',alpha=.17)
    a.text(.97,.08,'2,000 held-out records per point\nConditional Wilson95 intervals',transform=a.transAxes,ha='right',color=gray,fontsize=9)
    a=axes[0,1]
    for name,label,color in [('classical_readout_shift','Readout changed',orange),('classical_mode_mismatch','Mode overlap .85',purple),('classical_loss_shift','Collection .8 → .5',green)]:
        rows=[next(c for c in b['cases'] if c['name']==name) for b in r['power_trials']]
        a.plot(x,[c['flag_rate']*100 for c in rows],'o-',color=color,label=label)
    a.axhline(5,color=gray,ls='--',lw=1);a.set(xscale='log',ylim=(-2,80),xlabel='Attempted pairs per record (log scale)',ylabel='False flags on classical sources (%)',title='More data can amplify acquisition-model mistakes')
    a.legend(frameon=False);a.grid(axis='y',alpha=.17)
    a=axes[1,0]
    for design,label,color in [('selected','Selected finite-grid design',blue),('original_prefix','Original four-pair prefix',gray)]:
        rows=sorted([row for row in d['loss_sensitivity'] if row['design']==design and row['acquisition']=='nominal_confusion'],key=lambda row:row['parameters']['eta'])
        a.plot([row['parameters']['eta'] for row in rows],[4*row['information']['sufficient_independent_blocks_alpha05_power80'] for row in rows],marker='o',color=color,label=label)
    a.set(yscale='log',xlabel='Per-photon survival probability',ylabel='Sufficient attempted pairs (log scale)',title='Loss makes the sufficient budget expensive')
    a.legend(frameon=False);a.grid(axis='y',alpha=.17)
    a.text(.98,.47,'Exact known models; independent perfect resets\n5% false-flag / 80% power sufficient bound',transform=a.transAxes,ha='right',fontsize=9,color=gray,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none','pad':2})
    a=axes[1,1]
    names=['hmm_4','hmm_8','saturated_categorical_fit','exact_classical_categorical_oracle']
    labels=['4-state HMM','8-state HMM','Fitted 81-outcome\nclassical law','Exact classical\ncategorical oracle']
    for i,name in enumerate(names):
        s=r['prediction_scores'][name]['paired_gain_vs_calibrated_physical'];y=s['mean']*1e4;low,high=np.array(s['approximate_interval95'])*1e4
        a.errorbar(i,y,yerr=[[y-low],[high-y]],color=green,fmt='o',capsize=4)
    a.axhline(0,color=gray,ls='--',lw=1);a.set_xticks(range(len(labels)),labels,fontsize=9)
    a.set(ylabel='Gain vs calibrated physical model\n(×10⁻⁴ nats per attempted pair)',title='A stronger learned classical HMM is competitive')
    a.grid(axis='y',alpha=.17)
    fig.suptitle('A better control helps nominal inference; calibration ambiguity remains',fontsize=18,fontweight='bold',y=.96)
    fig.text(.5,.915,'Exploratory model selection → separately specified fresh validation. Original study and hardware circuits remain unchanged.',ha='center',fontsize=11,color=gray)
    fig.text(.5,.045,'Synthetic four-pair blocks, with environment reset to I/2 between blocks. Reset fidelity/time and source-control feasibility are untested.\nHMMs use the same 20,000 training blocks; physical predictors know source parameters. All 20 local EM starts hit the 200-iteration cap. No unique quantum-memory diagnosis.',ha='center',fontsize=9,color=gray)
    outputs=[]
    for suffix in ['png','pdf']:
        target=HERE/f'design_validation.{suffix}'
        options={'dpi':180} if suffix=='png' else {'metadata':{'CreationDate':None,'ModDate':None}}
        fig.savefig(target,**options);outputs.append(target.name)
    plt.close(fig)
    m={'source_sha256':digest(Path(__file__)),'design_results_sha256':digest(HERE/'design_results.json'),
       'validation_results_sha256':digest(HERE/'validation_run/results.json'),
       'artifacts':{name:digest(HERE/name) for name in outputs},'scope':'Exact model-based design and conditional synthetic validation, not measured optical performance.'}
    (HERE/'plot_manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    print('Saved design_validation.png and .pdf')


if __name__=='__main__':main()
