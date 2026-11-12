"""Check the local finals handoff using only the Python standard library.

This verifies file availability, slide package integrity and offline visual
assets. It does not replace a browser/PowerPoint rehearsal, quantum-software
tests, hardware validation, or checking the event's submission rules.
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
REQUIRED = [
    'START_HERE_FINALS.md', 'FINALS_TALK.md', 'FINALS_QA.md', 'FINALS_EVIDENCE.md', 'FINALS_RUBRIC.md',
    'Qiskit_Fall_Fest_Judging_Rubric.xlsx',
    'finals-deck/Rewind_Amplify_Finals_Visual.pptx', 'finals-deck/Rewind_Amplify_Finals_Visual.pdf',
    'finals-deck/visual_manifest.json', 'finals-deck/Visual_Presenter_Guide.md',
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


class LocalAssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.external_resources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        # External <a> links are optional background, not load-time dependencies.
        if tag in ('img', 'script', 'iframe') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel', '').lower() == 'stylesheet' and attrs.get('href'):
            self.assets.append(attrs['href'])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', action='store_true', help='check the public edition, which omits the supplied private rubric workbook')
    args = parser.parse_args()
    errors = []
    for name in REQUIRED:
        if args.public and name == 'Qiskit_Fall_Fest_Judging_Rubric.xlsx':
            continue
        path = ROOT / name
        if not path.is_file() or not path.stat().st_size:
            errors.append(f'Missing or empty: {name}')
    manifest_path = ROOT / 'finals-deck/visual_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else {}
    pptx = ROOT / 'finals-deck/Rewind_Amplify_Finals_Visual.pptx'
    if pptx.is_file():
        try:
            with zipfile.ZipFile(pptx) as z:
                bad = z.testzip()
                if bad:
                    errors.append(f'Corrupt presentation member: {bad}')
                slides = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
                notes = [n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)]
                expected = manifest.get('total_slide_count')
                if len(slides) != expected or len(notes) != expected or manifest.get('main_slide_count') != 13:
                    errors.append(f'Expected thirteen main slides and {expected} total slides/notes; found {len(slides)} and {len(notes)}')
                else:
                    print(f'Presentation: {len(slides)} slides and note pages, package intact')
                scripts_path = ROOT/'.finals-deck-build/visual_notes.json'
                if scripts_path.is_file():
                    scripts = json.loads(scripts_path.read_text(encoding='utf-8'))
                    if len(scripts) != len(slides):
                        errors.append('Presenter source count differs from deck')
                    for i, script in enumerate(scripts, 1):
                        name = f'ppt/notesSlides/notesSlide{i}.xml'
                        if name not in z.namelist():
                            continue
                        node = ET.fromstring(z.read(name))
                        text = ' '.join(t.text or '' for t in node.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'))
                        normalize = lambda x: re.sub(r'\s+', ' ', x).strip()
                        if normalize(script['text']) not in normalize(text):
                            errors.append(f'Embedded speaker script differs on slide {i}')
                    endpoint = 0
                    for script in scripts[:13]:
                        start, end = script['time'].split('–')
                        seconds = lambda t: sum(int(v)*m for v,m in zip(t.split(':'), (60,1)))
                        if seconds(start) != endpoint:
                            errors.append('Main talk timeline has a gap/overlap')
                        endpoint = seconds(end)
                    if endpoint != 560 or manifest.get('talk_timing_seconds') != 560:
                        errors.append('Expected the 9:20 main talk plan')
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append(f'Could not read presentation: {exc}')
    pdf = ROOT / 'finals-deck/Rewind_Amplify_Finals_Visual.pdf'
    if pdf.is_file() and pdf.read_bytes()[:5] != b'%PDF-':
        errors.append('PDF fallback does not have a PDF header')
    for filename, expected_hash in manifest.get('sha256', {}).items():
        artifact = ROOT / 'finals-deck' / filename
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected_hash:
            errors.append(f'Presentation manifest mismatch: {filename}')
    if not manifest.get('source_sha256'):
        errors.append('Current presentation is missing its research-source hash map')
    for filename, expected_hash in manifest.get('source_sha256', {}).items():
        source = ROOT / filename.replace('\\', '/')
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
            errors.append(f'Presentation research source mismatch: {filename}')
    for key in ('validation_report', 'visual_review_report'):
        report_path = (ROOT / 'finals-deck' / manifest.get(key, '')).resolve()
        if not report_path.is_relative_to(ROOT) or not report_path.is_file():
            errors.append(f'Missing local presentation report: {key}')
            continue
        report = json.loads(report_path.read_text(encoding='utf-8'))
        pptx_hash = manifest.get('sha256', {}).get(pptx.name)
        if key == 'validation_report':
            if report.get('finalSha256') != pptx_hash:
                errors.append('Presentation structural report is for a different PPTX')
            for section in ('packageIntegrity', 'presentationLayout'):
                if report.get(section, {}).get('slide_count') != manifest.get('total_slide_count'):
                    errors.append(f'Presentation report slide count differs: {section}')
        else:
            if report.get('pptx_sha256') != pptx_hash or report.get('pdf_sha256') != manifest.get('sha256', {}).get(pdf.name):
                errors.append('Presentation visual review is for different output files')
            if report.get('reviewed_slide_count') != manifest.get('total_slide_count'):
                errors.append('Presentation visual review does not cover the current deck')
    app_check = ROOT / 'laser-diagnostics-app/check_package.py'
    if app_check.is_file():
        result = subprocess.run([sys.executable, str(app_check)], capture_output=True, text=True)
        if result.returncode:
            errors.append('Application package check failed: ' + result.stderr.strip())
        else:
            print('Application: local assets, links and copied evidence hashes verified')
    else:
        errors.append('Missing application package checker')
    original_path = ROOT / 'research-validation/original_after_click_verification.json'
    if original_path.is_file():
        original = json.loads(original_path.read_text(encoding='utf-8'))
        if original.get('verified') is not True:
            errors.append('Original after-click verification did not pass')
        for filename, expected_hash in original.get('source_sha256', {}).items():
            source = ROOT / filename
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
                errors.append(f'Original after-click evidence does not match source: {filename}')
    sensor_path = ROOT / 'laser_sensor_viability/results.json'
    if sensor_path.is_file():
        sensor = json.loads(sensor_path.read_text(encoding='utf-8'))
        for filename, expected_hash in sensor.get('source_sha256', {}).items():
            source = sensor_path.parent / filename
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
                errors.append(f'Sensor results do not match source: {filename}')
        if len(sensor.get('scenarios', [])) < 8:
            errors.append('Expected the eight declared sensor scenarios')
    html = ROOT / 'finals-lithography/index.html'
    if html.is_file():
        parser = LocalAssetParser()
        parser.feed(html.read_text(encoding='utf-8'))
        for resource in parser.assets:
            if re.match(r'(?i)^(https?:)?//', resource):
                errors.append(f'Visual demo has a network-loaded dependency: {resource}')
            elif not (html.parent / resource).is_file():
                errors.append(f'Missing visual asset: {resource}')
        if not errors:
            print(f'Visual demo: {len(parser.assets)} load-time assets available locally')
    if errors:
        for error in errors:
            print('ERROR:', error, file=sys.stderr)
        return 1
    print('Files passed basic checks. Open the deck and demo on the presentation computer and rehearse.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
