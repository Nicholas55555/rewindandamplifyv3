"""Check the finals handoff using only the Python standard library.

This verifies that the files a presenter needs are present, that the V3 deck is the one its manifest describes
(slide and note counts, the 9:20 talk plan, real embedded videos, hashes of the deck and of every saved result a
slide quotes), that the archived V2 deck is intact, and that the offline demos load only local assets.

It does not replace a rehearsal on the presentation computer, the quantum-software tests, or reading the event's
submission rules.

    python check_finals.py --public      # the public repository
    python check_finals.py               # also expects the private rubric workbook
"""
from __future__ import annotations

from html.parser import HTMLParser
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DECK = ROOT / 'finals-deck'
V2_DECK = DECK / 'v2'
MAIN_SLIDES = 13
TALK_SECONDS = 560
REQUIRED = [
    'README.md', 'START_HERE_FINALS.md', 'FINALS_TALK.md', 'FINALS_QA.md', 'FINALS_EVIDENCE.md', 'FINALS_RUBRIC.md',
    'Qiskit_Fall_Fest_Judging_Rubric.xlsx',
    # the V3 presentation
    'finals-deck/Rewind_Amplify_Finals_V3.pptx', 'finals-deck/Rewind_Amplify_Finals_V3.pdf',
    'finals-deck/v3_manifest.json', 'finals-deck/v3_notes.json', 'finals-deck/Presenter_Guide_V3.md',
    'media/lab-tour.mp4', 'media/cinematic-45s.mp4',
    # the Lab, and the one-command reproduction
    'Rewind_Amplify_Lab.html', 'index.html', 'lab/index.html', 'lab/engine.js', 'lab/data.js', 'lab/app.js', 'lab/styles.css',
    'reproduce.py', 'hardware_campaign/noise_model/results.json',
    # the archived V2 deck and the research explorer
    'finals-deck/v2/Rewind_Amplify_Finals_Visual.pptx', 'finals-deck/v2/Rewind_Amplify_Finals_Visual.pdf',
    'finals-deck/v2/visual_manifest.json', 'finals-deck/v2/Visual_Presenter_Guide.md',
    'laser-diagnostics-app/index.html', 'laser-diagnostics-app/data.js',
    'laser-diagnostics-app/research-data.js',
    'RESEARCH_RESULTS.md',
    'laser_sensor_viability/followup/main/results.json',
    'qrsm_photon_poc/drive_diagnostics_followup/main/results.json',
    'qrsm_photon_poc/drive_diagnostics_followup/main/prior_only_estimation_control.json',
    'quantum_lithography_poc/phase_inspection_followup/results.json',
    'finals-lithography/full_spatial_circuit/results.json',
    'laser_sensor_viability/results.json', 'laser_sensor_viability/README.md',
    'animations/laser-diagnostic-lenses.mp4', 'animations/rewind-amplify.mp4',
    'research-validation/hardware_verification.json',
    'research-validation/original_after_click_verification.json',
    'research-validation/sensor_physics_verification.json',
    'finals-lithography/index.html', 'finals-lithography/spatial_demo.png',
    'finals-lithography/dose_sweep.png', 'finals-lithography/viability_cost_tradeoff.png',
    'photon_reference/README.md',
]
DRAWING = '{http://schemas.openxmlformats.org/drawingml/2006/main}t'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def squeeze(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def clock(stamp: str) -> int:
    return sum(int(value) * unit for value, unit in zip(stamp.split(':'), (60, 1)))


class LocalAssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        # External <a> links are optional background, not load-time dependencies.
        if tag in ('img', 'script', 'iframe') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel', '').lower() == 'stylesheet' and attrs.get('href'):
            self.assets.append(attrs['href'])


def check_v3_deck(errors: list) -> None:
    manifest_path = DECK / 'v3_manifest.json'
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    script = json.loads((DECK / 'v3_notes.json').read_text(encoding='utf-8'))
    pptx = DECK / manifest['deck']
    total = manifest.get('total_slide_count')
    try:
        with zipfile.ZipFile(pptx) as z:
            bad = z.testzip()
            if bad:
                errors.append(f'Corrupt presentation member: {bad}')
            names = z.namelist()
            if len(names) != len(set(names)):
                errors.append('The presentation package has duplicate part names')
            slides = [n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
            notes = [n for n in names if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)]
            if len(slides) != total or len(notes) != total or manifest.get('main_slide_count') != MAIN_SLIDES:
                errors.append(f'Expected {MAIN_SLIDES} main slides and {total} slides and notes; found {len(slides)} and {len(notes)}')
            else:
                print(f'Presentation: {len(slides)} slides and note pages, package intact')
            # the speaker script inside the deck is the script in v3_notes.json
            if len(script['main']) != MAIN_SLIDES:
                errors.append('The speaker script does not have one entry per main slide')
            for i, entry in enumerate(script['main'], 1):
                name = f'ppt/notesSlides/notesSlide{i}.xml'
                if name not in names:
                    errors.append(f'Slide {i} has no notes page')
                    continue
                text = ' '.join(t.text or '' for t in ET.fromstring(z.read(name)).iter(DRAWING))
                if squeeze(entry['text']) not in squeeze(text):
                    errors.append(f'Embedded speaker script differs on slide {i}')
            # the talk plan is contiguous and ends at 9:20
            end = 0
            for entry in script['main']:
                start, stop = (clock(t) for t in entry['time'].split('–'))
                if start != end:
                    errors.append('Main talk timeline has a gap or overlap')
                end = stop
            if end != TALK_SECONDS or manifest.get('talk_timing_seconds') != TALK_SECONDS:
                errors.append('Expected the 9:20 main talk plan')
            # videos must be playable media, not pictures of videos
            videos = [n for n in names if n.startswith('ppt/media/') and n.lower().endswith('.mp4')]
            video_slides = []
            for i in range(1, len(slides) + 1):
                xml = z.read(f'ppt/slides/slide{i}.xml').decode('utf-8')
                if 'videoFile' in xml:
                    if 'p14:media' not in xml or '<p:timing' not in xml:
                        errors.append(f'Slide {i} has a video without its media or timing node')
                    rels = z.read(f'ppt/slides/_rels/slide{i}.xml.rels').decode('utf-8')
                    if 'relationships/video' not in rels or 'relationships/media' not in rels:
                        errors.append(f'Slide {i} has a video without its relationships')
                    video_slides.append(i)
            if 'video/mp4' not in z.read('[Content_Types].xml').decode('utf-8'):
                errors.append('The presentation does not declare MP4 content')
            expected = manifest.get('embedded_videos', {})
            if len(videos) != expected.get('count') or video_slides != expected.get('slides') or len(videos) < 2:
                errors.append(f'Expected embedded videos on slides {expected.get("slides")}; found {video_slides}')
            else:
                print(f'Presentation: {len(videos)} embedded videos, on slides {video_slides}')
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        errors.append(f'Could not read presentation: {exc}')
    pdf = DECK / manifest['pdf']
    if pdf.is_file() and pdf.read_bytes()[:5] != b'%PDF-':
        errors.append('PDF fallback does not have a PDF header')
    for filename, expected_hash in manifest.get('sha256', {}).items():
        artifact = DECK / filename
        if not artifact.is_file() or sha(artifact) != expected_hash:
            errors.append(f'Presentation manifest mismatch: {filename}. Rebuild the deck (finals-deck/README.md).')
    if not manifest.get('source_sha256'):
        errors.append('The presentation manifest is missing its evidence hash map')
    for filename, expected_hash in manifest.get('source_sha256', {}).items():
        source = ROOT / filename
        if not source.is_file() or sha(source) != expected_hash:
            errors.append(f'A result quoted on a slide changed since the deck was built: {filename}')
    report = manifest.get('powerpoint_check', {})
    if report.get('opened_without_repair') is not True or report.get('slides') != total:
        errors.append('The deck has no record of opening cleanly in PowerPoint: run finals-deck/finish_v3_deck.ps1')


def check_v2_deck(errors: list) -> None:
    """The V2 deck is kept as it was published. Its manifest still pins the deck and the research it quoted."""
    manifest_path = V2_DECK / 'visual_manifest.json'
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for filename, expected_hash in manifest.get('sha256', {}).items():
        artifact = V2_DECK / filename
        if not artifact.is_file() or sha(artifact) != expected_hash:
            errors.append(f'Archived V2 presentation mismatch: {filename}')
    for filename, expected_hash in manifest.get('source_sha256', {}).items():
        source = ROOT / filename.replace('\\', '/')
        if not source.is_file() or sha(source) != expected_hash:
            errors.append(f'Research quoted by the archived V2 presentation changed: {filename}')
    pptx_hash = manifest.get('sha256', {}).get('Rewind_Amplify_Finals_Visual.pptx')
    for key in ('validation_report', 'visual_review_report'):
        # these paths were written relative to finals-deck/, where the V2 deck used to live
        report_path = (DECK / manifest.get(key, '')).resolve()
        if not report_path.is_relative_to(ROOT) or not report_path.is_file():
            errors.append(f'Missing archived presentation report: {key}')
            continue
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if key == 'validation_report' and report.get('finalSha256') != pptx_hash:
            errors.append('Archived structural report is for a different PPTX')
        if key == 'visual_review_report' and report.get('pptx_sha256') != pptx_hash:
            errors.append('Archived visual review is for a different PPTX')
    with zipfile.ZipFile(V2_DECK / 'Rewind_Amplify_Finals_Visual.pptx') as z:
        count = len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)])
    if count != manifest.get('total_slide_count'):
        errors.append('Archived V2 presentation has an unexpected slide count')
    else:
        print(f'Archived V2 presentation: {count} slides, hashes intact')


def check_offline_page(html: Path, label: str, errors: list) -> None:
    if not html.is_file():
        return
    parser = LocalAssetParser()
    parser.feed(html.read_text(encoding='utf-8'))
    before = len(errors)
    for resource in parser.assets:
        if re.match(r'(?i)^(https?:)?//', resource):
            errors.append(f'{label} has a network-loaded dependency: {resource}')
        elif not resource.startswith('data:') and not (html.parent / resource).is_file():
            errors.append(f'{label} is missing a local asset: {resource}')
    if len(errors) == before:
        print(f'{label}: {len(parser.assets)} load-time assets available locally')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--public', action='store_true', help='check the public edition, which omits the supplied private rubric workbook')
    args = parser.parse_args()
    errors = []
    for name in REQUIRED:
        if args.public and name == 'Qiskit_Fall_Fest_Judging_Rubric.xlsx':
            continue
        path = ROOT / name
        if not path.is_file() or not path.stat().st_size:
            errors.append(f'Missing or empty: {name}')
    check_v3_deck(errors)
    check_v2_deck(errors)

    app_check = ROOT / 'laser-diagnostics-app/check_package.py'
    if app_check.is_file():
        result = subprocess.run([sys.executable, str(app_check)], capture_output=True, text=True)
        if result.returncode:
            errors.append('Research explorer package check failed: ' + result.stderr.strip())
        else:
            print('Research explorer: local assets, links and copied evidence hashes verified')
    else:
        errors.append('Missing research explorer package checker')

    original_path = ROOT / 'research-validation/original_after_click_verification.json'
    if original_path.is_file():
        original = json.loads(original_path.read_text(encoding='utf-8'))
        if original.get('verified') is not True:
            errors.append('Original after-click verification did not pass')
        for filename, expected_hash in original.get('source_sha256', {}).items():
            source = ROOT / filename
            if not source.is_file() or sha(source) != expected_hash:
                errors.append(f'Original after-click evidence does not match source: {filename}')
    sensor_path = ROOT / 'laser_sensor_viability/results.json'
    if sensor_path.is_file():
        sensor = json.loads(sensor_path.read_text(encoding='utf-8'))
        for filename, expected_hash in sensor.get('source_sha256', {}).items():
            source = sensor_path.parent / filename
            if not source.is_file() or sha(source) != expected_hash:
                errors.append(f'Sensor results do not match source: {filename}')
        if len(sensor.get('scenarios', [])) < 8:
            errors.append('Expected the eight declared sensor scenarios')

    check_offline_page(ROOT / 'lab/index.html', 'Lab', errors)
    check_offline_page(ROOT / 'Rewind_Amplify_Lab.html', 'Single-file Lab', errors)
    check_offline_page(ROOT / 'finals-lithography/index.html', 'Lithography mini-demo', errors)

    if errors:
        for error in errors:
            print('ERROR:', error, file=sys.stderr)
        return 1
    print('Files passed basic checks. Open the deck and the Lab on the presentation computer and rehearse.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
