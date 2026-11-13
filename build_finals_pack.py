"""Build a local, portable presentation and reproducibility bundle.

The bundle copies project files into a ZIP; it does not send or publish them.
It excludes large original research archives/PDFs, generated caches, and old
presentation drafts. The workspace retains all original files. Rebuild only
after the final deck and handoff notes have been reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
DOCS = ["START_HERE_FINALS.md", "check_finals.py", "FINALS_PLAN.md", "FINALS_TALK.md", "FINALS_QA.md", "FINALS_EVIDENCE.md",
        "VIABILITY_FINDINGS.md", "WORKSPACE_AUDIT.md", "QUANTUM_PHOTOLITHOGRAPHY_ROADMAP.md", "LASER_DIAGNOSTICS_ROADMAP.md",
        "LASER_SENSOR_RESEARCH_PLAN.md", "FINALS_RUBRIC.md", "Qiskit_Fall_Fest_Judging_Rubric.xlsx", "results.csv", "build_finals_pack.py",
        "RESEARCH_RESULTS.md", "RESEARCH_CURRENT.md", "RESEARCH_CONTINUATION_PLAN.md", "verify_research_pack.py", "build_research_pack.py",
        "reproduce.py"]
DECKS = ["finals-deck/Rewind_Amplify_Finals_V3.pptx", "finals-deck/Rewind_Amplify_Finals_V3.pdf",
         "finals-deck/Presenter_Guide_V3.md", "finals-deck/v3_manifest.json", "finals-deck/v3_notes.json", "finals-deck/README.md",
         "finals-deck/main-slides.png", "finals-deck/backup-slides.png", "finals-deck/deck_kit.py", "finals-deck/build_v3_deck.py", "finals-deck/v3_backups.py",
         "finals-deck/finish_v3_deck.py", "finals-deck/finish_v3_deck.ps1",
         ".finals-deck-build/visual_build.mjs", ".finals-deck-build/visual_render_final.mjs",
         ".finals-deck-build/visual_finish.py", ".finals-deck-build/visual_notes.json"]
TREES = ["finals-lithography", "photon_reference", "qrsm_photon_poc", "rewindandamplify-main", "external_data", "quantum_lithography_poc", "laser_sensor_poc",
         "laser_sensor_viability", "laser-diagnostics-app", "animations", "research-validation", "finals-deck/assets", "finals-deck/v2",
         "quantum_dot_bridge", "hardware_campaign", "applied", "lab", "media", "docs"]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"}
PRIVATE_DOCUMENTS = {"results.csv", "Qiskit_Fall_Fest_Judging_Rubric.xlsx", "WORKSPACE_AUDIT.md"}
PUBLIC_DOCUMENTS = ["README.md", "Rewind_Amplify_Lab.html", "Rewind_Amplify_Research_Explorer.html", "index.html", "LICENSE",
                    "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md",
                    "docs/REPOSITORY_GUIDE.md", "requirements-dev.txt", "requirements-tools.txt",
                    "RESEARCH_ARCHIVE_MANIFEST.json", ".gitignore", ".gitattributes", ".nojekyll", ".github/workflows/ci.yml",
                    ".github/scripts/run_tests.py", ".github/scripts/check_publication.py"]
INTRO = """# Rewind & Amplify — portable finals pack

1. Open `finals-deck/Rewind_Amplify_Finals_V3.pptx` for thirteen main slides followed by 28 backups in the same style. It holds two embedded videos. The PDF is a static fallback without speaker notes or video. Use Presenter_Guide_V3.md for the 9:25 planned talk.
2. Open `Rewind_Amplify_Lab.html` directly: this single file is the live demo and needs nothing else. Its last three tabs animate the follow-up research on photon sources, laser monitoring and chipmaking. For the follow-up studies, open `Rewind_Amplify_Research_Explorer.html`, which includes its videos and downloadable evidence. Or open `laser-diagnostics-app/index.html` with its folder intact. Choose Focus view for the original QRSM demo. Current research contains the new comparisons; Earlier sensor study preserves the known-time experiment. Both work offline.
3. The two 12-second MP4 videos and PNG fallbacks are in `animations/`. They are conceptual illustrations from the earlier optical/sensing extensions, not current performance evidence. The app has playback controls.
4. Read `START_HERE_FINALS.md`, `FINALS_RUBRIC.md`, `FINALS_EVIDENCE.md`, and `RESEARCH_CURRENT.md`. The earlier `RESEARCH_RESULTS.md` remains the frozen research snapshot. Run `python check_finals.py` for package checks. Rehearse on the presentation computer.

The original main-project source and archived results are in `rewindandamplify-main/`.
This pack does not include the large original research-document ZIPs and PDFs or
old presentation drafts. Those remain in the source workspace. Third-party
photon-correlation data, attribution and license are in `photon_reference/`;
independent integrated photon counts and their license are in `external_data/`.
The later `quantum_dot_bridge/` study separates an illustrative coherence model
from external GaAs HOM measurements in `reference_hom/` and our conditional
reanalysis in `hom_analysis/`. Its README explains semiconductor photon quality,
collection cost, attribution and the limits of microscopic interpretation.
The subsequent `qrsm_hom_followup/` implements a sequential emitter/environment
and joint-photon instrument, with held-out synthetic diagnostic tests and
classical controls. `hardware_campaign/` records real IBM execution of feasible
gate-model circuits, raw counts and a family-by-family coverage ledger. Digital
emulation on a superconducting processor is distinct from optical or wafer
validation; read the recorded negative results and conditional-answer errors.
The current research includes unknown-onset frequency sensing, a negative
amplitude-diagnosis result, a prior-only control, conditional phase inspection,
detector-aware inference and full spatial circuit construction. The source
models remain synthetic; the separately attributed GaAs measurements come from
the cited authors. No industrial validation or quantum advantage is claimed.
`applied/` asks the follow-up studies' shared question of the main project's own
machine on IBM hardware; one of its two runs was predicted before it ran.
Canonical full-grid QPYs are included as construction artifacts; do not attempt
a desktop statevector simulation of their 389 qubits. Failed and superseded QPY
binaries are omitted, while bounded-attempt reports remain.
No files are sent or published when creating this archive.
"""


def sources(public: bool = False) -> list[Path]:
    names = [name for name in (*DOCS, *DECKS) if not public or name not in PRIVATE_DOCUMENTS]
    if public:
        names.extend(PUBLIC_DOCUMENTS)
        # Retain every file required by the frozen research snapshot, including
        # small generated fixtures omitted from the original finals-only pack.
        research = json.loads((ROOT/'RESEARCH_ARCHIVE_MANIFEST.json').read_text(encoding='utf-8'))
        names.extend(item['path'] for item in research['files'])
    selected = [ROOT / name for name in names]
    # the archived V2 deck's own receipts, whose paths were written relative to finals-deck/
    manifest = json.loads((ROOT/'finals-deck/v2/visual_manifest.json').read_text(encoding='utf-8'))
    for key in ('validation_report', 'visual_review_report'):
        candidate = (ROOT/'finals-deck'/manifest[key]).resolve()
        if not candidate.is_relative_to(ROOT):
            raise ValueError(f'Deck manifest path leaves workspace: {key}')
        selected.append(candidate)
    for name in TREES:
        directory = ROOT / name
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        for path in directory.rglob('*'):
            rel_parts = path.relative_to(ROOT).parts
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in rel_parts):
                continue
            if path.suffix in {'.partial', '.tmp', '.pyc'}:
                continue
            if 'full_spatial_circuit' in rel_parts and 'archive' in rel_parts and path.suffix == '.qpy':
                continue
            # Avoid duplicating full generated photon data already included at
            # the top level; keep the small checked dilation result.
            if name == 'qrsm_photon_poc' and 'generated' in rel_parts:
                if path.name not in {'dilation_feasibility_normalized.json',
                                      'dilation_synthesis_coarse_validated.json',
                                      'dilation_synthesis_8q_validated.json',
                                      'two_bin_double.json',
                                      'two_bin_summary.png'}:
                    continue
            selected.append(path)
    if public and (ROOT/'.git').exists():
        # A developer workspace can contain private/untracked files inside an
        # otherwise public tree. Only package the reviewed Git inventory.
        inventory = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT,
                                   check=True, capture_output=True)
        tracked = {name.decode('utf-8') for name in inventory.stdout.split(b'\0') if name}
        if not tracked:
            raise ValueError('Stage the intended public repository files before building its public pack')
        missing = set(names) - tracked
        if missing:
            raise ValueError('Required public sources are not tracked: ' + ', '.join(sorted(missing)))
        selected = [path for path in selected if path.relative_to(ROOT).as_posix() in tracked]
    for path in selected:
        if not path.is_file():
            raise FileNotFoundError(path)
    return sorted(set(selected))


def build(output: Path, replace: bool = False, public: bool = False) -> tuple[int, int]:
    if output.exists() and not replace:
        raise FileExistsError(f'Output already exists: {output}')
    staged = output.with_name(output.name + '.building')
    if staged.exists():
        raise FileExistsError(f'Staging file already exists: {staged}')
    files = sources(public=public)
    expected = {}
    for path in files:
        name = path.relative_to(ROOT).as_posix()
        expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = ''.join(f'{digest}  {name}\n' for name, digest in sorted(expected.items()))
    with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        intro = INTRO
        if public:
            intro = intro.replace('python check_finals.py', 'python check_finals.py --public')
            intro += ('\nThis is the public repository edition. Other teams\' judging scores, the supplied '
                      'rubric workbook, private workspace audit, conversation exports and original '
                      'document archives are excluded. FINALS_RUBRIC.md describes the criteria. '
                      'The previous local finals ZIP is a different artifact and must not be uploaded.\n')
        z.writestr('README_FIRST.md', intro)
        for path in files:
            z.write(path, path.relative_to(ROOT).as_posix())
        z.writestr('SHA256SUMS.txt', manifest)
    with zipfile.ZipFile(staged) as z:
        if z.testzip() is not None:
            raise RuntimeError('Archive integrity check failed')
        for name, digest in expected.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise RuntimeError(f'Archive hash mismatch: {name}')
    staged.replace(output)
    return len(files), output.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--replace', action='store_true', help='replace an existing pack only after the new archive verifies')
    parser.add_argument('--public', action='store_true', help='build the public edition without private judging/source documents')
    args = parser.parse_args()
    output = args.output or ROOT/('Rewind_Amplify_v3_Public_Pack.zip' if args.public else 'Rewind_Amplify_Finals_V3_Pack.zip')
    count, size = build(output, replace=args.replace, public=args.public)
    print(f'Verified {count} project files in {output} ({size:,} bytes).')


if __name__ == '__main__':
    main()
