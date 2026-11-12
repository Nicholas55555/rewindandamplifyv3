"""Render actual saved results; no illustration is substituted for data."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'figure.facecolor':'#f8fafb','axes.facecolor':'#f8fafb'})
COLORS={'direct':'#64748b','original_fixed_tilt':'#bc6a32','pilot_tuned_exponential':'#087f83'}


def main():
    d=json.loads((ROOT/'correlated_spatial_results.json').read_text())
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    ax=axes[0,0]
    weights=np.array(d['response']['weights_normalized']).reshape(2,2)
    ax.imshow(weights,cmap='Blues',vmin=0,vmax=4/9)
    for y in range(2):
        for x in range(2): ax.text(x,y,f'{round(weights[y,x]*9)}/9',ha='center',va='center',fontsize=24,color='white' if weights[y,x]>.3 else '#142b44')
    ax.set_xticks([0,1]);ax.set_yticks([0,1]);ax.set_xlabel('Cell column');ax.set_ylabel('Cell row')
    ax.set_title('A. Spatial response to four Poisson counts\nGaussian corner weights; event: response < 1/3')
    ax=axes[0,1];c=d['exact_classical']
    ax.bar([0,1],100*np.array([c['independent_same_marginals_event_probability'],c['event_probability']]),color=['#64748b','#087f83'])
    ax.set_xticks([0,1],['Independent cells','Shared dose fluctuation'])
    ax.set_ylabel('Exact low-response probability (%)')
    ax.set_title('B. Correlation changes rare-event probability\nIdentical single-cell marginal distributions')
    for i,p in enumerate([c['independent_same_marginals_event_probability'],c['event_probability']]):
        ax.text(i,100*p+.012,f'{100*p:.4f}%',ha='center')
    ax.set_ylim(0,.45)
    for col,quantity in enumerate(('hit_probability','conditional_joint_tv')):
        ax=axes[1,col]
        for level,color,label in [(0,'#64748b','Ideal'),(.0001,'#087f83','CX depol. 0.0001; readout 0.001'),(.001,'#bc6a32','CX depol. 0.001; readout 0.01')]:
            rows=[r for r in d['noise_cases'] if r['status']=='completed' and r['cx_depolarizing_parameter']==level]
            ax.plot([r['rounds'] for r in rows],[100*r['after_readout'][quantity] for r in rows],marker='o',color=color,label=label)
        ax.set_xticks([0,1,2],['0\n144 CX','1\n988 CX','2\n1,832 CX'])
        ax.set_xlabel('Rounds; full generic circuit cost')
        ax.set_ylabel('Matching output probability (%)' if col==0 else 'Conditional joint TV distance (%)')
        ax.set_title(('C. More matches can include error' if col==0 else 'D. Accepted-map fidelity must also be checked')+'\n9-qubit enumerated circuit; exact density simulation')
        ax.grid(alpha=.15)
    axes[1,0].legend(fontsize=8,loc='upper left')
    fig.suptitle('A coherent circuit for a correlated spatial exposure model',fontsize=17,weight='bold')
    fig.supxlabel('Synthetic, dimensionless model. Exact classical DP solves this example without rejection. No wafer or hardware results.',fontsize=10)
    fig.savefig(ROOT/'correlated_spatial_bridge.png',dpi=170)
    plt.close(fig)

    d=json.loads((ROOT/'spatial_coverage_refined_results.json').read_text())
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    labels=['Direct\nWilson CI','Original fixed tilt\nnormal CI','Pilot-tuned tilt\nnormal CI']
    for column,dose in enumerate(d['doses']):
        ax=axes[0,column];ref=dose['reference'];mid=(ref['lower']+ref['upper'])/2
        for x,(name,method) in enumerate(dose['methods'].items()):
            values=np.array([r['estimate'] for r in method['runs']])/mid
            # Deterministic spreading prevents overlaps; not random data jitter.
            offsets=.14*np.sin(np.arange(len(values))*2.39996323)
            ax.scatter(x+offsets,values,s=10,alpha=.5,color=COLORS[name])
        ax.axhspan(ref['lower']/mid,ref['upper']/mid,color='black',alpha=.2)
        ax.axhline(1,color='#1f2937',lw=1)
        ax.set_xticks(range(3),labels);ax.set_ylabel('Estimate / deterministic reference midpoint')
        ax.set_title(f'Mean count per cell {dose["dose"]}\n100 held-out runs × 20,000 maps per method')
        ax.grid(axis='y',alpha=.15)
        ax=axes[1,column]
        for x,(name,method) in enumerate(dose['methods'].items()):
            s=method['summary'];lo,hi=s['coverage95_fraction_bounds'];wlo,whi=s['coverage_sampling_wilson95_outer']
            ax.errorbar(x,100*(lo+hi)/2,yerr=[[100*((lo+hi)/2-wlo)],[100*(whi-(lo+hi)/2)]],fmt='o',capsize=5,color=COLORS[name])
            label=f'{round(100*lo)} / 100' if lo==hi else f'{round(100*lo)}–{round(100*hi)} / 100'
            ax.text(x,100*lo-7,label,ha='center',fontsize=9)
        ax.axhline(95,color='#1f2937',ls='--',lw=1)
        ax.set_ylim(65,102);ax.set_xlim(-.45,2.45);ax.set_xticks(range(3),labels);ax.set_ylabel('Observed coverage of nominal 95% intervals (%)')
        ax.set_title('Bars: finite-repeat Wilson uncertainty\nLabel range: deterministic reference ambiguity')
        ax.grid(axis='y',alpha=.15)
    fig.suptitle('Testing uncertainty on the original 7×7 spatial process',fontsize=17,weight='bold')
    fig.supxlabel('Classical synthetic model. Tuned method adds 40,000 independent pilot maps per dose. Held-out results never tune the proposal.',fontsize=10)
    fig.savefig(ROOT/'spatial_coverage.png',dpi=170)
    plt.close(fig)


if __name__=='__main__':main()
