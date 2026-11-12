# Pre-evaluation numerical clarification

Added before generating the main training/calibration/held-out records. Record log-likelihood ratios of absolute magnitude below1e−10 are numerical zero. This avoids treating floating-point differences between mathematically identical passive record laws as evidence. This tolerance is fixed in inference.py and tested on passive records; it is not selected from held-out classification performance. The zero result has a separate exact effect-operator check.

The unchanged PROTOCOL.md remains the hardware-bundle source snapshot. This clarification concerns the later synthetic classifier only and does not change any emitted state, circuit, instrument, parameter, measurement or exact reference probability. Main inference provenance includes this file.
