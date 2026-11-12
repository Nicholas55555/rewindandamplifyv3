"""Plot the saved illustrative benchmark; never fit or alter reference data."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=HERE/'results.json')
    parser.add_argument('--output', type=Path, default=HERE/'coherence_bridge.png')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    receipt_path = args.output.with_suffix('.json')
    if not args.overwrite and (args.output.exists() or receipt_path.exists()):
        parser.error('Output already exists; choose a new output or explicitly request --overwrite')
    data = json.loads(args.results.read_text(encoding='utf-8'))
    cases = data['benchmark_cases']
    trap = data['classical_trap_pair_comparison']
    loss = data['collection_loss_sweep']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.labelcolor': '#173140', 'text.color': '#173140',
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(15.8, 5.9), gridspec_kw={'width_ratios': [1.25, 1.1, 1]})
    fig.patch.set_facecolor('#fcfbf7')
    for ax in axes:
        ax.set_facecolor('#fcfbf7')
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#dce2e3', linewidth=.7)
    x = np.arange(len(cases))
    axes[0].bar(x-.17, [r['single_photon_survival_probability'] for r in cases], .32,
                color='#9caeb7', label='Survival probability / photon')
    bars = axes[0].bar(x+.17, [r['conditional_overlap'] for r in cases], .32,
                       color='#087f8c', label='HOM overlap, given a pair')
    for bar in bars:
        axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+.025,
                     f'{bar.get_height():.0%}', ha='center', fontsize=10, fontweight='bold')
    axes[0].set_xticks(x, ['Ideal', 'Phase\nnoise', 'Frequency\nmismatch', 'Both'])
    axes[0].set_ylim(0, 1.18)
    axes[0].set_ylabel('Probability or conditional overlap')
    axes[0].set_title('Same photon count; different coherence', fontsize=12, fontweight='bold', pad=14)
    axes[0].legend(loc='upper center', bbox_to_anchor=(.5, -.18), frameon=False, fontsize=9)
    p = [r['switch_probability_between_endpoints'] for r in trap]
    overlap = [r['conditional_overlap'] for r in trap]
    axes[1].plot(p, overlap, color='#ad6510', marker='o', linewidth=2.5, markersize=7)
    axes[1].set_xlim(-.025, .53)
    axes[1].set_ylim(.5, 1.12)
    axes[1].set_xlabel('Probability the two offsets differ')
    axes[1].set_ylabel('Pair HOM overlap')
    axes[1].set_title('Environmental memory changes a pair', fontsize=12, fontweight='bold', pad=14)
    axes[1].annotate('Persistent offsets\nM = 1.00', xy=(0, 1), xytext=(.035, 1.025), fontsize=10)
    axes[1].annotate('Independent offsets\nM = 0.60', xy=(.5, .6), xytext=(.16, .55), fontsize=10)
    axes[1].text(.5, -.32, 'Single-photon offset distribution\nstays the same.',
                 transform=axes[1].transAxes, ha='center', va='top', fontsize=9)
    selected = [next(row for row in loss if row['single_photon_survival_probability'] == eta)
                for eta in [.8, .2]]
    attempts = [row['expected_excitation_pairs_per_surviving_pair'] for row in selected]
    bars = axes[2].bar([0, 1], attempts, color=['#087f8c', '#ad6510'], width=.55)
    for bar in bars:
        axes[2].text(bar.get_x()+bar.get_width()/2, bar.get_height()+.7,
                     f'{bar.get_height():.2f}'.rstrip('0').rstrip('.'), ha='center', fontweight='bold')
    axes[2].set_xticks([0, 1], ['80% survival\nper photon', '20% survival\nper photon'])
    axes[2].set_ylim(0, 31)
    axes[2].set_ylabel('Expected excitation pairs / available pair')
    axes[2].set_title('Loss changes the acquisition cost', fontsize=12, fontweight='bold', pad=14)
    axes[2].text(.5, .94, '16x more attempts', transform=axes[2].transAxes,
                 ha='center', fontsize=12, fontweight='bold', color='#ad6510')
    axes[2].text(.5, -.32, 'Pair survival is eta squared.\nConditional overlap stays fixed.',
                 transform=axes[2].transAxes, ha='center', va='top', fontsize=9)
    fig.suptitle('Photon brightness is only one measure of a quantum-dot source',
                 x=.06, y=.98, ha='left', fontsize=18, fontweight='bold')
    fig.text(.06, .91, 'Illustrative two-level model: T1 = 1 ns; ideal one-photon preparation; no fabricated-device fit.', fontsize=11)
    fig.text(.06, .02, 'g2(0) = 0 is imposed in every case. HOM requires mode alignment and a calibrated reference; it does not uniquely identify a defect.', fontsize=10)
    fig.subplots_adjust(left=.065, right=.98, top=.80, bottom=.26, wspace=.45)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    receipt = {'figure': args.output.name, 'results': args.results.name,
               'results_sha256': hashlib.sha256(args.results.read_bytes()).hexdigest(),
               'plot_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'figure_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
               'scope': 'Plot of saved synthetic benchmark values, no external experimental data fitted.'}
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
