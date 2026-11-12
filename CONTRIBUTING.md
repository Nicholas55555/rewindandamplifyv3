# Contributing

Start with [RESEARCH_RESULTS.md](RESEARCH_RESULTS.md) for the current scientific status and the relevant study README for its assumptions. The original QRSM project is in `rewindandamplify-main/`; later optical, sensor and lithography studies retain their own directories and frozen evidence. The offline application is in `laser-diagnostics-app/`.

## Local development

Use Python 3.12 and a dedicated virtual environment. The development dependency file extends the audited research environment with the original project's test framework and IBM Runtime package. Tests use local fake backends; no IBM account or API key is required.

```sh
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in PowerShell, then install:

```sh
python -m pip install -r requirements-dev.txt
```

Use Node.js 24 for the app checks. The app has no npm dependencies or build step and opens directly from `index.html`.

## Checks before a pull request

From the repository root:

```sh
node --test lab/test_engine.cjs lab/test_data.cjs lab/test_research.cjs laser-diagnostics-app/test_model.cjs
python lab/make_data.py --check
python lab/build.py --check
python laser-diagnostics-app/check_package.py
python laser-diagnostics-app/build_standalone.py --check
python check_finals.py --public
python verify_research_pack.py .
python .github/scripts/check_publication.py
python .github/scripts/run_tests.py --group core
python .github/scripts/run_tests.py --group research
python lab/make_reference.py --check
python reproduce.py
```

If you change anything under `lab/`, rebuild the single file with `python lab/build.py`. If a saved hardware result changes, run `python lab/make_data.py` and rebuild the deck (see [finals-deck/README.md](finals-deck/README.md)): `check_finals.py` fails until the slides agree with the evidence again.

The runner starts a fresh process for each test directory, limits each suite to five minutes, and limits numerical libraries to one thread. Do not collect every `test_model.py` in one Python process: several studies deliberately have distinct modules named `model`. `--list` prints the selected commands without running them. The original photon CPTP check is an executable script rather than a unittest class, so the runner invokes it explicitly.

CI uses Python 3.12 on Linux and Windows for bounded scientific tests and runs the app/evidence checks on Linux. It checks existing mathematical tests, small circuit models, retained external-data integrity, causal detection accounting and exact app/source parity. It does not regenerate long statistical studies, reconstruct/read giant QPY circuits, render the presentation, contact IBM, publish anything, or claim independent laboratory validation. Some unit tests contain small seeded sampling experiments; these do not replace the saved full studies.

The optional browser check in the app README requires preinstalled Python Playwright and Chrome. It is not part of default CI: it writes screenshots and a browser-validation receipt, and H.264 support varies between Chromium distributions. PowerPoint COM/Windows-specific deck rendering and scientific artifact-generation tools have separate dependencies and instructions.

## Preserve evidence and make changes reviewable

- Keep protocol, model, acquisition cost and outcome definitions explicit. A 32-second unknown-onset detection rate is different from the earlier known-onset batch rate; source-stable false alarms and source-event detection use different record populations.
- Retain classical comparators, detector controls and the prior-only amplitude control. Separate circuit execution, classical inference, optical simulation and proposed laboratory applications.
- Write new experiments into a new output directory with their source hashes, seeds, assumptions and bounds. Do not silently replace frozen numerical files or relabel an earlier experiment with a new task. Explain changed parameters and whether new holdouts were used.
- Preserve artifact bytes and the repository's `.gitattributes` policy. Line-ending conversion alone can invalidate saved SHA-256 provenance. Do not refresh a manifest merely to hide an unexplained mismatch.
- When intentionally updating app evidence, run `laser-diagnostics-app/import_results.py` only after the canonical study outputs are reviewed, then rerun parity/package checks and appropriate browser checks. Importing is a packaging action, not a new scientific run.
- Several `validate_*`, `verify_*`, plot and delivery scripts write receipts or figures. Inspect a script before using it as a read-only check. The commands above are the supported nonregenerating CI path.
- Keep credentials outside source, notebooks, screenshots and artifacts. Changes to hardware execution require an explicit task, resource budget and interpretation criterion; ordinary CI has no hardware credentials.

A pull request should state the concrete problem, the changed behavior or scientific claim, the validation performed, and any remaining uncertainty. Small documentation changes need proportionate checks; a scientific change needs tests that can detect a wrong model or accounting rule, not just tests that repeat the implementation.

## Dependency and portability notes

The root development environment follows `research-validation/research_requirements.txt`. Some historical subprojects pin a different SciPy version because their original results used an earlier environment. Keep those records intact; use an isolated environment when reproducing a historical run exactly. The root test environment validates the current combined tree and does not promise identical platform floating-point behavior for every regenerated experiment.

The original QRSM tests require `rewindandamplify-main/tests/data/step_operator_k*.npy`, its `demo/` helpers and local fake-backend data supplied by the pinned Runtime package. The external-data tests require the retained source CSV and its accompanying license/provenance. The research integrity check requires all files listed in `RESEARCH_ARCHIVE_MANIFEST.json`, even when they are not imported by a unit test.

See the workflow's upstream [checkout](https://github.com/actions/checkout), [Python setup](https://github.com/actions/setup-python) and [Node setup](https://github.com/actions/setup-node) documentation when updating action versions. Preserve read-only permissions, bounded execution and the separation between test and publication workflows.
