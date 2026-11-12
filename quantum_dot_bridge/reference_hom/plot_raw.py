"""Plot unchanged imported counts; no normalization, fit, subtraction or rebinning."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from import_verify import HERE, FILES, audit, read_histogram


def main():
    result = audit()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.titleweight':'bold'})
    fig, axes = plt.subplots(3,2,figsize=(12.6,9.5),layout='constrained')
    for row,separation in enumerate((13.1,26.2,39.4)):
        for filename,md5,_,pulse_delay,polarization in FILES:
            if pulse_delay != separation:
                continue
            times,counts = read_histogram(HERE/filename,md5)
            x = [value/1000 for value in times]
            color = '#147D8C' if polarization=='co' else '#AD6711'
            label = 'Co-polarized' if polarization=='co' else 'Cross-polarized'
            for ax in axes[row]:
                ax.step(x,counts,where='mid',color=color,lw=.9,alpha=.85,label=label)
        axes[row,0].set(title=f'{separation:g} ns excitation separation — full recorded grid',
                         xlim=(-125,125),ylabel='Raw coincidence counts / 50 ps bin')
        axes[row,1].set(title=f'{separation:g} ns excitation separation — central region',xlim=(-2,2))
        for ax in axes[row]:
            ax.set_xlabel('Recorded coincidence delay (ns)')
            ax.grid(axis='y',alpha=.18)
            ax.set_ylim(bottom=0)
            ax.legend(loc='upper right',fontsize=8)
    fig.suptitle('External GaAs quantum-dot HOM histograms\nRaw counts; acquisition exposure and relative normalization not established here',fontsize=14)
    fig.supxlabel('Münzberg et al. · Zenodo 10.5281/zenodo.6337697 · CC BY 4.0\nProject replot only: no derived visibility, fitted source model or lithography measurement',fontsize=9)
    png=HERE/'raw_hom_histograms.png'; pdf=HERE/'raw_hom_histograms.pdf'
    fig.savefig(png,dpi=150)
    fig.savefig(pdf)
    plt.close(fig)
    output = {'scope':'Unnormalized raw-count replot, not a HOM-visibility reproduction',
              'source_sha256':{r['path']:r['sha256'] for r in result['files']},
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'matplotlib_version':matplotlib.__version__,
              'axis_transform':'Time (ps) divided by 1000 for ns display; no source-grid shift',
              'counts_transform':'none; no exposure normalization, smoothing, subtraction or rebinning',
              'central_plot_limits_ns':[-2,2],
              'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (png,pdf)}}
    (HERE/'plot_manifest.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'png':png.name,'pdf':pdf.name,'normalized':False}))


if __name__=='__main__':
    main()
