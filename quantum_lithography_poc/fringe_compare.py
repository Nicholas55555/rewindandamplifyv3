"""Compare ideal two-photon signals for NOON and coherent input states.

This is an exploratory quantum-optics correlation model, not a photoresist,
EUV process, device, wafer simulation, or speedup benchmark. The two models
have equal mean incident photon number (two) and identical arm transmission.
"""
from pathlib import Path
import numpy as np


def signals(phase, transmission=1.0):
    """Return normal-ordered two-photon moments at one output mode.

    Each input arm undergoes identical independent transmission. For the
    normalized output c=(a+exp(i*phase)b)/sqrt(2), evaluate <c†² c²>.
    Input states: (|2,0>+|0,2>)/sqrt(2) and |1>_coh|1>_coh,
    both with total mean incident photon number 2. The coherent amplitudes
    are 1, so their mean photon numbers are 1 per arm (not Fock states).
    """
    if not 0 <= transmission <= 1:
        raise ValueError('transmission must lie between 0 and 1')
    phi = np.asarray(phase, dtype=float)
    if not np.isfinite(phi).all():
        raise ValueError('phase must be finite')
    # Normal ordering makes equal, independent arm loss multiply G2 by eta².
    noon = .5 * (1 + np.cos(2 * phi)) * transmission**2
    coherent = (1 + np.cos(phi))**2 * transmission**2
    return noon, coherent


def main():
    import matplotlib.pyplot as plt
    phi = np.linspace(0, 2*np.pi, 501)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5), constrained_layout=True)
    for ax, eta in zip(axes, [1.0, .5]):
        noon, coherent = signals(phi, eta)
        ax.plot(phi/np.pi, noon, label='2-photon NOON state', color='#d85e2b', lw=2)
        ax.plot(phi/np.pi, coherent, label='Coherent light', color='#1674aa', lw=2)
        ax.set(title=f'Identical arm transmission: {eta:.0%}', xlabel='Relative phase / π',
               ylabel='Two-photon moment  ⟨c†²c²⟩', xlim=(0, 2), ylim=(0, 4.2))
        ax.set_xticks([0, .5, 1, 1.5, 2])
        ax.grid(alpha=.2)
        ax.legend(frameon=False, fontsize=9)
    fig.suptitle('Equal mean incident photons; idealized correlation, not printed features', fontsize=12)
    output = Path(__file__).with_name('fringe_comparison.png')
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    fig.savefig(output, dpi=180)
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
