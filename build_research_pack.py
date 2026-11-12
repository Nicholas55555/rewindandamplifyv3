"""Create a separate portable research snapshot after the completion audit.

Keeps the frozen finals archive untouched. Archived failed/old full-grid QPY
binaries are excluded; their source, hashes and bounded-attempt reports remain.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile
from verify_research_pack import MANIFEST, verify, digest_stream

ROOT = Path(__file__).resolve().parent
TREES = ('finals-lithography', 'qrsm_photon_poc', 'laser_sensor_viability',
         'quantum_lithography_poc')
TOP = ('RESEARCH_RESULTS.md', 'RESEARCH_CONTINUATION_PLAN.md',
       'LASER_DIAGNOSTICS_ROADMAP.md', 'QUANTUM_PHOTOLITHOGRAPHY_ROADMAP.md',
       'LASER_SENSOR_RESEARCH_PLAN.md', 'build_research_pack.py',
       'verify_research_pack.py', 'research-validation/research_requirements.txt',
       'research-validation/collect_research_checks.py',
       'research-validation/check_research_delivery.py',
       'research-validation/completion_audit.json',
       'research-validation/research_checks.json')


def main():
    status = json.loads((ROOT / 'research-validation/completion_audit.json').read_text(encoding='utf-8'))
    if status['bounded_local_program_status'] != 'complete':
        raise RuntimeError('The research completion audit is not complete')
    candidates = {ROOT / name for name in TOP}
    exclusions = []
    for tree in TREES:
        for path in (ROOT / tree).rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            reason = None
            if any(p in ('__pycache__', '.pytest_cache', '.venv', 'node_modules') for p in rel.parts):
                reason = 'regenerable cache/environment'
            elif path.suffix in ('.partial', '.pyc', '.tmp'):
                reason = 'partial or regenerable output'
            elif 'full_spatial_circuit' in rel.parts and 'archive' in rel.parts and path.suffix == '.qpy':
                reason = 'superseded/failed circuit binary; source and attempt reports retained'
            if reason:
                exclusions.append({'path': rel.as_posix(), 'reason': reason})
            else:
                candidates.add(path)
    entries = []
    for path in sorted(candidates):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f'Missing or unexpected file: {path}')
        with path.open('rb') as handle:
            size, digest = digest_stream(handle)
        entries.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': size, 'sha256': digest})
    manifest = {
        'schema': 'rewind-research-snapshot-v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'entrypoint': 'RESEARCH_RESULTS.md',
        'scope': 'Local numerical research, sources, original dependencies and provenance; separate from finals delivery.',
        'excluded_files': exclusions,
        'files': entries,
    }
    encoded = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    destination = ROOT / 'Rewind_Amplify_Research_Followups.zip'
    staging = destination.with_suffix('.zip.staging')
    with zipfile.ZipFile(staging, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in entries:
            archive.write(ROOT / item['path'], item['path'])
        archive.writestr(MANIFEST, encoded)
    receipt = verify(staging)
    staging.replace(destination)
    (ROOT / MANIFEST).write_text(encoded, encoding='utf-8')
    receipt.update({'archive': destination.name, 'archive_bytes': destination.stat().st_size,
                    'archive_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                    'manifest_sha256': hashlib.sha256(encoded.encode('utf-8')).hexdigest(),
                    'exclusions': len(exclusions),
                    'created_utc': datetime.now(timezone.utc).isoformat()})
    (ROOT / 'research-validation/research_pack_validation.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
