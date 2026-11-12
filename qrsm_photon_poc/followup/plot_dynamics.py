from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'dynamics_results.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
for n,color in zip(['2','3','4','6'],['#b76329','#8577a8','#248895','#173b55']):
    row=r['cutoff']['default']['dimensions'][n]
    axes[0].plot(np.arange(1,41),np.array(row['click'])*100,label=f'Cavity dimension {n}',color=color)
axes[0].set(xlabel='Model time bin',ylabel='Click probability (%)',title='Default model: finite-cavity predictions')
axes[0].legend(fontsize=9)
for case,label in [('default','Default'),('high_drive','Higher drive'),('high_coupling','Higher coupling')]:
    dims=r['cutoff'][case]['dimensions']
    axes[1].semilogy(range(2,6),[dims[str(n)]['max_conditional_difference_vs_dimension6']*100 for n in range(2,6)],'o-',label=label)
axes[1].set(xlabel='Cavity dimension',ylabel='Maximum absolute difference (percentage points)',
            title='After-step-3 prediction error versus dimension 6',xticks=[2,3,4,5])
axes[1].legend(fontsize=9)
fig.suptitle('Truncation sensitivity of a synthetic photon model',fontsize=14)
fig.savefig(HERE/'cavity_cutoff.png',dpi=180)
plt.close(fig)
print(HERE/'cavity_cutoff.png')
