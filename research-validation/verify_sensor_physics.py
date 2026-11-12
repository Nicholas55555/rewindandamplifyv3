"""Independent density-matrix and identifiability checks for the sensor model.

The implementation under review propagates Bloch vectors with operator splitting.
This check instead exponentiates a Lindblad superoperator on density matrices.
"""
from dataclasses import replace
from pathlib import Path
import json
import hashlib
import sys
import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "laser_sensor_viability"))
from model import Config, ramsey_probability

I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1., -1.]).astype(complex)


def propagate(rho, hamiltonian, duration, config):
    generator = -1j * (np.kron(I, hamiltonian) - np.kron(hamiltonian.T, I))
    relaxation = np.array([[0, 0], [1, 0]], complex) / np.sqrt(config.t1_s)
    pure_dephasing = max(0., 1 / config.t2_s - 1 / (2 * config.t1_s))
    for collapse in (relaxation, np.sqrt(pure_dephasing / 2) * Z):
        norm = collapse.conj().T @ collapse
        generator += (np.kron(collapse.conj(), collapse)
                      - .5 * np.kron(I, norm) - .5 * np.kron(norm.T, I))
    vector = expm(generator * duration) @ rho.reshape(-1, order="F")
    return vector.reshape((2, 2), order="F")


def exact_probability(detuning, power, config):
    rho = np.diag([config.preparation_error, 1 - config.preparation_error]).astype(complex)
    omega = np.pi / (2 * config.pulse_s) * np.sqrt(power)
    pulse_delta = detuning - config.pulse_lightshift_hz_per_relative_power * (power - 1)
    rho = propagate(rho, omega / 2 * X + np.pi * pulse_delta * Z, config.pulse_s, config)
    rho = propagate(rho, np.pi * detuning * Z, config.dark_s, config)
    rho = propagate(rho, omega / 2 * Y + np.pi * pulse_delta * Z, config.pulse_s, config)
    if not np.isclose(np.trace(rho), 1) or np.linalg.eigvalsh(rho).min() < -1e-12:
        raise AssertionError("Exact propagated state is not physical")
    born = float(rho[0, 0].real)
    return config.readout_01 + (1 - config.readout_01 - config.readout_10) * born


def main():
    rows = []
    for label, config in [("nominal", Config()),
                          ("short_coherence", replace(Config(), t2_s=.012, readout_01=.1, readout_10=.14))]:
        errors4, errors16, errors_default = [], [], []
        for delta in [-25., -5., -.5, 0., .5, 5., 25.]:
            for power in [.6, 1., 1.4]:
                exact = exact_probability(delta, power, config)
                errors4.append(abs(exact - float(ramsey_probability(delta, power, config, subdivisions=4))))
                errors16.append(abs(exact - float(ramsey_probability(delta, power, config, subdivisions=16))))
                errors_default.append(abs(exact - float(ramsey_probability(delta, power, config))))
        if max(errors_default) > 1e-4 or max(errors16) > max(errors4) / 10:
            raise AssertionError((label, max(errors4), max(errors16)))
        rows.append({"case": label, "points": len(errors4),
                     "max_probability_error_4_substeps": max(errors4),
                     "max_probability_error_16_substeps": max(errors16),
                     "max_probability_error_production_default": max(errors_default)})
    # Relative-frequency observations alone cannot identify a common shift
    # of source, primary reference and atomic transition.
    source, optical_ref, atomic_ref, shift = .7, .2, -.1, 2.0
    before = np.array([source - optical_ref,
                       float(ramsey_probability(source - atomic_ref))])
    after = np.array([(source + shift) - (optical_ref + shift),
                      float(ramsey_probability((source + shift) - (atomic_ref + shift)))])
    assert np.allclose(before, after, atol=1e-14, rtol=0)
    sensitivity = np.array([[1, -1, 0], [1, 0, -1]])
    assert np.linalg.matrix_rank(sensitivity) == 2
    assert np.array_equal(sensitivity @ np.ones(3), np.zeros(2))
    result = {"status": "pass", "independent_method": "Exact complex Lindblad density-matrix propagation",
              "model_sha256": hashlib.sha256((ROOT / "laser_sensor_viability/model.py").read_bytes()).hexdigest(),
              "checks": rows,
              "common_shift_identifiability": {"sensor_values_unchanged": True, "rank": 2, "unknown_frequencies": 3,
               "meaning": "Independent reference stability or another anchor is required to identify absolute source drift."},
              "scope": "Numerical consistency and model identifiability, not experimental validation."}
    Path(__file__).with_name("sensor_physics_verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
