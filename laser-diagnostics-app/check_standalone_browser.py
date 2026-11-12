"""Check the exported v2 HTML in an otherwise empty directory, with Chrome offline.

Requires an existing Python Playwright installation and system Chrome. Does not
install a browser, contact IBM, rerun science, or rewrite existing app QA files.
Optional screenshots and a receipt are saved only beneath .publication-audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tempfile
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STUDIES = ("frequency", "drive", "phase", "progress", "dot", "hardware")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_evidence(name: str):
    return json.loads((HERE / "evidence" / name).read_text(encoding="utf-8"))


def check(html: Path, output: Path | None = None) -> dict:
    assert html.is_file(), f"Missing exported HTML: {html}"
    if output is not None:
        output = output.resolve()
        assert output.is_relative_to(ROOT / ".publication-audit"), (
            "--output must be a directory beneath the ignored .publication-audit directory"
        )
        output.mkdir(parents=True, exist_ok=True)
    original = read_evidence("original_after_click_verification.json")
    dot = read_evidence("research_dot.json")
    design = read_evidence("research_dot_design_validation.json")
    hardware = read_evidence("research_hardware.json")
    errors, network, unexpected_files, checks, screenshots, downloads = [], [], [], [], [], []
    unique_downloads = set()

    def percent(actual, expected):
        assert abs(float(actual.rstrip("%")) - 100 * expected) <= .0050000001, (actual, expected)

    def text(page, selector, expected):
        assert expected in page.locator(selector).inner_text(), (selector, expected)

    def no_overflow(page):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow"

    def screenshot(page, name):
        if output is not None:
            page.screenshot(path=str(output / name), full_page=False)
            screenshots.append(name)

    with tempfile.TemporaryDirectory(prefix="rewind_single_html_") as temporary:
        isolated = Path(temporary).resolve()
        copied = isolated / html.name
        shutil.copyfile(html, copied)
        tested_hash = sha(copied)
        tested_bytes = copied.stat().st_size
        assert list(isolated.iterdir()) == [copied], "Isolation must start with only one HTML file"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, device_scale_factor=1,
                offline=True, accept_downloads=True, service_workers="block",
            )
            # A separate route guard records even an attempted external request.
            context.route("http://**/*", lambda route: (network.append(route.request.url), route.abort()))
            context.route("https://**/*", lambda route: (network.append(route.request.url), route.abort()))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))

            def requested(request):
                url = request.url
                parts = urlsplit(url)
                if parts.scheme in {"http", "https", "ws", "wss"}:
                    network.append(url)
                elif parts.scheme == "file":
                    # Ignore query/hash changes to the same isolated document.
                    if unquote(parts.path).lstrip("/").casefold() != copied.as_posix().lstrip("/").casefold():
                        unexpected_files.append(url)

            page.on("request", requested)

            def ready():
                page.wait_for_function("Boolean(window.PORTABLE_DEMO && window.PORTABLE_DEMO.ready)")
                page.evaluate("async () => { await window.PORTABLE_DEMO.ready; }")

            def go(suffix=""):
                # Test a fresh file entry; fragment-only navigation does not
                # reload the app and is not how its chapter buttons operate.
                page.goto("about:blank")
                page.goto(copied.as_uri() + suffix, wait_until="load")
                ready()

            def mapped(link):
                # Wait for asynchronous mapping after a selector rewrites href.
                page.wait_for_function(
                    "e => e.getAttribute('href').startsWith('blob:') && !!e.dataset.portablePath",
                    arg=link.element_handle(),
                )
                relative = link.get_attribute("data-portable-path")
                source = (HERE / relative).resolve()
                assert source.is_relative_to(HERE) and source.is_file(), relative
                assert relative in metadata, relative
                assert link.get_attribute("download") == source.name, relative
                return relative, source

            def download(link):
                relative, source = mapped(link)
                if relative in unique_downloads:
                    return relative
                with page.expect_download() as pending:
                    link.click()
                downloaded = pending.value
                assert downloaded.failure() is None, relative
                assert downloaded.suggested_filename == source.name, relative
                destination = isolated / "downloads" / str(len(downloads)) / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                downloaded.save_as(str(destination))
                actual = sha(destination)
                assert actual == sha(source) == metadata[relative]["sha256"], relative
                downloads.append({"path": relative, "sha256": actual, "bytes": destination.stat().st_size})
                unique_downloads.add(relative)
                return relative

            go()
            assert page.locator("#rewind").is_visible()
            assert not page.locator("body").evaluate("e => e.classList.contains('focus-view')")
            metadata = page.evaluate("Object.fromEntries(Object.entries(PORTABLE_DEMO.files).map(([k,v]) => [k,{sha256:v.sha256,filename:v.filename}]))")
            required = {p.relative_to(HERE).as_posix() for p in (HERE / "evidence").rglob("*") if p.is_file()}
            assert required <= set(metadata), sorted(required - set(metadata))
            assert "README.md" in metadata
            for relative, entry in metadata.items():
                source = (HERE / relative).resolve()
                assert source.is_relative_to(HERE) and source.is_file(), relative
                assert entry["sha256"] == sha(source), relative
            checks.append(f"Only the exported HTML is copied; all {len(required)} evidence files and the demo guide are embedded with matching hashes")
            screenshot(page, "standalone-original-desktop.png")

            for model, button in [("with_hidden_defect", "core-coupled"), ("no_hidden_defect", "core-emitter")]:
                page.locator("#" + button).click()
                for method, saved in original["models"][model]["ideal_circuits"].items():
                    page.locator("#core-method").select_option(method)
                    percent(page.locator("#core-acceptance").inner_text(), saved["event_probability"])
                    for i, expected in enumerate(saved["conditional_probabilities"]):
                        percent(page.locator("#core-future-values strong").nth(i).inner_text(), expected)
                    no_overflow(page)
            page.locator("#core-coupled").click()
            page.locator("#core-method").select_option("plain")
            download(page.locator('a[data-portable-path="evidence/original_after_click_verification.json"]').first)
            checks.append("Both original QRSM models and every sampling method retain saved acceptance and conditional future answers")

            page.locator("#present").click()
            assert page.locator("body").evaluate("e => e.classList.contains('focus-view')")
            go("?focus=1#research")
            assert page.locator("body").evaluate("e => e.classList.contains('focus-view')")
            assert page.locator("#research").is_visible()
            for study in STUDIES:
                page.locator("#study-" + study).click()
                assert page.locator("#research-" + study).is_visible()
                assert page.locator("#study-" + study).get_attribute("aria-pressed") == "true"
                no_overflow(page)
            text(page, "#hardware-summary", "688,640")
            text(page, "#hardware-original", "0.1177")
            text(page, "#hardware-original", "0.1814")
            checks.append("All six current research views render in the isolated file; hash routing and Focus view work")

            page.locator("#study-dot").click()
            for case in dot["benchmark_cases"]:
                page.locator("#dot-case").select_option(case["case"])
                percent(page.locator("#dot-overlap").inner_text(), case["conditional_overlap"])
            for trial in design["power_trials"]:
                page.locator("#dot-design-budget").select_option(str(trial["independent_blocks"]))
                text(page, "#dot-design-detail", f'{trial["attempted_pairs"]:,} attempted pairs')
            for delay in (13.1, 26.2, 39.4):
                page.locator("#dot-hom-pair").select_option(str(delay))
                text(page, "#dot-hom-detail", f"{delay:.1f} ns apart")
                for selector in ("#dot-co-csv", "#dot-cross-csv"):
                    download(page.locator(selector))
                for link in page.locator("#dot-analysis a").all():
                    download(link)
            assert len([d for d in downloads if d["path"].endswith(".csv")]) == 6
            page.locator("#dot-design-budget").select_option("646")
            page.locator("#dot-instrument").scroll_into_view_if_needed()
            screenshot(page, "standalone-dot-desktop.png")
            checks.append("Four dot cases and all six acquisition budgets work; six dynamically switched CSV downloads and generated analysis links preserve exact bytes")

            page.locator("#study-hardware").click()
            circuits = histories = 0
            for family in ("dot_frozen", "dot_joint", "dot_selected_four_pair", "atomic", "photon", "spatial", "optical_dilation"):
                rows = hardware["family_results"][family]
                page.locator("#hardware-family").select_option(family)
                for i, row in enumerate(rows):
                    page.locator("#hardware-circuit").select_option(str(i))
                    circuits += 1
                    text(page, "#hardware-circuit-context", row["name"])
                    observed = row["observables"]
                    if "histories" in observed:
                        for history, saved in observed["histories"].items():
                            page.locator("#hardware-history").select_option(history)
                            percent(page.locator("#hardware-values strong").first.inner_text(), saved["observed"]["probability"])
                            histories += 1
                    elif "raw_event_probability" in observed:
                        percent(page.locator("#hardware-values strong").first.inner_text(), observed["raw_event_probability"])
                    for link in page.locator("#hardware-evidence a").all():
                        download(link)
            assert page.locator(".hardware-job").count() == hardware["jobs"]
            for link in page.locator(".hardware-job a").all():
                if link.get_attribute("href").startswith("https:"):
                    assert link.get_attribute("href") == "https://quantum.cloud.ibm.com/workloads"
                else:
                    download(link)
            text(page, "#hardware-failure-values", "0.7604")
            text(page, "#hardware-failure-values", "8 / 512")
            page.locator(".hardware-hero").scroll_into_view_if_needed()
            screenshot(page, "standalone-hardware-desktop.png")
            checks.append(f"All seven hardware families, {circuits} circuit views and {histories} flag histories work; generated raw-count/analysis/plan downloads match source hashes")

            page.locator("#tab-sensor").click()
            text(page, ".history-note", "told that the event starts at 64 s")
            page.locator("#open-current-research").click()
            assert page.locator("#research-frequency").is_visible()
            page.locator("#tab-evidence").click()
            videos = []
            for identifier in ("video-sensing", "video-quantum-extension"):
                video = page.locator("#" + identifier)
                video.scroll_into_view_if_needed()
                assert video.get_attribute("autoplay") is None
                assert video.get_attribute("controls") is not None
                assert video.get_attribute("poster").startswith("data:image/")
                assert video.locator("source").get_attribute("src").startswith("data:video/mp4;base64,")
                video.evaluate("v => v.load()")
                page.wait_for_function("id => document.getElementById(id).readyState >= 2", arg=identifier)
                duration = video.evaluate("v => v.duration")
                assert abs(duration - 12) < .05
                video.evaluate("v => v.play()")
                page.wait_for_function("id => document.getElementById(id).currentTime > 0.1", arg=identifier)
                video.evaluate("v => { v.pause(); v.currentTime = 6; }")
                page.wait_for_function("id => Math.abs(document.getElementById(id).currentTime - 6) < .1 && !document.getElementById(id).seeking", arg=identifier)
                assert video.evaluate("v => v.paused")
                videos.append({"id": identifier, "duration_seconds": duration, "play_pause_seek": "passed"})
            screenshot(page, "standalone-videos-desktop.png")
            checks.append("Both embedded 12-second H.264 MP4s play, pause and seek with offline posters; historical-study navigation remains distinct")

            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#tab-rewind").click()
            no_overflow(page)
            page.locator("#tab-research").click()
            for study in STUDIES:
                page.locator("#study-" + study).click()
                no_overflow(page)
                page.locator("#research-" + study).scroll_into_view_if_needed()
                screenshot(page, f"standalone-{study}-mobile.png")
            checks.append("Original view and all six research views fit a 390px viewport without document horizontal overflow")

            go("?focus=1#rewind")
            assert page.locator("#rewind").is_visible()
            page.emulate_media(reduced_motion="reduce")
            page.reload()
            ready()
            assert all(page.locator("#" + name).is_disabled() for name in ("motion", "replay", "walk"))
            assert not network, network
            assert not unexpected_files, unexpected_files
            assert not errors, errors
            checks.append("Offline and network-blocked throughout: zero attempted remote requests, missing sibling-file requests or page errors; reduced-motion behavior retained")
            version = browser.version
            context.close()
            browser.close()

    receipt = {
        "status": "passed", "all_checks_passed": True,
        "route": "Only the exported HTML copied into a fresh temporary directory; isolated system Chrome with offline networking and HTTP(S) route blocking",
        "html": html.name, "html_sha256": tested_hash, "html_bytes": tested_bytes,
        "checker_sha256": sha(Path(__file__)), "python": platform.python_version(), "chromium": version,
        "checks": checks, "embedded_files_checked": len(metadata), "downloaded_files": downloads,
        "videos": videos, "screenshots": screenshots, "page_errors": errors,
        "remote_requests": network, "unexpected_file_requests": unexpected_files,
    }
    if output is not None:
        (output / "standalone_browser_validation.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=ROOT / "Rewind_Amplify_v2_Demo.html")
    parser.add_argument("--output", type=Path, help="Optional receipt/screenshots directory beneath .publication-audit")
    arguments = parser.parse_args()
    result = check(arguments.html.resolve(), arguments.output)
    print(json.dumps({key: result[key] for key in ("status", "html_sha256", "html_bytes", "embedded_files_checked", "page_errors", "remote_requests", "unexpected_file_requests")} | {"checks": len(result["checks"]), "downloaded_files": len(result["downloaded_files"]), "screenshots": len(result["screenshots"])}, indent=2))


if __name__ == "__main__":
    main()
