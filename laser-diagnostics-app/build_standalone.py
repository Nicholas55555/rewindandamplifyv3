"""Build/check the single-file v2 demo using only the Python standard library.

The folder app is the source. All its scripts, styles, videos and evidence are
embedded unchanged; the portable edition saves evidence links as named files.
No scientific computation or IBM access is performed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = ROOT / 'Rewind_Amplify_v2_Demo.html'
MANIFEST = HERE / 'standalone_manifest.json'
MIMES = {'.mp4': 'video/mp4', '.png': 'image/png', '.json': 'application/json',
         '.md': 'text/plain;charset=utf-8', '.csv': 'text/csv;charset=utf-8',
         '.txt': 'text/plain;charset=utf-8', '.svg': 'image/svg+xml'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> tuple[bytes, bytes]:
    sources = {}

    def read(path: Path) -> bytes:
        assert path.resolve().is_relative_to(HERE), path
        data = path.read_bytes()
        sources[path.relative_to(ROOT).as_posix()] = sha(data)
        return data

    def text(path: Path) -> str:
        return read(path).decode('utf-8').replace('\r\n', '\n')

    files, blobs = {}, {}
    paths = [HERE / 'README.md']
    paths += sorted((HERE / 'evidence').rglob('*'))
    paths += sorted((HERE / 'assets').rglob('*'))
    for path in paths:
        if not path.is_file():
            continue
        data = read(path)
        digest = sha(data)
        files[path.relative_to(HERE).as_posix()] = {
            'filename': path.name, 'sha256': digest, 'bytes': len(data),
            'mime': MIMES.get(path.suffix, 'application/octet-stream'),
        }
        blobs[digest] = base64.b64encode(data).decode('ascii')

    html = text(HERE / 'index.html')
    css = text(HERE / 'styles.css')
    assert '</style' not in css.lower()
    assert all(url.strip(' \"\'').startswith('#')
               for url in re.findall(r'url\s*\((.*?)\)', css)), 'External CSS asset requires embedding'
    html, count = re.subn(r'<link rel="stylesheet" href="styles.css">',
                         lambda _: '<style>\n' + css + '\n</style>', html)
    assert count == 1
    scripts = []

    def inline(match):
        name = match.group(1)
        scripts.append(name)
        source = text(HERE / name)
        # Prevent a JS string/comment containing an HTML closing tag from
        # prematurely terminating the inline script element.
        source = re.sub(r'</script', r'<\\/script', source, flags=re.I)
        return f'<script data-source="{name}">\n{source}\n</script>'

    html = re.sub(r'<script src="([^"]+)"></script>', inline, html)
    assert len(scripts) == 8

    def media(match):
        attr, name = match.groups()
        entry = files[name]
        return f'{attr}="data:{entry["mime"]};base64,{blobs[entry["sha256"]]}"'

    html = re.sub(r'(poster|src)="(assets/[^"]+)"', media, html)
    html = html.replace('<title>Rewind & Amplify · Quantum histories lab</title>',
                        '<title>Rewind & Amplify V2 · Portable demo</title>')
    notice = ('<p class="caption" style="max-width:1370px;margin:16px auto;padding:0 24px">'
              '<strong>V2 · Single-file offline demo.</strong> '
              'Evidence links save embedded files. External citations and IBM portal links need internet. '
              'All interactive results and both videos work offline.</p>\n')
    registry = json.dumps({'files': files, 'blobs': blobs}, separators=(',', ':'), sort_keys=True)
    runtime = text(HERE / 'portable.js')
    read(Path(__file__))
    tail = (notice + '<script id="portable-files" type="application/json">' + registry
            + '</script>\n<script data-source="portable.js">\n' + runtime + '\n</script>\n')
    assert html.count('</body>') == 1
    html = html.replace('</body>', tail + '</body>')
    output = html.encode('utf-8')
    assert len(output) < 50 * 1024 * 1024, 'Portable HTML exceeds repository file budget'
    manifest = {
        'schema': 1, 'output': OUTPUT.name, 'sha256': sha(output), 'bytes': len(output),
        'embedded_files': len(files), 'unique_file_blobs': len(blobs),
        'embedded_bytes_before_deduplication': sum(f['bytes'] for f in files.values()),
        'scripts_in_order': scripts, 'source_sha256': dict(sorted(sources.items())),
        'runtime_network_dependencies': 0,
        'evidence_access': 'Byte-exact embedded downloads with original filenames; external citations stay online.',
    }
    return output, (json.dumps(manifest, indent=2) + '\n').encode('utf-8')


class Resources(HTMLParser):
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for attr in ('src', 'poster'):
            if attr in a:
                assert a[attr].startswith('data:'), (tag, attr)
        assert not (tag == 'link' and a.get('rel') == 'stylesheet')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify the checked-in export without rewriting files')
    args = parser.parse_args()
    output, manifest = build()
    Resources().feed(output.decode('utf-8'))
    if args.check:
        assert OUTPUT.read_bytes() == output, 'Stale portable HTML: run build_standalone.py'
        assert MANIFEST.read_bytes() == manifest, 'Stale portable manifest: run build_standalone.py'
    else:
        OUTPUT.write_bytes(output)
        MANIFEST.write_bytes(manifest)
    m = json.loads(manifest)
    print(json.dumps({'status': 'verified' if args.check else 'built', 'file': m['output'],
                      'bytes': m['bytes'], 'embedded_files': m['embedded_files'], 'sha256': m['sha256']}))


if __name__ == '__main__':
    main()
