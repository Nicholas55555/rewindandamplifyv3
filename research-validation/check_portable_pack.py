"""Check the delivered ZIP from an isolated temporary extraction.

Runs only the standard-library handoff checks; it does not run cloud jobs.
"""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT / 'Rewind_Amplify_Finals_Visual_Pack.zip'
    temp_parent = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix='rewind_portable_', dir=temp_parent) as directory:
        target = Path(directory).resolve()
        # Check the exact extraction/cleanup directory stays inside the intended
        # temporary directory before populating it. TemporaryDirectory owns it.
        assert target.parent == temp_parent and target.name.startswith('rewind_portable_')
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None, 'Corrupt ZIP member'
            members = bundle.namelist()
            assert len(members) == len(set(members)), 'Duplicate ZIP member'
            for name in members:
                resolved = (target / name).resolve()
                assert resolved.is_relative_to(target), f'Unsafe member: {name}'
            hashes = bundle.read('SHA256SUMS.txt').decode('utf-8').splitlines()
            for line in hashes:
                digest, name = line.split('  ', 1)
                assert hashlib.sha256(bundle.read(name)).hexdigest() == digest, name
            bundle.extractall(target)
        completed = subprocess.run([sys.executable, str(target / 'check_finals.py')],
                                   cwd=target, capture_output=True, text=True)
        if completed.returncode:
            raise RuntimeError(completed.stdout + completed.stderr)
        print(completed.stdout.strip())
        print(f'Portable archive passed: {len(hashes)} source hashes and checks from an isolated extraction.')


if __name__ == '__main__':
    main()
