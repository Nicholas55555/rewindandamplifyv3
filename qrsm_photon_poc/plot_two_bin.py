"""Visualize the saved two-bin photon-circuit experiment; no simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root/'generated/two_bin_double.json')
    parser.add_argument('--output', type=Path, default=root/'generated/two_bin_summary.png')
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if data['model']['event'] != 'double' or data['compilation'] is None:
        raise ValueError('Expected compiled double-click experiment')
    e, c, m = data['event'], data['compilation'], data['model']
    values = [100*e['original_open_system_probability'], 100*e['retained_model_probability'],
              100*e['qiskit_amplified_probability']]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), gridspec_kw={'width_ratios':[1.35, 1]},
                             layout='constrained')
    bars = axes[0].bar(['Original\nchannel', 'Coarse retained\nmodel', 'After one ideal\nGrover round'],
                       values, color=['#7b96a4', '#3a8292', '#dc873d'], width=.65)
    axes[0].set_ylabel('Probability of click in both modeled bins (%)')
    axes[0].set_title('The marked model history becomes more common', fontsize=11, weight='bold')
    axes[0].set_ylim(0, max(values)*1.25)
    for bar, val in zip(bars, values):
        axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(values)*.025,
                     f'{val:.3f}%', ha='center', fontsize=10)
    axes[1].axis('off')
    text = (f"{m['total_qubits']} circuit qubits\n{c['cx_gates']:,} generic CX gates\n"
            f"{c['depth']:,} generic depth\n\n"
            f"Selected-state trace distance:\n"
            f"amplified vs retained  {e['amplified_vs_retained_conditional_state_trace_distance']:.1e}\n"
            f"retained vs original     {e['retained_vs_original_conditional_state_trace_distance']:.4f}\n\n"
            "One initial state and record;\nnot a worst-case error bound.")
    axes[1].text(.03, .95, text, transform=axes[1].transAxes, va='top',
                 fontsize=10.2, linespacing=1.55,
                 bbox={'boxstyle':'round,pad=1', 'facecolor':'#edf4f3', 'edgecolor':'#c2d8d4'})
    fig.suptitle('Two-bin photon model: a coherent rare-history query', fontsize=14, weight='bold')
    fig.text(.5, -.035, 'Synthetic cavity-2, coarse channel approximation, ideal Qiskit statevector; '
             'no real photon measurement or hardware noise.', ha='center', fontsize=9, color='#444')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(args.output)


if __name__ == '__main__':
    main()
