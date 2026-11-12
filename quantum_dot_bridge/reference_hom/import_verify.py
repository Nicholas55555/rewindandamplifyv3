"""Import and audit the six published Fig. 4 HOM histograms; never fit visibility.

Default: verify local files against the pinned inventory and saved manifest.
--download: fetch missing source files only, then verify them.
--write-manifest: create the provenance manifest, refusing to overwrite one.
Only the optional plotter requires third-party packages.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
RECORD_URL = 'https://zenodo.org/records/6337697'
API_URL = 'https://zenodo.org/api/records/6337697'
PAPER_URL = 'https://arxiv.org/html/2203.08682v1'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
SOURCE_README_MD5 = 'c96c377de1642b00591b717586874e08'
FILES = (
    ('HOM_QD5_resonant_photon1+2_17-39-23.csv', 'a0608db38ed887163fbd323ad4908233', '4a', 13.1, 'co'),
    ('HOM_QD5_resonant_photon1+2_dist_17-42-16.csv', '7f5ab09fcfd6cdf4bc092de1117e6834', '4a', 13.1, 'cross'),
    ('HOM_QD5_resonant_photon1+3_17-50-06.csv', '3f501c856a54ee304af00b27b250c93e', '4b', 26.2, 'co'),
    ('HOM_QD5_resonant_photon1+3_dist_17-52-41.csv', '3867559ab693c857fd0e9e2d0c3d969d', '4b', 26.2, 'cross'),
    ('HOM_QD5_resonant_photon1+4_17-57-10.csv', 'a67bd07f2f91e5a0e28a0b51b27470dc', '4c', 39.4, 'co'),
    ('HOM_QD5_resonant_photon1+4_dist_18-00-48.csv', '8393de1731b15906a3b59d68f2c93287', '4c', 39.4, 'cross'),
)
AUTHORS = (
    'Julian Münzberg', 'Franz Draxl', 'Saimon Filipe Covre da Silva', 'Yusuf Karli',
    'Santanu Manna', 'Armando Rastelli', 'Gregor Weihs', 'Robert Keil',
)


def digest(data: bytes, algorithm='sha256'):
    return hashlib.new(algorithm, data).hexdigest()


def read_histogram_bytes(data: bytes):
    """Preserve the reported axis; validate counts without normalization/rebinning."""
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''))
    if next(reader, None) != ['Time (ps)', 'Counts']:
        raise ValueError('Unexpected header or units')
    rows = list(reader)
    if len(rows) != 5000 or any(len(row) != 2 for row in rows):
        raise ValueError('Expected exactly 5000 two-column histogram bins')
    try:
        times = [int(row[0]) for row in rows]
        counts = [int(row[1]) for row in rows]
    except ValueError as exc:
        raise ValueError('The source grid and counts must be integers') from exc
    if times != list(range(-125000, 125000, 50)):
        raise ValueError('Unexpected timing grid: source axis must be retained')
    if any(value < 0 for value in counts):
        raise ValueError('Counts must be nonnegative')
    return times, counts


def read_histogram(path: Path, expected_md5=None):
    data = path.read_bytes()
    if expected_md5 is not None and digest(data, 'md5') != expected_md5:
        raise ValueError(f'MD5 mismatch: {path.name}')
    return read_histogram_bytes(data)


def fetch_missing(url, destination):
    """Never replace an existing source snapshot."""
    if destination.exists():
        return
    request = urllib.request.Request(url, headers={'User-Agent':'RewindAmplify-research-ingestion/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    destination.write_bytes(data)


def audit(folder=HERE, download=False):
    folder = Path(folder)
    if download:
        folder.mkdir(parents=True, exist_ok=True)
        fetch_missing(API_URL, folder/'zenodo_record.json')
    metadata_bytes = (folder/'zenodo_record.json').read_bytes()
    record = json.loads(metadata_bytes)
    if int(record['id']) != 6337697 or record['doi'] != '10.5281/zenodo.6337697':
        raise ValueError('Wrong Zenodo record')
    if record['metadata']['license']['id'] != 'cc-by-4.0':
        raise ValueError('Unexpected license; review before redistributing')
    inventory = {entry['key']:entry for entry in record['files']}
    rows = []
    axes = []
    for name, expected, figure, separation, polarization in FILES:
        entry = inventory[name]
        if entry['checksum'] != 'md5:'+expected:
            raise ValueError(f'Inventory differs from pinned source checksum: {name}')
        if download:
            fetch_missing(entry['links']['self'], folder/name)
        data = (folder/name).read_bytes()
        if len(data) != entry['size'] or digest(data,'md5') != expected:
            raise ValueError(f'Source byte count or MD5 mismatch: {name}')
        times, counts = read_histogram_bytes(data)
        axes.append(times)
        rows.append({
            'path':name, 'source_url':entry['links']['self'],
            'figure':figure, 'excitation_pulse_separation_ns':separation,
            'polarization':polarization, 'source_bytes':entry['size'],
            'zenodo_md5':expected, 'local_md5':digest(data,'md5'),
            'sha256':digest(data), 'md5_matches_zenodo':True,
            'shape':[len(times),2], 'source_header':['Time (ps)','Counts'],
            'axis_min_ps':times[0], 'axis_max_ps':times[-1], 'axis_step_ps':50,
            'count_min':min(counts), 'count_max':max(counts), 'count_sum':sum(counts),
            'zero_count_bins':sum(value==0 for value in counts),
            'counts_nonnegative_integers':True,
            'duration_seconds':None, 'duration_status':'not supplied in these CSV headers or mapping README',
            'transformations':'none; raw source bytes unchanged',
        })
    readme_entry = inventory['readme.md']
    if download:
        fetch_missing(readme_entry['links']['self'], folder/'source_readme.md')
    readme_bytes = (folder/'source_readme.md').read_bytes()
    if digest(readme_bytes,'md5') != SOURCE_README_MD5 or readme_entry['checksum'] != 'md5:'+SOURCE_README_MD5:
        raise ValueError('Source README checksum mismatch')
    if not all(axis == axes[0] for axis in axes):
        raise ValueError('Co/cross histogram axes do not match')
    return {
        'schema':'reference-hom-ingestion-v1',
        'scope':'External experimental histogram ingestion and compatibility audit; no visibility estimate or physical fit',
        'record_url':RECORD_URL, 'record_api_url':API_URL, 'dataset_doi':record['doi'],
        'dataset_title':record['metadata']['title'],
        'publication_date':record['metadata']['publication_date'],
        'source_authors':list(AUTHORS),
        'paper_url':PAPER_URL, 'paper_version':'arXiv:2203.08682v1',
        'license':{'id':'CC-BY-4.0','url':LICENSE_URL},
        'files':rows, 'all_axes_identical':True, 'all_checks_passed':True,
        'metadata_snapshot':{'path':'zenodo_record.json','sha256':digest(metadata_bytes),
                             'saved_utc':datetime.fromtimestamp((folder/'zenodo_record.json').stat().st_mtime,timezone.utc).isoformat()},
        'source_readme':{'path':'source_readme.md','source_key':'readme.md','bytes':len(readme_bytes),
                         'md5':digest(readme_bytes,'md5'),'sha256':digest(readme_bytes)},
        'paper_reported_corrected_visibility':[
            {'excitation_pulse_separation_ns':13.1,'value':.803,'reported_parenthetical_uncertainty':.005},
            {'excitation_pulse_separation_ns':26.2,'value':.826,'reported_parenthetical_uncertainty':.004},
            {'excitation_pulse_separation_ns':39.4,'value':.774,'reported_parenthetical_uncertainty':.004},
        ],
        'reported_values_note':'Transcribed from paper Sec. IV, not recomputed here; no monotonic trend inferred',
        'compatibility':{
            'appropriate_observable':'Co/cross coincidence-delay histograms for a two-photon interference measurement model',
            'not_available':'Ordered per-shot photon records or underlying source-state trajectories',
            'normalization_reproduced':False,
            'missing_for_visibility_reproduction':['verified per-run duration/relative normalization','central and reference peak integration conventions','background treatment','uncertainty propagation and calibration association'],
            'paper_corrections':'Sec. IV Eq. 4 uses beam-splitter R=.514(.007), T=1-R and g2(0)=.016(.001); this audit does not reapply them',
            'team_data':False, 'team_fit':False, 'lithography_validation':False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    result = audit(download=args.download)
    manifest = HERE/'provenance_manifest.json'
    if args.write_manifest:
        if manifest.exists():
            raise FileExistsError('Refusing to replace the saved provenance manifest')
        result['verified_utc'] = datetime.now(timezone.utc).isoformat()
        result['audit_source_sha256'] = digest(Path(__file__).read_bytes())
        manifest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    else:
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        # File mtimes change during transport; hashes identify the source snapshot.
        result['metadata_snapshot']['saved_utc'] = saved['metadata_snapshot']['saved_utc']
        for key,value in result.items():
            if saved[key] != value:
                raise ValueError(f'Saved manifest mismatch: {key}')
        if saved['audit_source_sha256'] != digest(Path(__file__).read_bytes()):
            raise ValueError('Audit source differs from the recorded version')
    print(json.dumps({'all_checks_passed':True,'histograms':len(result['files']),
                      'rows_each':5000,'axis_step_ps':50,'visibility_recomputed':False}))


if __name__=='__main__':
    main()
