"""Run a controlled synthetic-data recovery test and save figures/results."""
import argparse
from dataclasses import replace,asdict
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from qrsm_photon import (Parameters,instruments,init_state,sample_records,fit_coupling,
                         conditional_click_probability,_traces)

ROOT=Path(__file__).resolve().parent
OUTPUT_NAMES=('poc_results.png', 'synthetic_click_records.csv', 'no_defect_control.csv', 'results.json')


def prepare_output(out_dir, overwrite):
    """Keep bundled reference artifacts intact, and guard prior generated runs."""
    path=Path(out_dir).expanduser().resolve()
    if path == ROOT:
        raise ValueError('Output must be separate from the bundled reference files')
    existing=[path/name for name in OUTPUT_NAMES if (path/name).exists()]
    if existing and not overwrite:
        raise FileExistsError(f'{existing[0]} exists; choose another --outdir or pass --overwrite')
    path.mkdir(parents=True,exist_ok=True)
    return path

def cavity_top_occupancy(p,steps=40):
    no,yes,E=instruments(p)
    state=init_state(p)
    d=4*p.n_cavity
    ix=np.arange(d)
    cavlevel=(ix%p.n_cavity)==(p.n_cavity-1)
    out=[]
    for _ in range(steps):
        state=E@state
        rho=state.reshape((d,d),order='F')
        out.append(float(np.real(np.diag(rho)[cavlevel].sum())))
    return max(out),out[-1]

def run(n_records=600, steps=40, seed=77, show_no_defect=True,
        out_dir=ROOT/'generated', overwrite=False):
    if n_records < 2 or steps < 9:
        raise ValueError('At least 2 records and 9 steps are required for this analysis')
    out=prepare_output(out_dir, overwrite)
    p=Parameters()
    records=sample_records(p,n_records,steps,seed)
    grid=np.linspace(0,1.25,26)
    fit=fit_coupling(records,p,grid)
    baseline,conditional=conditional_click_probability(records,8)
    # A separate synthetic control, genuinely generated without the defect interaction.
    nullp=replace(p,g_defect=0.0)
    nullrecs=sample_records(nullp,n_records,steps,seed+100)
    nullfit=fit_coupling(nullrecs,p,grid) if show_no_defect else None
    nullbase,nullcond=conditional_click_probability(nullrecs,8)
    cutoff3=cavity_top_occupancy(p)
    # Compare same physical parameters at higher cavity Fock cutoff; top occupation must stay small.
    cutoff4=cavity_top_occupancy(replace(p,n_cavity=4))

    # Figure 1: 4 panels share a unified reproducible experiment.
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(12.2,8.0),constrained_layout=True)
    take=min(28,n_records)
    for arr,color,label,offset in [(records,'#2563eb','hidden defect',0),
                                    (nullrecs,'#ea580c','no defect',take+4)]:
        # Show same 28 example histories with faint gray marks and detected clicks highlighted.
        ys,xs=np.where(arr[:take]>0)
        axs[0,0].scatter(xs,ys+offset,
                         s=24,c=color,marker='|',linewidth=1.7,label=label)
    axs[0,0].set_xlim(-.5,steps-.5)
    axs[0,0].set_ylim(2*take+3.5,-1)
    axs[0,0].set_yticks([(take-1)/2,take+4+(take-1)/2],['defect records','control records'])
    axs[0,0].set_xlabel('Time bin')
    axs[0,0].set_title('Photon click records: representative samples')

    axs[0,1].plot(grid,fit['log_likelihood']-max(fit['log_likelihood']),
                  '-o',color='#2563eb',ms=3.6,label='data with defect')
    if nullfit is not None:
        axs[0,1].plot(grid,nullfit['log_likelihood']-max(nullfit['log_likelihood']),
                      '-o',color='#ea580c',ms=3.6,label='no-defect control')
    axs[0,1].axvline(p.g_defect,color='#2563eb',linestyle=':',label='true g = %.2f'%p.g_defect)
    axs[0,1].set_xlabel('Assumed defect–emitter coupling g (arb. units)')
    axs[0,1].set_ylabel('Relative log likelihood (max = 0)')
    axs[0,1].set_title('Can the hidden coupling be recovered?')
    axs[0,1].legend(fontsize=8)

    xx=np.arange(1,9)
    axs[1,0].axhline(baseline,color='#2563eb',linestyle=':',alpha=.7)
    axs[1,0].axhline(nullbase,color='#ea580c',linestyle=':',alpha=.7)
    axs[1,0].plot(xx,conditional,'-o',label='defect data',color='#2563eb')
    axs[1,0].plot(xx,nullcond,'-o',label='no-defect data',color='#ea580c')
    axs[1,0].set_xlabel('Steps after detected click')
    axs[1,0].set_ylabel('P(later click | earlier click)')
    axs[1,0].set_title('Post-click temporal correlations')
    axs[1,0].legend(fontsize=8)

    pars=['defect g','detuning Δ','emitter–cavity gc','κ (leakage)','η (detection)','dark rate']
    vals=[p.g_defect,p.defect_detuning,p.g_cavity,p.kappa,p.detector_eta,p.dark_rate]
    axs[1,1].axis('off')
    summary=(f'OPEN QUANTUM SYSTEM: SYNTHETIC EXAMPLE\n\n'
             f'2 spin-like qubits + {p.n_cavity}-level photon cavity\n'
             f'Continuous emitter drive; Lindblad loss & dephasing\n'
             f'Binned photon counting (with missed and false clicks)\n\n'
             f'{n_records} independent records × {steps} bins\n'
             f'Defect: g_true={p.g_defect:.2f}, g_fit={fit["g_hat"]:.2f}\n'
             + (f'Null: g_true=0.00, g_fit={nullfit["g_hat"]:.2f}\n' if nullfit is not None
                else 'Null: control fit not requested\n') +
             f'Coupling identification log-likelihood gap: {fit["llr_vs_no_defect"]:.1f}\n'
             f'Maximum n=2 Fock occupation: {cutoff3[0]:.2%}\n'
             f'Cavity cutoff=4 top-level occupation: {cutoff4[0]:.2%}\n\n'
             f'SYNTHETIC ONLY • not a real optical experiment\n'
             f'No speedup or Grover integration demonstrated')
    axs[1,1].text(0,1,summary,va='top',ha='left',fontsize=10.5,
                  family='monospace',linespacing=1.5,transform=axs[1,1].transAxes)
    fig.suptitle('QRSM-inspired emitter–defect–photon proof of concept',fontsize=17,fontweight='bold')
    fig.savefig(out/'poc_results.png',dpi=170,bbox_inches='tight')
    plt.close(fig)

    np.savetxt(out/'synthetic_click_records.csv',records,fmt='%i',delimiter=',')
    np.savetxt(out/'no_defect_control.csv',nullrecs,fmt='%i',delimiter=',')
    output={'parameters':asdict(p), 'n_records':n_records,'steps':steps,'seed':seed,
            'fit':{'g_hat':fit['g_hat'],'g_true':p.g_defect,
                   'llr_vs_no_defect':fit['llr_vs_no_defect'],
                   'grid':grid.tolist(),'log_likelihood':fit['log_likelihood'].tolist()},
            'no_defect_control':({'g_hat':nullfit['g_hat'],
                        'llr_vs_no_defect':nullfit['llr_vs_no_defect']} if nullfit is not None else None),
            'click_rates':{'with_defect':float(records.mean()),
                           'without_defect':float(nullrecs.mean())},
            'photon_cutoff_check':{'n3_occupation_top':cutoff3[0],
                                   'n4_occupation_top':cutoff4[0]},
            'limitation':'Simulated data and fixed known nuisance parameters; neither industrial validation nor quantum speedup'}
    (out/'results.json').write_text(json.dumps(output,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in output.items() if k in ['fit','no_defect_control','click_rates','photon_cutoff_check']},indent=2)[:1800])
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='small 24-record, 16-bin smoke test')
    parser.add_argument('--records', type=int, help='number of records (default: 600)')
    parser.add_argument('--steps', type=int, help='number of bins per record (default: 40)')
    parser.add_argument('--seed', type=int, default=77)
    parser.add_argument('--outdir', type=Path, default=ROOT/'generated', help='separate output directory')
    parser.add_argument('--overwrite', action='store_true', help='replace prior files in the output directory')
    args=parser.parse_args()
    run(n_records=args.records if args.records is not None else (24 if args.quick else 600),
        steps=args.steps if args.steps is not None else (16 if args.quick else 40),
        seed=args.seed, out_dir=args.outdir, overwrite=args.overwrite)
