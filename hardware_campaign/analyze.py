"""Offline, raw-first analysis of immutable real-hardware campaign results.

No service or account calls. Z probabilities test a measurement distribution,
not full state fidelity. Independent readout inversion is a secondary sensitivity
analysis: its projected estimates are not confidence intervals.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from functools import lru_cache

import numpy as np
from scipy.stats import binom

import campaign

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'feasibility'))
from adapters import marginal, score_counts as feasibility_score


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sparse_counts(counts, width):
    """Parse without allocating the Hilbert-space dimension (supports29q+)."""
    result = {}
    for key, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
            raise ValueError('Counts must be nonnegative integers')
        text = key.replace(' ', '') if isinstance(key, str) else None
        index = int(text, 16 if text.startswith('0x') else 2) if text is not None else int(key)
        if not 0 <= index < (1 << width):
            raise ValueError('Count key outside measured logical register')
        result[index] = result.get(index, 0)+int(value)
    if sum(result.values()) <= 0:
        raise ValueError('Empty counts')
    return result


def counts_array(counts, width):
    if width > 20:
        raise ValueError('Full count array capped at20qubits; use sparse marginal projection')
    result = np.zeros(1 << width, dtype=np.int64)
    for index,value in sparse_counts(counts,width).items():result[index]=value
    return result


def sparse_marginal_counts(counts, width, qubits):
    if len(qubits) > 20 or len(set(qubits)) != len(qubits) or any(q<0 or q>=width for q in qubits):
        raise ValueError('Invalid or oversized reference marginal')
    result=np.zeros(1 << len(qubits),dtype=np.int64)
    for index,value in sparse_counts(counts,width).items():
        packed=sum(((index >> q)&1) << j for j,q in enumerate(qubits))
        result[packed]+=value
    return result


def wilson(successes, shots):
    if shots == 0:
        return None
    p = successes/shots; z = 1.959963984540054; den = 1+z*z/shots
    center = (p+z*z/(2*shots))/den
    radius = z*math.sqrt(p*(1-p)/shots+z*z/(4*shots**2))/den
    return [max(0., center-radius), min(1., center+radius)]


def probability_stat(probability, shots=None):
    result = {'probability': float(probability)}
    if shots is not None:
        successes = int(round(probability*shots))
        result.update(successes=successes, shots=shots, wilson95=wilson(successes, shots))
    return result


def tv(a, b):
    return float(.5*np.abs(np.asarray(a)-np.asarray(b)).sum())


def ideal_sampling_tv(target, shots):
    """Exact E[TV(empirical,p)] for multinomial shots, via binomial marginals.

    E|X-np|=2np(1-p) P[Bin(n-1,p)=floor(np)]. No Monte Carlo/tuned floor.
    """
    p = np.asarray(target, float)
    if shots < 1 or np.min(p) < 0 or not np.isfinite(p).all() or abs(p.sum()-1) > 1e-8:
        raise ValueError('Invalid distribution or shot count')
    # Exact statevector arrays can sum to1 plus floating-point roundoff.
    p = np.clip(p/p.sum(), 0., 1.)
    return float(np.sum(p*(1-p)*binom.pmf(np.floor(shots*p), shots-1, p)))


def conditional(distribution, mask):
    p = float(np.asarray(distribution)[mask].sum())
    return p, np.asarray(distribution)[mask]/p if p > 0 else None


def original_observables(probabilities, row, ideal, shots=None):
    meta = row['metadata']; kind = meta['kind']
    if kind == 'echo':
        return {'kind': 'echo', 'all_zero_return': probability_stat(probabilities[0], shots),
                'ideal_all_zero_return': float(ideal[0]), 'repeats': meta['repeats'],
                'scope': 'Return-to-zero circuit check; not reversal of a previously measured optical field.'}
    if kind == 'catalog':
        from qrsm_grover.search import demo_catalog, tokens_of, tokenise, classical_scores
        catalog = demo_catalog(meta['N'])
        query = tokenise(meta['query'], set().union(*(tokens_of(n) for n in catalog)))
        scores = classical_scores(catalog, query); top = scores >= scores.max()-1e-12
        return {'kind': 'catalog', 'classical_tokens': query,
                'top_indices': np.flatnonzero(top).tolist(),
                'top_entries': [catalog[i] for i in np.flatnonzero(top)],
                'top_match': probability_stat(float(probabilities[top].sum()), shots),
                'ideal_top_match_probability': float(ideal[top].sum()),
                'classical_full_catalog_scan_required_to_compile_oracle': True}
    qubits = row['reference']['chronological_history_qubits']
    history = marginal(probabilities, qubits); logical = marginal(ideal, qubits)
    unsteered = np.asarray(row['reference']['unsteered_history_probabilities'], float)
    indices = np.arange(len(history))
    if kind == 'loop':
        selected_step = meta['t0']; mask = ((indices >> (selected_step-1)) & 1) == 1
    elif meta['question'].startswith('click at step '):
        selected_step = int(meta['question'].split()[-1]); mask = ((indices >> (selected_step-1)) & 1) == 1
    elif meta['question'] == 'any click':
        selected_step = None; mask = indices != 0
    else:
        raise ValueError('Unrecognized original predicate; refuse guessed decoding')
    p, after = conditional(history, mask)
    pi, ideal_after = conditional(logical, mask)
    pu, original_after = conditional(unsteered, mask)
    kept = int(round(p*shots)) if shots is not None else None
    result = {'kind': kind, 'chronological_history_qubits': qubits,
              'event': 'click at step '+str(selected_step) if selected_step else 'any click',
              'selected': probability_stat(p, shots), 'logical_ideal_selected_probability': pi,
              'unsteered_selected_probability': pu, 'history_tv_to_logical_ideal': tv(history, logical),
              'selected_history_tv_to_logical_ideal': tv(after, ideal_after) if after is not None else None,
              'selected_history_tv_to_unsteered_target': tv(after, original_after) if after is not None else None,
              'logical_ideal_selected_history_bias_vs_unsteered': tv(ideal_after, original_after),
              'history_probabilities': history.tolist(),
              'scope': 'Conditional history probabilities only; additional accepted shots do not imply a correct conditional answer.'}
    if kind == 'loop':
        future = []
        for step in range(meta['t0']+1, meta['t0']+meta['tau']+1):
            bit = ((indices >> (step-1)) & 1) == 1
            value = float(history[mask & bit].sum()/p) if p > 0 else None
            stat = probability_stat(value, kept) if value is not None else {'probability': None, 'successes': 0, 'shots': 0, 'wilson95': None}
            future.append({'step': step, 'raw_or_secondary_conditional': stat,
                           'unsteered_target': float(unsteered[mask & bit].sum()/pu),
                           'logical_ideal_target': float(logical[mask & bit].sum()/pi)})
        result['future_clicks_after_selected_click'] = future
    return result


def dot_observables(probabilities, row, ideal, shots=None, reference_qubits=None):
    meta = row['metadata']; flags = meta['flag_qubits']
    remap = {q:i for i,q in enumerate(reference_qubits)} if reference_qubits is not None else None
    if remap is not None:flags=[remap[q] for q in flags]
    distribution = marginal(probabilities, flags); target = marginal(ideal, flags)
    histories = {}
    for packed in range(len(distribution)):
        history = ''.join(str((packed >> i) & 1) for i in range(len(flags)))
        histories[history] = {'observed': probability_stat(distribution[packed], shots),
                              'ideal_probability': float(target[packed])}
    result = {'kind': meta['kind'], 'flag_history_tv': tv(distribution, target), 'histories': histories}
    if meta['kind'] == 'frozen_classical_pair_memory_benchmark':
        interval = wilson(int(round(distribution[1]*shots)), shots) if shots is not None else None
        result.update(raw_swap_overlap_estimate=float(1-2*distribution[1]),
                      ideal_overlap=meta['expected_overlap'],
                      raw_swap_overlap_interval95=[1-2*interval[1],1-2*interval[0]] if interval else None,
                      scope='Digital two-photon overlap benchmark; no unique microscopic cause identified.')
        return result
    memory = remap[meta['memory_qubit']] if remap is not None else meta['memory_qubit']
    joint = marginal(probabilities, [memory]+flags)
    expected_joint = marginal(ideal, [memory]+flags)
    for packed in range(len(distribution)):
        history = ''.join(str((packed >> i) & 1) for i in range(len(flags)))
        p = distribution[packed]; n = int(round(p*shots)) if shots is not None else None
        zero = float(joint[2*packed]/p) if p > 0 else None
        stat = probability_stat(zero, n) if zero is not None else {'probability': None, 'successes': 0, 'shots': 0, 'wilson95': None}
        histories[history]['conditional_memory_zero'] = stat
        histories[history]['ideal_conditional_memory_zero'] = float(expected_joint[2*packed]/target[packed]) if target[packed] > 1e-12 else None
        histories[history]['conditional_memory_pauli'] = 2*zero-1 if zero is not None else None
        ci = stat.get('wilson95')
        histories[history]['conditional_memory_pauli_interval95'] = [2*ci[0]-1, 2*ci[1]-1] if ci else None
    result['memory_measurement_basis'] = meta['memory_readout_basis']
    result['scope'] = 'Raw conditional single-memory-qubit Pauli measurement in the declared basis. Hardware readout noise is separate from synthetic optical acquisition noise.'
    return result


@lru_cache(None)
def original_history_target(steps):
    from qrsm_grover.model import QRSM
    return QRSM().history_probabilities(steps)


def extension_observables(probabilities,row,ideal,shots=None):
    meta=row['metadata'];family=meta['family'];indices=np.arange(len(probabilities))
    if family in ('catalog_cost_1024','semantic_catalog16'):
        marked=meta['marked_indices'] if family=='catalog_cost_1024' else [meta['target_index']]
        return {'kind':family,'selected':probability_stat(float(probabilities[marked].sum()),shots),
                'logical_ideal_selected_probability':float(ideal[marked].sum()),
                'selected_indices':marked,'scope':meta['scope']}
    data=meta['data_qubits'] if family=='independent_contact' else meta['history_qubits']
    observed=marginal(probabilities,data);target=marginal(ideal,data);history_indices=np.arange(len(observed))
    if family=='independent_contact':
        mask=np.isin(history_indices,meta['marked_data_indices'])
        original_after=np.asarray(meta['conditional_data_target'])
    else:
        mask=((history_indices>>(meta['steps']-1))&1)==1
        original=original_history_target(meta['steps']);original_after=original[mask]/original[mask].sum()
    p,after=conditional(observed,mask);pi,ideal_after=conditional(target,mask)
    work=meta['workspace_qubits']
    dirty=float(1-marginal(probabilities,work)[0]) if work else 0.
    result={'kind':family,'selected':probability_stat(p,shots),'logical_ideal_selected_probability':pi,
            'data_tv_to_logical_ideal':tv(observed,target),
            'selected_data_tv_to_logical_ideal':tv(after,ideal_after) if after is not None else None,
            'selected_data_tv_to_original_unsteered_target':tv(after,original_after) if after is not None else None,
            'logical_ideal_selected_bias_vs_original':tv(ideal_after,original_after),
            'workspace_dirty':probability_stat(max(0.,dirty),shots),
            'workspace_postselection_applied':False,'scope':meta['scope']}
    if 'ideal_conditional_history_bias_vs_original_tv' in meta:
        if abs(result['logical_ideal_selected_bias_vs_original']-meta['ideal_conditional_history_bias_vs_original_tv'])>1e-8:
            raise ValueError('Canonical conditional-target mismatch')
    return result


def load_optical_analyzer():
    folder = HERE/'optical_controls'
    old_path = sys.path[:]; old_model = sys.modules.get('models')
    try:
        sys.path.insert(0, str(folder))
        spec = importlib.util.spec_from_file_location('_campaign_optical_count_models', folder/'models.py')
        model = importlib.util.module_from_spec(spec); sys.modules[spec.name] = model; spec.loader.exec_module(model)
        sys.modules['models'] = model
        spec = importlib.util.spec_from_file_location('_campaign_optical_count_analysis', folder/'analyze_counts.py')
        module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        if old_model is None: sys.modules.pop('models', None)
        else: sys.modules['models'] = old_model


def calibration_summary(raw_rows):
    controls = {r['name']: r for r in raw_rows if r['kind'] == 'calibration'}
    errors = {}; diagnostics = []
    for name, label in [('cal_zero', 'e01'), ('cal_one', 'e10')]:
        if name not in controls: continue
        row = controls[name]; mapping = row['measurement_physical_qubits']
        counts = sparse_counts(row['counts'], len(mapping)); shots = sum(counts.values())
        for bit, physical in enumerate(mapping):
            p1 = sum(value for index,value in counts.items() if (index >> bit)&1)/shots
            error = p1 if label == 'e01' else 1-p1
            errors.setdefault(str(physical), {})[label] = probability_stat(error, shots)
    for name, row in controls.items():
        mapping = row['measurement_physical_qubits']; counts = sparse_counts(row['counts'], len(mapping)); shots = sum(counts.values())
        indices=np.array(list(counts),dtype=np.uint64)
        probabilities=np.array(list(counts.values()),dtype=float)/shots; individual = []
        error_bits = []
        for bit, physical in enumerate(mapping):
            prepared = row['prepared_bits'][bit]
            is_error = (((indices >> bit) & 1) != prepared).astype(float)
            error_bits.append(is_error)
            actual = float(probabilities@is_error)
            fit = errors.get(str(physical), {}).get('e01' if prepared == 0 else 'e10', {}).get('probability')
            individual.append({'physical_qubit': physical, 'observed_error': actual,
                               'independent_fit_error': fit,
                               'residual': actual-fit if fit is not None else None})
        covariances = [float(probabilities@(error_bits[i]*error_bits[j])-(probabilities@error_bits[i])*(probabilities@error_bits[j]))
                       for i in range(len(mapping)) for j in range(i)]
        diagnostics.append({'name': name, 'per_qubit': individual,
                            'maximum_absolute_pair_error_covariance': max(map(abs, covariances), default=0.)})
    return {'independent_bit_error_estimates': errors, 'pattern_diagnostics': diagnostics,
            'scope': 'Preparation-plus-readout controls, not a pure readout channel measurement. Wilson intervals condition on stationary independent shots; pattern residuals/covariances are descriptive.'}


def secondary_readout_inverse(probabilities, physical_qubits, calibration):
    corrected = np.asarray(probabilities, float).copy(); conditions = []
    for bit, physical in enumerate(physical_qubits):
        rates = calibration['independent_bit_error_estimates'].get(str(physical), {})
        if set(rates) != {'e01', 'e10'}:
            return None, {'status': 'unavailable', 'reason': 'Missing matching physical-qubit calibration'}
        e01, e10 = rates['e01']['probability'], rates['e10']['probability']
        matrix = np.array([[1-e01,e10],[e01,1-e10]])
        if 1-e01-e10 <= .05:
            return None, {'status': 'unavailable', 'reason': 'Ill-conditioned assignment estimate'}
        conditions.append(float(np.linalg.cond(matrix)))
        corrected = np.einsum('ij,ajb->aib', np.linalg.inv(matrix), corrected.reshape(-1,2,1 << bit)).reshape(-1)
    negative = float(-corrected[corrected < 0].sum())
    mass = float(corrected.sum()); unprojected = corrected.copy()
    corrected = np.maximum(corrected, 0); corrected /= corrected.sum()
    return corrected, {'status': 'secondary_sensitivity_only', 'negative_mass_before_projection': negative,
                       'mass_before_projection': mass, 'projection_l1_change': float(np.abs(corrected-unprojected).sum()),
                       'maximum_single_bit_assignment_condition_number': max(conditions, default=1.),
                       'interval': 'none; not a confidence interval or uncertainty-corrected estimator',
                       'assumptions': ['Independent stationary per-bit assignment channel estimated from all-zero/all-one controls.',
                                       'Calibration includes preparation errors; gate errors and correlated/context-dependent readout are not removed.',
                                       'Negative entries clipped and distribution renormalized; this nonlinear projection is biased.',
                                       'Calibration uncertainty and temporal drift are not propagated. Raw estimates remain primary.']}


def analyze_run(directory, output=None):
    directory = Path(directory).resolve(); plan = campaign.verify_plan(directory)
    raw_path = directory/'raw.json'; raw = read(raw_path)
    if raw['plan_sha256'] != sha(directory/'plan.json') or raw['backend'] != plan['backend'] or raw['status'].upper() != 'DONE':
        raise ValueError('Raw result does not match immutable completed plan')
    if raw.get('submitted_dry_run') is not False or plan.get('simulator') is not False:
        raise ValueError('Not an explicitly recorded real hardware run')
    if raw['job_id'] != read(directory/'job.json')['job_id']:
        raise ValueError('Raw result job identity mismatch')
    if len(raw['rows']) != len(plan['pubs']): raise ValueError('PUB count mismatch')
    for expected, observed in zip(plan['pubs'], raw['rows']):
        for key in ('name','kind','pub_index','measurement_physical_qubits'):
            if expected[key] != observed[key]: raise ValueError('Raw PUB order/metadata mismatch')
        if observed.get('bundle_index') != expected.get('bundle_index'): raise ValueError('Bundle index mismatch')
        count = sparse_counts(observed['counts'], len(observed['measurement_physical_qubits']))
        if sum(count.values()) != plan['shots'] or observed['shots'] != plan['shots']: raise ValueError('Raw shot count mismatch')
    bundle = ROOT/plan['bundle']; manifest = read(bundle/'manifest.json')
    declared = {r['index']: r for r in manifest['circuits']}
    calibration = calibration_summary(raw['rows']); rows = []; optical_scores = []
    optical = load_optical_analyzer()
    reference_file = bundle/plan.get('reference_file','ideal_probabilities.npz')
    with np.load(reference_file, allow_pickle=False) as references:
        for observed in raw['rows']:
            if observed['kind'] != 'science': continue
            row = declared[observed['bundle_index']]
            if row['name'] != observed['name']: raise ValueError('Science name/index mismatch')
            width = observed['logical_qubits']; reference_qubits=row.get('reference_marginal_qubits')
            if reference_qubits != observed.get('reference_marginal_qubits'):
                # Older full-reference plans omit the optional field entirely.
                if reference_qubits is not None:raise ValueError('Plan/reference marginal wiring mismatch')
            count = (sparse_marginal_counts(observed['counts'],width,reference_qubits)
                     if reference_qubits is not None else counts_array(observed['counts'], width))
            shots = int(count.sum()); probabilities = count/shots
            ideal = references[campaign.ref_key(row)]
            if ideal.shape != probabilities.shape or np.min(ideal) < 0 or not np.isfinite(ideal).all() or abs(ideal.sum()-1) > 1e-8:
                raise ValueError('Invalid exact reference')
            meta = row['metadata']; family = meta.get('family', meta.get('kind'))
            item = {'name': row['name'], 'bundle_index': row['index'], 'pub_index': observed['pub_index'],
                    'family': family, 'shots': shots, 'logical_qubits': width,
                    'native_two_qubit_gate_count': sum(v for k,v in observed['gate_counts'].items() if k in ('cx','cz','ecr')),
                    'compiled_depth': observed['depth'], 'circuit_duration_seconds': observed['duration_seconds']}
            if reference_qubits is None:
                item.update(raw_full_z_tv=tv(probabilities,ideal),
                            ideal_multinomial_expected_full_z_tv_at_these_shots=ideal_sampling_tv(ideal,shots))
            else:
                item.update(reference_marginal_qubits=reference_qubits,
                            raw_reference_marginal_z_tv=tv(probabilities,ideal),
                            ideal_multinomial_expected_reference_marginal_tv_at_these_shots=ideal_sampling_tv(ideal,shots),
                            full_z_reference_available=False)
            if family in ('history','loop','catalog','echo'):
                item['observables'] = original_observables(probabilities,row,ideal,shots)
            elif family in ('optical_retained_instrument','correlated_spatial_2x2'):
                item['observables'] = feasibility_score(observed['counts'],meta,row['reference']['target_data_z_marginal'])
            elif 'flag_qubits' in meta:
                item['observables'] = dot_observables(probabilities,row,ideal,shots,reference_qubits)
            elif family in ('independent_contact','catalog_cost_1024','semantic_catalog16','qrsm_fixed_round_history','bounded_rewind'):
                item['observables']=extension_observables(probabilities,row,ideal,shots)
            elif family in ('atomic_finite_pulse','photon_noon_or_mixture','photon_coherent_sector'):
                item['observables'] = optical.score_counts(observed['counts'],row)
                optical_scores.append(item['observables'])
            else:
                raise ValueError('Unrecognized family; refuse guessed analysis')
            correction_wires=(observed['measurement_physical_qubits'] if reference_qubits is None else
                              [observed['measurement_physical_qubits'][q] for q in reference_qubits])
            corrected, info = secondary_readout_inverse(probabilities,correction_wires,calibration)
            item['secondary_independent_readout'] = info
            if corrected is not None:
                info['full_z_tv' if reference_qubits is None else 'reference_marginal_z_tv'] = tv(corrected,ideal)
                if family in ('history','loop','catalog','echo'):
                    info['observables'] = original_observables(corrected,row,ideal)
                elif 'flag_qubits' in meta:
                    info['observables'] = dot_observables(corrected,row,ideal,reference_qubits=reference_qubits)
                elif family in ('independent_contact','catalog_cost_1024','semantic_catalog16','qrsm_fixed_round_history','bounded_rewind'):
                    info['observables']=extension_observables(corrected,row,ideal)
            rows.append(item)
    result = {'schema':'ra-offline-hardware-analysis-v1','run':directory.name,'backend':raw['backend'],'job_id':raw['job_id'],
              'source_sha256':{'hardware_campaign/analyze.py':sha(__file__),
                               'hardware_campaign/feasibility/adapters.py':sha(HERE/'feasibility/adapters.py'),
                               'hardware_campaign/optical_controls/analyze_counts.py':sha(HERE/'optical_controls/analyze_counts.py')},
              'input_sha256':{'plan.json':sha(directory/'plan.json'),'raw.json':sha(raw_path),
                              'manifest.json':sha(bundle/'manifest.json'),'reference_npz':sha(reference_file)},
              'calibration':calibration,'rows':rows,'raw_quantum_usage':raw.get('usage'),'raw_job_metrics':raw.get('metrics'),
              'interpretation':['Raw estimates are primary; every submitted science circuit is retained.',
                                'More accepted events can be produced by noise without preserving the selected answer.',
                                'Full-Z and conditional TVs include shot noise and are not quantum-state fidelities.',
                                'Expected multinomial full-Z TV is a model-based sampling benchmark, not a confidence bound.',
                                'Wilson intervals are marginal binomial intervals, not simultaneous coverage or physical-model uncertainty.',
                                'Independent readout inversion is secondary, biased after projection, and excludes calibration uncertainty.',
                                'Superconducting model execution does not validate physical optical sensors, quantum-dot devices or wafer performance.'],
              'immutable_artifacts_verified_before_analysis':True}
    if 'coherent_sector_accounting' in manifest:
        result['coherent_sector_aggregation'] = optical.aggregate_coherent_sector_scores(optical_scores,manifest['circuits'],manifest['coherent_sector_accounting'])
    target = Path(output) if output else directory/'analysis.json'
    if target.exists(): raise FileExistsError('Refusing to overwrite an analysis; choose a versioned output')
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(); result=analyze_run(args.run,args.output)
    print(json.dumps({'run':result['run'],'science_rows':len(result['rows']),'job_id':result['job_id']},indent=2))
