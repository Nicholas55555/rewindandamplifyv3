"""Build or check Rewind_Amplify_Lab.html: the whole Lab as one offline file.

The folder app in lab/ is the source. This inlines its stylesheet and three scripts unchanged, so the single
file can be emailed, opened from a USB stick, or dropped on a presentation laptop with no server and no network.

    python lab/build.py            # rewrite Rewind_Amplify_Lab.html
    python lab/build.py --check    # fail if the checked-in file is stale

Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = ROOT / "Rewind_Amplify_Lab.html"
REPO = "https://github.com/Nicholas55555/rewindandamplifyv3"
SCRIPTS = ["engine.js", "data.js", "app.js"]
# A single file travels alone, so links that lean on the folder layout point at the repository instead.
PORTABLE_LINKS = {
    'href="../laser-diagnostics-app/index.html"': f'href="{REPO}#research-explorer"',
}


def read(name: str) -> str:
    return (HERE / name).read_bytes().decode("utf-8").replace("\r\n", "\n")


def build() -> bytes:
    html = read("index.html")
    css = read("styles.css")
    assert "</style" not in css.lower() and "url(" not in css.lower(), "the stylesheet must not pull in other files"
    html, count = re.subn(r'<link rel="stylesheet" href="styles.css">', lambda _: "<style>\n" + css + "</style>", html)
    assert count == 1
    found = []

    def inline(match: re.Match) -> str:
        name = match.group(1)
        found.append(name)
        source = re.sub(r"</script", r"<\\/script", read(name), flags=re.I)
        return f'<script data-source="lab/{name}">\n{source}</script>'

    html = re.sub(r'<script src="([^"]+)"></script>', inline, html)
    assert found == SCRIPTS, found
    for old, new in PORTABLE_LINKS.items():
        assert html.count(old) == 1, old
        html = html.replace(old, new)
    stamp = hashlib.sha256("".join(read(n) for n in ["index.html", "styles.css", *SCRIPTS]).encode("utf-8")).hexdigest()[:12]
    html = html.replace("<title>Rewind & Amplify · Lab</title>",
                        f'<title>Rewind & Amplify · Lab</title>\n<meta name="generator" content="lab/build.py from sources {stamp}">')
    return html.encode("utf-8")


class NoExternalAssets(HTMLParser):
    """The single file must not load anything: no script, stylesheet, image or font from elsewhere."""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        assert not (tag == "script" and "src" in a), a
        assert not (tag == "link" and a.get("rel") in ("stylesheet", "preload", "icon")), a
        assert tag not in ("img", "iframe", "video", "audio", "source"), tag


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the checked-in file without rewriting it")
    args = parser.parse_args()
    output = build()
    NoExternalAssets().feed(output.decode("utf-8"))
    if args.check:
        assert OUTPUT.read_bytes() == output, "Stale Rewind_Amplify_Lab.html: run python lab/build.py"
    else:
        OUTPUT.write_bytes(output)
    print(json.dumps({"status": "verified" if args.check else "built", "file": OUTPUT.name, "bytes": len(output),
                      "sha256": hashlib.sha256(output).hexdigest()}))


if __name__ == "__main__":
    main()
