"""Portable adaptation of the root reviewer's independently written stdlib check.

Original .publication-audit/check_hom_independent.py SHA-256:
1b99f3114f4e4157227cd30c03c3dcd0f1b55d44d1aa7c841b704f7e8fefde22
No scientific-analysis imports. Adaptations: portable paths, CLI optional output,
and explicit comparisons to the canonical saved result. Extraction unchanged.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "reference_hom"


def check():
    manifest = json.loads((DATA/'provenance_manifest.json').read_text(encoding='utf-8'))
    period = 4e6/76.2  # picoseconds
    rows = []
    for entry in manifest['files']:
        file = DATA/entry['path']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == entry['sha256']
        with file.open(newline='') as stream:
            reader = csv.reader(stream)
            assert next(reader) == ['Time (ps)', 'Counts']
            pairs = [(int(float(t)), int(n)) for t,n in reader]
        numerator = 0.
        denominator = 0
        for k in [-2,-1,1,2]:
            nominal = k*period
            for t,n in pairs:
                if nominal-3000 <= t < nominal+3000:
                    numerator += (t-nominal)*n
                    denominator += n
        offset = 50*round(numerator/denominator/50)
        areas=[]
        centers=[]
        for k in [0,-2,-1,1,2]:
            center=50*round((k*period+offset)/50)
            bins=[n for t,n in pairs if center-2000 <= t < center+2000]
            assert len(bins)==80
            areas.append(sum(bins))
            centers.append(center)
        ratio=4*areas[0]/sum(areas[1:])
        rows.append({'file':entry['path'], 'delay_ns':entry['excitation_pulse_separation_ns'],
                     'polarization':entry['polarization'], 'offset_ps':offset,
                     'centers_ps':centers, 'counts':areas, 'normalized_central':ratio,
                     'raw_sha256':entry['sha256']})

    estimates=[]
    for delay in [13.1,26.2,39.4]:
        co=next(row for row in rows if row['delay_ns']==delay and row['polarization']=='co')
        cross=next(row for row in rows if row['delay_ns']==delay and row['polarization']=='cross')
        ratio=co['normalized_central']/cross['normalized_central']
        raw=1-ratio
        R=.514
        factor=(R*R+(1-R)**2)/(2*R*(1-R))
        corrected=(raw+.016)/.984*factor
        relative_variance=sum(1/r['counts'][0]+1/sum(r['counts'][1:]) for r in [co,cross])
        estimates.append({'delay_ns':delay,'raw_visibility':raw,'corrected_visibility':corrected,
                          'corrected_count_only_sd_delta':ratio*relative_variance**.5*factor/.984,
                          'co_only_corrected':(1-2*co['normalized_central']+.016)/.984*factor})
    saved = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
    for case, estimate in zip(saved['cases'], estimates):
        assert case['excitation_separation_ns'] == estimate['delay_ns']
        for key in ['raw_visibility', 'corrected_visibility']:
            assert abs(case['primary'][key] - estimate[key]) < 1e-14
        assert abs(case['primary']['co_only_corrected_visibility'] - estimate['co_only_corrected']) < 1e-14
        assert abs(case['primary']['count_only_sd'] / estimate['corrected_count_only_sd_delta'] - 1) < .01
        for pol in ['co', 'cross']:
            row = next(r for r in rows if r['delay_ns'] == estimate['delay_ns'] and r['polarization'] == pol)
            ex = case['extractions'][pol]
            assert abs(ex['registration_offset_ns'] * 1000 - row['offset_ps']) < 1e-8
            for j, k in enumerate([0, -2, -1, 1, 2]):
                assert abs(ex['peaks'][str(k)]['center_ns'] * 1000 - row['centers_ps'][j]) < 1e-8
                assert ex['peaks'][str(k)]['count'] == row['counts'][j]
    return {'scope': 'Independent stdlib primary extraction, no science-module import; adapted from root reviewer',
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'original_reviewer_source_sha256': '1b99f3114f4e4157227cd30c03c3dcd0f1b55d44d1aa7c841b704f7e8fefde22',
            'protocol_sha256': hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),
            'results_sha256': hashlib.sha256((HERE/'results.json').read_bytes()).hexdigest(),
            'all_primary_areas_centers_and_point_estimates_match': True,
            'count_only_monte_carlo_sd_within_1_percent_of_independent_delta_method': True,
            'acquisitions': rows, 'estimates': estimates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check()
    if args.output:
        if args.output.exists():
            raise SystemExit('Refusing to overwrite an independent receipt')
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('Independent stdlib check passed: 30 peak areas, 30 centers, all primary/alternative point estimates and counting uncertainty.')


if __name__ == '__main__':
    main()
