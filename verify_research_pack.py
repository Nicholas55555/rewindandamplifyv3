"""Check the research archive's inventory and SHA-256 hashes; no science rerun.

Usage: python verify_research_pack.py [extracted-directory-or-zip]
Only the Python standard library is required. Extra files in an extracted
directory are ignored; every listed archive file must exist and match.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import stat
import zipfile

MANIFEST = 'RESEARCH_ARCHIVE_MANIFEST.json'


def safe_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or any(
            part in ('', '.', '..') for part in name.split('/')):
        raise ValueError(f'Unsafe archive path: {name!r}')
    return p


def digest_stream(handle):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: handle.read(1024 * 1024), b''):
        digest.update(block)
        size += len(block)
    return size, digest.hexdigest()


def verify(target):
    target = Path(target).resolve()
    if target.is_file():
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
            if len(names) != len({n.casefold() for n in names}):
                raise ValueError('Duplicate or case-colliding archive members')
            for info in archive.infolist():
                safe_name(info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError('Archive contains a symbolic link')
            manifest = json.loads(archive.read(MANIFEST))
            expected = {item['path'] for item in manifest['files']}
            if set(names) != expected | {MANIFEST}:
                raise ValueError('Archive inventory differs from manifest')
            for item in manifest['files']:
                safe_name(item['path'])
                with archive.open(item['path']) as handle:
                    size, digest = digest_stream(handle)
                if size != item['bytes'] or digest != item['sha256']:
                    raise ValueError(f"Mismatch: {item['path']}")
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC failure')
    else:
        manifest = json.loads((target / MANIFEST).read_text(encoding='utf-8'))
        for item in manifest['files']:
            parts = safe_name(item['path']).parts
            path = target.joinpath(*parts)
            current = target
            for part in parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f'Symbolic link in extracted path: {current}')
            if not path.resolve().is_relative_to(target):
                raise ValueError('Extracted path leaves root')
            with path.open('rb') as handle:
                size, digest = digest_stream(handle)
            if size != item['bytes'] or digest != item['sha256']:
                raise ValueError(f"Mismatch: {item['path']}")
    paths = [item['path'] for item in manifest['files']]
    if len(paths) != len({p.casefold() for p in paths}):
        raise ValueError('Manifest lists duplicate paths')
    return {'all_hashes_match': True, 'files_verified': len(paths),
            'total_uncompressed_bytes': sum(x['bytes'] for x in manifest['files']),
            'scope': 'Artifact integrity only; see study receipts for numerical validation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', type=Path, default=Path(__file__).parent)
    print(json.dumps(verify(parser.parse_args().target), indent=2))
