"""Assess whether published one-second photon counts can be used as click records.

This is a transparent format/observability check, not a physical model fit or
defect diagnosis. Source attribution and measurement limitations: DATA_USE.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'QD5_countrates_18-06-15.csv'
EXPECTED_MD5 = 'c348c2a0c228222469fae33e8113d852'
COLUMNS = ('Timestamp','Ch1','Ch2','Ch3','Ch4','Coin_12','Coin_13','Coin_14',
           'Coin_23','Coin_24','Coin_34','Coin_123','Coin_124','Coin_134',
           'Coin_234','Coin_1234')


def read_counts(path=SOURCE, verify_checksum=True):
    """Read and validate the published fields; do not infer missing photons."""
    path = Path(path)
    content = path.read_bytes()
    digest = hashlib.md5(content).hexdigest()
    if verify_checksum and digest != EXPECTED_MD5:
        raise ValueError(f'source file checksum mismatch: {digest}')
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        header = next(csv.reader(stream))
    if tuple(header) != COLUMNS:
        raise ValueError('unexpected count-data header or column order')
    values = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    if values.ndim != 2 or values.shape[1] != len(COLUMNS) or len(values) < 2:
        raise ValueError('expected at least two records with 16 columns')
    if not np.isfinite(values).all():
        raise ValueError('non-finite values')
    times, counts = values[:, 0], values[:, 1:]
    if np.any(np.diff(times) <= 0):
        raise ValueError('timestamps are not strictly increasing')
    if np.any(counts < 0) or np.any(counts != np.floor(counts)):
        raise ValueError('count values must be nonnegative integers')
    return times, counts, digest


def assess(times, counts, digest):
    dt = np.diff(times)
    fields = {}
    for i, name in enumerate(COLUMNS[1:]):
        values = counts[:, i]
        fields[name] = {'mean_recorded_count_per_integration': float(values.mean()),
                        'min_count': int(values.min()), 'max_count': int(values.max()),
                        'number_zero': int(np.count_nonzero(values == 0)),
                        'number_positive': int(np.count_nonzero(values > 0)),
                        'fraction_positive': float(np.mean(values > 0))}
    return {'source': {'dataset_doi': '10.5281/zenodo.6337697',
                       'publication_doi': '10.1063/5.0091867',
                       'license': 'CC BY 4.0', 'file': SOURCE.name, 'file_md5': digest,
                       'integration_seconds_per_record_as_documented': 1},
            'n_records': len(times),
            'record_timestamp_delta_seconds': {'minimum': float(dt.min()),
                'median': float(np.median(dt)), 'maximum': float(dt.max()),
                'count_over_two_seconds': int(np.count_nonzero(dt > 2))},
            'channels': fields,
            'interpretation': [
                'The file contains 1-second integrated count records, not individual photon arrival times.',
                'A Ch1 >= 1 click/no-click conversion is constant for these data and cannot recover within-bin histories.',
                'Coin_1234 is a four-channel coincidence count, not a substitute single-emitter click record.',
                'Timestamp spacing and exposure duration should not be treated as identical.',
                'These are independent authors\' measured data, not a validation or measurement by Rewind & Amplify.',
            ]}


def render(times, counts, result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    n = min(len(times), 600)
    x = (times[:n] - times[0]) / 60
    ch1, four = counts[:n, 0], counts[:n, -1]
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.4), layout='constrained',
                             gridspec_kw={'height_ratios': [2, .85, .85]})
    fig.suptitle('Measured photon-count data: can we recover click histories?', weight='bold')
    axes[0].plot(x, ch1, color='#286e8d', linewidth=.8)
    axes[0].set_ylabel('Ch1 counts per\n1-second integration')
    axes[0].set_title('Published quantum-dot experiment — first 600 records', loc='left', fontsize=10)
    axes[1].step(x, (ch1 > 0).astype(int), where='post', color='#e49a3e')
    axes[1].set_yticks([0, 1], ['no', 'yes'])
    axes[1].set_ylim(-.15, 1.15)
    axes[1].set_ylabel('Ch1 > 0?')
    axes[2].step(x, (four > 0).astype(int), where='post', color='#6b8191', linewidth=.7)
    axes[2].set_yticks([0, 1], ['no', 'yes'])
    axes[2].set_ylim(-.15, 1.15)
    axes[2].set_ylabel('Fourfold\ncount > 0?')
    axes[2].set_xlabel('Elapsed timestamp time (minutes)')
    for ax in axes:
        ax.grid(alpha=.15)
    fig.text(.5, -.035, 'Independent published data, not our measurement. Fourfold coincidences are not single-emitter clicks.\n'
             'Münzberg et al., Zenodo 10.5281/zenodo.6337697, CC BY 4.0.', ha='center', fontsize=9)
    fig.savefig(output, dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path, help='save a summary without overwriting an existing file')
    parser.add_argument('--figure', type=Path, help='save a plot without overwriting an existing file')
    args = parser.parse_args()
    for path in (args.json, args.figure):
        if path and path.exists():
            parser.error(f'output already exists: {path}')
    times, counts, digest = read_counts()
    result = assess(times, counts, digest)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    if args.figure:
        render(times, counts, result, args.figure)
    print('Measured, independently published data:', len(times), 'records; source checksum verified')
    print('Median timestamp spacing:', f"{result['record_timestamp_delta_seconds']['median']:.6f}", 's')
    for name in ('Ch1', 'Coin_1234'):
        x = result['channels'][name]
        print(name, 'positive:', x['number_positive'], '/', len(times),
              '; fraction:', f"{x['fraction_positive']:.6f}")
    print('No physical model was fitted; one-second count bins are not individual photon arrival times.')


if __name__ == '__main__':
    main()
