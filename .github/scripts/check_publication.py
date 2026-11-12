"""Check the public Git inventory without printing possible credential values.

This is a targeted guard, not a proof that arbitrary content is safe to publish.
Run after staging, or in a clean clone. No network or nonstandard package needed.
"""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOTS = {
    'results.csv', 'Qiskit_Fall_Fest_Judging_Rubric.xlsx', 'WORKSPACE_AUDIT.md',
    'relevantconversationswithai', 'finals-archive', '.finals-deck-stage', 'tmp',
}
FORBIDDEN_PARTS = {'.env', '.venv', 'venv', '__pycache__', 'node_modules', '.qiskit'}
TEXT_SUFFIXES = {'.py', '.js', '.mjs', '.cjs', '.json', '.md', '.txt', '.csv',
                 '.html', '.css', '.yml', '.yaml', '.toml', '.ipynb', '.log'}
SIGNATURES = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'OpenAI token': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'Google API key': re.compile(r'\bAIza[A-Za-z0-9_-]{30,}\b'),
}


def main():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True)
    names = [p.decode('utf-8') for p in result.stdout.split(b'\0') if p]
    if not names:
        raise SystemExit('No tracked files to inspect; stage the intended public files first.')
    errors = []
    total = 0
    for name in names:
        parts = PurePosixPath(name).parts
        path = ROOT / name
        if (parts[0] in PRIVATE_ROOTS or any(p in FORBIDDEN_PARTS for p in parts)
                or path.suffix.lower() in {'.zip', '.token', '.pem', '.key'}
                or path.name in {'qiskit-ibm.json', 'ibm-quantum.json'}):
            errors.append(f'Excluded/private artifact tracked: {name}')
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            errors.append(f'Unexpected public file type/path: {name}')
            continue
        size = path.stat().st_size
        total += size
        if size >= 50 * 1024 * 1024:
            errors.append(f'File exceeds the repository 50 MiB budget: {name}')
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {'LICENSE', '.gitignore', '.gitattributes'}:
            content = path.read_text(encoding='utf-8', errors='replace')
            for kind, pattern in SIGNATURES.items():
                for match in pattern.finditer(content):
                    line = content.count('\n', 0, match.start()) + 1
                    errors.append(f'Possible {kind}: {name}:{line} (value withheld)')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Public inventory: {len(names)} files, {total:,} bytes; no excluded paths, oversized files or known secret signatures found.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
