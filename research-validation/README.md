# Independent verification and reproduction

The featured hardware analysis and optical sensor study have separate verification records. These establish software consistency and explicitly stated model properties, not experimental validation of an optical device.

| Check | Implementation | Saved evidence |
|---|---|---|
| Featured IBM pair, both archived jobs | `verify_hardware.py` rebuilds logical Qiskit circuits, recounts the correct event bit, reapplies archived calibration and compares conditional-history errors | `hardware_verification.json` |
| Original after-click question | `verify_original_after_click.py` independently propagates a density matrix, rebuilds full/local Qiskit queries, and recounts raw and corrected longer-loop results from both saved jobs | `original_after_click_verification.json` |
| Optical dynamics | `verify_sensor_physics.py` independently exponentiates a complex Lindblad superoperator and compares the Bloch implementation across 42 parameter points | `sensor_physics_verification.json` |
| Reference ambiguity | The same independent verifier shifts source and both references together and checks invariant observations and a rank-deficient sensitivity matrix | `sensor_physics_verification.json` |
| Complete sensor reproduction | Separate full experiment output compared field for field with the canonical results and traces | `sensor_reproduction_verification.json`, `reproduced-sensor/` |
| Application behavior | Observed browser interactions at desktop and narrow widths, numeric controls, failure case, keyboard fixes and GIF playback | `../laser-diagnostics-app/browser_validation.json` |

From the project root, use Python with the relevant dependencies:

```powershell
python -m pip install -r laser_sensor_viability/requirements.txt
python -m unittest discover -s laser_sensor_viability -p test_model.py
python research-validation/verify_sensor_physics.py
python laser_sensor_viability/run_experiment.py --out laser_sensor_viability/fresh-reproduction
```

The last command refuses to overwrite an existing result by default. The full experiment takes a few minutes and makes no cloud calls. For the hardware verifiers, additionally install the original project's dependencies from `rewindandamplify-main/requirements.txt`, then run `python research-validation/verify_hardware.py` and `python research-validation/verify_original_after_click.py`. They read archived counts; they do not contact IBM.

The app's JavaScript checks use `node --test laser-diagnostics-app/test_model.cjs`. Its package checker uses only standard Python: `python laser-diagnostics-app/check_package.py`. The current presentation media are MP4 videos with playback controls; conversion and decoding checks are documented in `animations/README.md`. The original explanatory frames can be regenerated with `python animations/build_animations.py` using Pillow 11.3.0 and the documented Windows fonts. Normal demo playback needs no Python or Node.

The canonical results record a plot-title editorial correction after the complete numerical reproduction. The numerical tree and traces remain exactly equal. The reproduction receipt excludes only that editorial provenance and its associated source-file hashes from equality checks; canonical source hashes are verified separately.
