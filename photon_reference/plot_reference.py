"""Replot publicly released photon-correlation data and its published fit.

This is third-party experimental data for context, not a fit or measurement by
the Rewind & Amplify team. Source, original checksums and license in README.md.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    folder = Path(__file__).resolve().parent
    measured = np.loadtxt(folder / 'fig3a.dat')
    published_fit = np.loadtxt(folder / 'fig3a_fit.dat')
    fig, ax = plt.subplots(figsize=(8.4, 4.5), layout='constrained')
    ax.plot(measured[:, 0], measured[:, 1], '.', color='#2866a3', markersize=4,
            label='Published measured correlation')
    ax.plot(published_fit[:, 0], published_fit[:, 1], color='#d87931', linewidth=2,
            label="Original authors' fit")
    ax.axhline(1, linestyle=':', color='#8a9196', linewidth=1)
    ax.set_xlabel('Photon detection delay τ (ns)')
    ax.set_ylabel('Normalized correlation $g^{(2)}(τ)$')
    ax.set_title('A measured photon-correlation trace from an hBN emitter', weight='bold')
    ax.legend(loc='upper right')
    ax.grid(alpha=.15)
    fig.text(.5, -.035,
             'Fournier et al., Phys. Rev. B 107, 195304 (2023), Fig. 3a data and fit; '
             'Zenodo 10.5281/zenodo.7938744, CC BY 4.0', ha='center', fontsize=8, color='#444')
    fig.savefig(folder / 'published_photon_correlation.png', dpi=160, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
