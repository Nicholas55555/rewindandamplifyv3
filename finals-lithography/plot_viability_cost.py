"""Plot the saved synthetic round-count study; no new data are generated."""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    root=Path(__file__).resolve().parent
    fig,axes=plt.subplots(1,2,figsize=(11,4.6),sharey=True)
    fig.subplots_adjust(top=.73,bottom=.21,left=.09,right=.98,wspace=.10)
    for ax,n in zip(axes,(5,7)):
        source=json.loads((root/f'viability_cost_n{n}.json').read_text(encoding='utf-8'))
        rows=source['quantum_cases']
        x=[r['rounds'] for r in rows]
        ax.plot(x,[r['ideal']['hit_probability'] for r in rows],marker='o',color='#577588',label='Ideal event probability')
        ax.plot(x,[r['noisy_after_readout']['hit_probability'] for r in rows],marker='o',color='#d77437',label='Noisy matching-bit rate')
        ax.plot(x,[r['noisy_after_readout']['conditional_tv'] for r in rows],marker='s',color='#147d71',label='Noisy conditional-history TV')
        ax.set_xticks(x,[f"{r['rounds']}\n{r['routed_instruction_counts'].get('cx',0):,} CX" for r in rows])
        ax.set_xlabel('Amplification rounds and routed CX gates')
        ax.set_title(f'{n} synthetic absorption sites',weight='bold')
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Probability or total variation distance')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.88),ncol=3,frameon=False,fontsize=9)
    fig.suptitle('Synthetic noise can raise match rates while bias also grows',y=.98,weight='bold')
    fig.text(.5,.035,'One synthetic line target; layouts differ by circuit. Density-matrix probabilities, not hardware or wafer data.',
             ha='center',fontsize=9,color='#555')
    fig.savefig(root/'viability_cost_tradeoff.png',dpi=160,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':main()
