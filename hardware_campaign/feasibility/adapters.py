"""Faithful, account-free adapters for frozen optical and spatial circuits.

No backend, Runtime service, credentials, or hardware submission is imported.
The model imports are isolated because historical directories use ``model.py``.
The hardware observable is a computational-basis distribution, not tomography.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
from qiskit import QuantumCircuit, transpile

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def _import_context(paths, aliases=None):
    old_path = sys.path[:]
    aliases = aliases or {}
    old = {name: sys.modules.get(name) for name in aliases}
    sys.path[:0] = [str(p) for p in paths]
    sys.modules.update(aliases)
    try:
        yield
    finally:
        sys.path[:] = old_path
        for name, value in old.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(None)
def optical_module():
    with _import_context([ROOT / 'qrsm_photon_poc']):
        return _load('_campaign_optical', ROOT / 'qrsm_photon_poc/multibin_followup/model.py')


@lru_cache(None)
def spatial_modules():
    folder = ROOT / 'finals-lithography/followup'
    model = _load('_campaign_spatial_model', folder / 'model.py')
    with _import_context([folder], {'model': model}):
        quantum = _load('_campaign_spatial_quantum', folder / 'quantum.py')
    return model, quantum


def source_hashes(paths):
    return {str(p.relative_to(ROOT)).replace('\\', '/'):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def resources(circuit):
    return {'qubits': circuit.num_qubits, 'depth': circuit.depth(),
            'operations': {str(k): int(v) for k, v in circuit.count_ops().items()},
            'basis': ['u', 'cx'], 'routing': 'none; generic all-to-all logical circuit'}


def marginal(probabilities, qubits):
    """Order supplied qubits from least to most significant marginal bit."""
    probabilities = np.asarray(probabilities, float)
    packed = np.zeros(len(probabilities), dtype=np.int64)
    indices = np.arange(len(probabilities), dtype=np.int64)
    for j, q in enumerate(qubits):
        packed |= ((indices >> q) & 1) << j
    return np.bincount(packed, weights=probabilities, minlength=1 << len(qubits))


@dataclass
class Experiment:
    circuit: QuantumCircuit
    metadata: dict
    target_marginal: np.ndarray


@lru_cache(None)
def _optical_components(cutoff):
    m = optical_module()
    original, retained, v, env_bits, report = m.instrument(cutoff)
    return original, retained, m.one_bin(v), env_bits, report


def build_optical(bins=1, cutoff=.03, event='last', rounds=0):
    """Frozen cavity-2 instrument, fresh flag/environment per actual time bin."""
    if bins not in (1, 2, 3) or rounds not in (0, 1) or event not in ('last', 'all'):
        raise ValueError('Supported optical ladder: 1..3 bins, 0/1 round, last/all event')
    if cutoff not in (.03, .003):
        raise ValueError('Use a frozen audited Choi cutoff: .03 or .003')
    m = optical_module()
    original, retained, one, env_bits, instrument_report = _optical_components(cutoff)
    prep, flags = m.prepare(one, bins, env_bits)
    body = m.amplify(prep, flags, event) if rounds else prep.copy()
    branches = m.channel_branches(retained, bins)
    original_branches = m.channel_branches(original, bins)
    p, state = m.selection(branches, event)
    po, original_state = m.selection(original_branches, event)
    expected = math.sin((2*rounds+1)*math.asin(math.sqrt(p)))**2
    target = np.zeros(1 << (3+bins))
    original_target = np.zeros_like(target)
    histories = {}
    for bits, rho in branches.items():
        packed_history = sum(bit << j for j, bit in enumerate(bits))
        factor = expected/p if m.selected(bits, event) else (1-expected)/(1-p)
        target[8*packed_history:8*(packed_history+1)] = np.diag(rho).real*factor
        original_target[8*packed_history:8*(packed_history+1)] = np.diag(original_branches[bits]).real
        histories[''.join(map(str, bits))] = {
            'retained_probability': float(np.trace(rho).real),
            'original_cavity2_probability': float(np.trace(original_branches[bits]).real),
            'expected_circuit_probability': float(np.trace(rho).real*factor)}
    name = f'optical_{bins}bin_{str(cutoff).replace(".", "p")}_{event}_r{rounds}'
    body.name = name
    paths = [ROOT / 'qrsm_photon_poc' / p for p in
             ('qrsm_photon.py', 'dilation_feasibility.py', 'multibin_followup/model.py')]
    return Experiment(body, {
        'id': name, 'family': 'optical_retained_instrument', 'bins': bins,
        'event': event, 'rounds': rounds, 'choi_absolute_cutoff': cutoff,
        'physical_parameters': asdict(m.Parameters(n_cavity=2)),
        'instrument': instrument_report,
        'measurement': {'order': 'Qiskit counts: q[n-1] ... q[0]; every logical qubit measured',
                        'system_qubits': [0, 1, 2], 'system_basis': ['cavity', 'emitter', 'defect'],
                        'chronological_flag_qubits': flags,
                        'environment_qubits_per_bin': env_bits,
                        'data_marginal_qubits_lsb_first': [0, 1, 2]+flags,
                        'workspace_qubits': [],
                        'environment_is_not_clean_workspace': True},
        'plain_event_probability': p, 'expected_event_probability': expected,
        'original_cavity2_event_probability': po,
        'retained_vs_original_selected_trace_distance': m.trace_distance(state, original_state),
        'history_reference': histories,
        'original_cavity2_z_marginal': original_target.tolist(),
        'ideal_selected_system_density_real': state.real.tolist(),
        'ideal_selected_system_density_imag': state.imag.tolist(),
        'resources': resources(body), 'source_sha256': source_hashes(paths),
        'scope': ['Digital simulation of the frozen synthetic cavity-2 optical instrument.',
                  'Choi truncation and cavity truncation remain physical-model approximations.',
                  'History/system Z statistics do not establish full quantum-state fidelity.',
                  'Retained environments are essential to circuit reversal; no physical photon is reversed.',
                  'These deep circuits are noise stress tests, not a sensitivity or speedup claim.']}, target)


def build_spatial(style='counter', rounds=0):
    """Shared latent dose + four capped Poisson cells; actual spatial oracle."""
    if style not in ('counter', 'enumerated') or rounds not in (0, 1, 2):
        raise ValueError('Supported spatial styles counter/enumerated, rounds0..2')
    m, q = spatial_modules()
    body = q.circuit(rounds, style)
    # A matched plain control exposes the same14 logical roles as counter r1.
    if style == 'counter' and rounds == 0:
        padded = QuantumCircuit(14)
        padded.compose(body, range(9), inplace=True)
        body = padded
    body = q.compiled(body)
    target = m.joint_probabilities()
    accepted = np.array([m.accepted(i) for i in range(512)])
    p, posterior, _ = m.dp_solution()
    expected = math.sin((2*rounds+1)*math.asin(math.sqrt(p)))**2
    target = target*np.where(accepted, expected/p, (1-expected)/(1-p))
    name = f'spatial2x2_{style}_r{rounds}'
    body.name = name
    paths = [ROOT / 'finals-lithography/followup' / f for f in ('model.py', 'quantum.py')]
    return Experiment(body, {
        'id': name, 'family': 'correlated_spatial_2x2', 'style': style, 'rounds': rounds,
        'config': asdict(m.DEFAULT), 'plain_event_probability': p,
        'expected_event_probability': expected,
        'conditional_low_dose_probability': float(posterior[0]),
        'measurement': {'order': 'Qiskit counts: q[n-1] ... q[0]; every logical qubit measured',
                        'data_marginal_qubits_lsb_first': list(range(9)),
                        'latent_dose_qubit': 0, 'cell_count_qubits_lsb_first': [[1+2*i, 2+2*i] for i in range(4)],
                        'workspace_qubits': list(range(9, body.num_qubits)),
                        'accepted_data_indices': np.flatnonzero(accepted).tolist()},
        'resources': resources(body), 'source_sha256': source_hashes(paths),
        'scope': ['Synthetic correlated2x2 process, not a replacement for the original7x7 model.',
                  'Capping N at3 preserves the score<3 event and every accepted map exactly; it changes unconditional counts.',
                  'Counter style reversibly computes the weighted sum; enumerated style is a small fixed-predicate comparator.',
                  'Exact classical DP and rejection-free conditional sampling solve this finite model efficiently.',
                  'Workspace leakage is reported separately, never silently postselected away.']}, target)


def measured(experiment):
    body = experiment.circuit.copy()
    body.measure_all()
    return body


def exact_reference(experiment):
    """Actual circuit simulation checked against independent channel/DP law."""
    vector = optical_module().statevector(experiment.circuit)
    probabilities = np.abs(vector)**2
    observed = marginal(probabilities, experiment.metadata['measurement']['data_marginal_qubits_lsb_first'])
    error = float(np.max(np.abs(observed-experiment.target_marginal)))
    normalization_error = float(abs(probabilities.sum()-1))
    workspace = experiment.metadata['measurement']['workspace_qubits']
    dirty = float(1-marginal(probabilities, workspace)[0]) if workspace else 0.
    if max(error, normalization_error, abs(dirty)) > 1e-8:
        raise AssertionError(f'Circuit/reference mismatch: {error}, norm{normalization_error}, work{dirty}')
    return probabilities, {'maximum_marginal_error': error, 'normalization_error': normalization_error,
                           'dirty_workspace_probability': dirty, 'tolerance': 1e-8,
                           'independent_reference': 'channel branch recursion' if experiment.metadata['family'].startswith('optical') else 'exact Poisson joint law and weighted-sum DP',
                           'all_checks_passed': True}


def event_mask(metadata):
    width = len(metadata['measurement']['data_marginal_qubits_lsb_first'])
    indices = np.arange(1 << width)
    if metadata['family'] == 'correlated_spatial_2x2':
        return np.isin(indices, metadata['measurement']['accepted_data_indices'])
    bits = [(indices >> (3+j)) & 1 for j in range(metadata['bins'])]
    return (bits[-1] == 1) if metadata['event'] == 'last' else np.all(bits, axis=0)


def score_counts(counts, metadata, target_marginal):
    """Raw all-qubit counts only; no readout correction or workspace filtering.

    Empty selected records yield null conditional estimates, not NaN or invented
    distributions. Wilson intervals concern the raw measured event probability.
    """
    width = metadata['resources']['qubits']
    distribution = np.zeros(1 << width)
    for key, value in counts.items():
        if isinstance(value, bool) or int(value) != value or value < 0:
            raise ValueError('Counts must be nonnegative integers')
        index = int(key.replace(' ', ''), 2) if isinstance(key, str) else int(key)
        if index < 0 or index >= len(distribution):
            raise ValueError('Count key outside logical register')
        distribution[index] += value
    shots = int(distribution.sum())
    if shots == 0:
        raise ValueError('No shots')
    measurement = metadata['measurement']
    data_counts = marginal(distribution, measurement['data_marginal_qubits_lsb_first'])
    mask = event_mask(metadata)
    accepted = int(data_counts[mask].sum())
    p = accepted/shots
    z = 1.959963984540054
    scale = 1+z*z/shots
    center = (p+z*z/(2*shots))/scale
    half = z*math.sqrt(p*(1-p)/shots+z*z/(4*shots*shots))/scale
    target = np.asarray(target_marginal, float)
    conditional_tv = (float(.5*np.abs(data_counts[mask]/accepted-target[mask]/target[mask].sum()).sum())
                      if accepted else None)
    workspace = measurement['workspace_qubits']
    dirty = int(shots-marginal(distribution, workspace)[0]) if workspace else 0
    return {'shots': shots, 'accepted_shots': accepted, 'raw_event_probability': p,
            'raw_event_wilson95': [max(0., center-half), min(1., center+half)],
            'ideal_event_probability': metadata['expected_event_probability'],
            'data_z_distribution_tv': float(.5*np.abs(data_counts/shots-target).sum()),
            'selected_data_z_distribution_tv': conditional_tv,
            'selected_data_z_counts': {str(i): int(data_counts[i]) for i in np.flatnonzero(mask)},
            'dirty_workspace_shots': dirty, 'dirty_workspace_fraction': dirty/shots,
            'correction': 'none; raw counts, no workspace postselection',
            'interpretation': 'Z-distribution discrepancy only, not density-state fidelity; conditional TV is sampling-noise biased.'}
