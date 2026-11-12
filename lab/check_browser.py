"""Open the Lab in a real browser and fail on anything broken.

Loads the folder app and the single-file build from disk, visits all seven scenes at both caption levels, presses
every control once, and checks that the numbers on screen are the ones the evidence supports. Any console error,
uncaught exception or request to the network is a failure.

    python lab/check_browser.py

Needs an installed Chrome or Edge and:  pip install playwright
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PAGES = {"folder app": HERE / "index.html", "single file": ROOT / "Rewind_Amplify_Lab.html"}
SCENES = ["signal", "machine", "question", "rewind", "answer", "hardware", "impact"]
# what must be on screen, taken from the evidence the tests already pin
EXPECT = {
    "answer": {"#ans-none": "10.10%", "#ans-defect": "4.67%"},
    "hardware": {"#hw-local-rate": "76.90%", "#hw-full-rate": "69.26%", "#hw-tv-local": "0.118", "#hw-tv-full": "0.181",
                 "#hw-nm-local": "78.4%", "#hw-nm-full": "69.7%", "#hw-plain-rate": "6.74%"},
    "rewind": {"#amp-hit": "96.10%", "#amp-tv": "0.035", "#amp-gates": "58"},
}


def check_page(context, label: str, path: Path) -> list[str]:
    problems: list[str] = []
    page = context.new_page()
    page.on("console", lambda m: problems.append(f"{label}: console {m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(f"{label}: uncaught {e}"))
    page.on("request", lambda r: problems.append(f"{label}: network request {r.url}")
            if r.url.startswith(("http://", "https://")) else None)
    page.goto(path.as_uri() + "?capture=1&seed=7")
    page.wait_for_function("window.LAB !== undefined")
    page.evaluate("LAB.manual()")
    step = "for (let i = 0; i < 90; i++) LAB.tick(1000 / 30)"
    for level in ("plain", "tech"):
        page.click(f"#level-{level}")
        for scene in SCENES:
            page.click(f'.scenes button[data-scene="{scene}"]')
            page.evaluate(step)
            if page.evaluate("LAB.state.scene") != scene:
                problems.append(f"{label}: could not open scene {scene}")
            if page.locator(f"#{scene}").is_hidden():
                problems.append(f"{label}: scene {scene} is hidden")
            for selector, want in EXPECT.get(scene, {}).items():
                got = page.locator(selector).inner_text().strip()
                if got != want:
                    problems.append(f"{label}: {scene} {selector} shows {got!r}, expected {want!r}")
            hidden_level = "tech" if level == "plain" else "plain"
            visible_wrong = page.evaluate(
                "([scene, cls]) => [...document.querySelectorAll(`#${scene} .${cls}`)].filter(e => e.offsetParent !== null).length",
                [scene, hidden_level])
            if visible_wrong:
                problems.append(f"{label}: {scene} shows {visible_wrong} {hidden_level} captions at the {level} level")
    # every control once
    page.click('.scenes button[data-scene="signal"]')
    for selector in ("#toggle-reveal", "#toggle-defect", "#toggle-defect", "#toggle-reveal"):
        page.click(selector)
        page.evaluate(step)
    page.click('.scenes button[data-scene="question"]')
    page.click("#ff")
    page.evaluate(step)
    runs = page.evaluate("LAB.stats.runs")
    if runs < 5000:
        problems.append(f"{label}: fast-forward recorded only {runs} runs")
    page.click("#reset-runs")
    page.click('.scenes button[data-scene="rewind"]')
    for selector in ("#amp-steer", "#amp-full", "#amp-steer", "#amp-local", "#amp-play"):
        page.click(selector)
        page.evaluate(step)
    for stage in range(5):
        page.click(f'#stages button[data-stage="{stage}"]')
        page.evaluate(step)
    page.click('.scenes button[data-scene="answer"]')
    page.locator("#phi").fill("0")
    page.evaluate(step)
    zero = page.locator("#ans-defect").inner_text().strip()
    if zero != "10.10%":
        problems.append(f"{label}: with no coupling the defect model should match the emitter-only one, got {zero}")
    page.click("#phi-reset")
    page.click("#ans-sample")
    page.check("#show-ibm")
    page.evaluate(step)
    page.click('.scenes button[data-scene="hardware"]')
    for selector in ("#hw-first", "#hw-supp", "#hw-precision"):
        page.click(selector)
        page.evaluate(step)
    for key in ("ArrowRight", "ArrowLeft", "t", "t", "r", "d", "d", "7", "1"):
        page.keyboard.press(key)
        page.evaluate(step)
    # the tour runs to its end and returns control
    page.click("#tour")
    page.evaluate("for (let i = 0; i < 47 * 30; i++) LAB.tick(1000 / 30)")
    if page.evaluate("LAB.state.tour !== null"):
        problems.append(f"{label}: the tour did not finish in 46 seconds")
    if page.evaluate("LAB.state.scene") != "impact":
        problems.append(f"{label}: the tour did not end on the last scene")
    page.close()
    return problems


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        sys.exit("Install the browser helper first: pip install playwright")
    problems: list[str] = []
    with sync_playwright() as p:
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            sys.exit("No installed Chrome or Edge could be started")
        for width, height in ((1600, 900), (1280, 720), (390, 844)):
            context = browser.new_context(viewport={"width": width, "height": height})
            for label, path in PAGES.items():
                if path.is_file():
                    problems += check_page(context, f"{label} at {width}x{height}", path)
            context.close()
        browser.close()
    print(json.dumps({"status": "failed" if problems else "passed", "pages": len(PAGES), "viewports": 3,
                      "scenes": len(SCENES), "problems": problems}, indent=1))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
