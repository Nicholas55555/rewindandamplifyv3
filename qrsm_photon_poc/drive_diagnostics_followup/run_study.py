"""Bounded train/calibrate/holdout study of effective drive schedules."""
from dataclasses import asdict, replace
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
import numpy as np
import scipy
from scipy.special import logsumexp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model as m
sys.path.insert(0, str(HERE.parent / 'diagnostics_baselines'))
from compare import fit_hmm
from refine_replication import refine_hmm

CASES = {
    'stable_source': {},
    'source_step_20pct': {'source': 'step', 'fraction': .2},
    'source_telegraph_20pct': {'source': 'telegraph', 'fraction': .2},
    'source_step_10pct': {'source': 'step', 'fraction': .1},
    'source_telegraph_fast': {'source': 'telegraph', 'fraction': .2, 'switch': .2},
    'stable_source_efficiency_loss': {'nuisance': {'eta_factor': .8}},
    'stable_source_dark_increase': {'nuisance': {'dark_add': .03}},
    'stable_source_emitter_detuning': {'nuisance': {'emitter_detuning': .6}},
    'stable_source_cavity_loss': {'nuisance': {'loss_factor': 1.2}},
    'stable_source_deadtime': {'nuisance': {'dead_bins': 1}},
    'stable_source_afterpulse': {'nuisance': {'afterpulse': .1}},
    'stable_source_combined_detector': {'nuisance': {'eta_factor': .8, 'dark_add': .03, 'afterpulse': .1}},
    'source_step_with_efficiency_loss': {'source': 'step', 'fraction': .2, 'nuisance': {'eta_factor': .8}},
}
MAIN = {'seeds': [620101, 620102, 620103, 620104], 'steps': 96, 'cavity': 4,
        'response_records': 128, 'train_each_class': 128, 'null_calibration': 256,
        'test_each_scenario': 128, 'efficiency_trials': 10000, 'dark_trials': 20000,
        'hmm_starts': 3, 'hmm_iterations': 400, 'bootstrap': 2000, 'alpha': .05}
METHODS = ['physical_history', 'classical_hmm', 'count_contrast']


def native(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, dict): return {k:native(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [native(v) for v in x]
    return x


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(native(value), indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def named_seed(master, purpose):
    """Explicit purpose namespace, mixed by NumPy SeedSequence; no seed offsets."""
    digest = hashlib.sha256(purpose.encode('utf-8')).digest()
    words = np.frombuffer(digest, dtype='<u4').tolist()
    state = np.random.SeedSequence([int(master)]+words).generate_state(2)
    return int(state[0]) | (int(state[1]) << 32)


def all_seed_namespaces(cfg, case_names):
    purposes = ['detector_calibration','hmm/baseline','hmm/source']
    data_sets = ['response','training/baseline','training/step','training/telegraph','threshold'] + ['test/'+name for name in case_names]
    purposes += [name+'/'+stream for name in data_sets for stream in ['measurement','schedule','nuisance']]
    table = [{'pipeline_master':master,'purpose':purpose,'seed':named_seed(master,purpose)}
             for master in cfg['seeds'] for purpose in purposes]
    table.append({'pipeline_master':622222,'purpose':'summary_bootstrap','seed':named_seed(622222,'summary_bootstrap')})
    assert len({x['seed'] for x in table}) == len(table), 'Random stream collision'
    return table


def source_hashes():
    paths = [Path(__file__), HERE/'model.py', HERE/'test_model.py', HERE/'PROTOCOL.md',
             HERE.parent/'qrsm_photon.py', HERE.parent/'followup/inference_model.py',
             HERE.parent/'diagnostics_baselines/compare.py', HERE.parent/'diagnostics_baselines/refine_replication.py']
    return {str(p.relative_to(HERE.parent.parent)): sha(p) for p in paths}


def fit_classical(records, cfg, seed):
    fitted = fit_hmm(records, states=3, starts=cfg['hmm_starts'],
                     max_iter=cfg['hmm_iterations'], seed=seed)
    refined, report = refine_hmm(records, np.array(fitted['initial']),
                                 np.array(fitted['transition']), np.array(fitted['emissions']))
    return {'initial': refined[0], 'transition': refined[1], 'emissions': refined[2],
            'em_fit': fitted, 'refinement': report}


def predict(records, base, fraction, hmm):
    physical = m.physical_predictions(records, base, fraction)
    classical = [m.hmm_prefix(records, a['initial'], a['transition'], a['emissions']) for a in hmm]
    scores = {'physical_history': physical['statistic'], 'classical_hmm': classical[1]-classical[0],
              'count_contrast': m.count_contrast(records)}
    for name in METHODS:
        scores[name][:, :15] = -np.inf
    logs = {'physical_history': physical['log_predictive'],
            'classical_hmm': np.logaddexp(classical[0][:, -1], classical[1][:, -1])-np.log(2.)}
    return scores, logs, physical['estimate']


def outcomes(data, scores, thresholds, estimate, calibrated_drive, true_drive):
    n, steps = data['records'].shape
    latent = data['source_states']
    event = np.any(latent, axis=1)
    onset = np.where(event, np.argmax(latent, axis=1), steps)
    eligible = event & (onset <= steps-32)
    results = {}
    for name, score in scores.items():
        crossed = score > thresholds[name]
        first = np.where(np.any(crossed, axis=1), np.argmax(crossed, axis=1)+1, steps+1)
        alarm = first <= steps
        pre = eligible & alarm & (first <= onset)
        detected = eligible & alarm & (first > onset) & (first <= onset+32)
        delay = np.where(detected, first-onset, 32)
        results[name] = {'alarm': alarm, 'first_alarm': first, 'eligible': eligible,
                         'detected32': detected, 'prealarm': pre,
                         'restricted_delay32': delay, 'no_event': ~event}
    # Convert the inference output to effective drive BEFORE scoring. Truth is
    # used only for evaluation/units, never by a predictor or threshold.
    normalized_estimate = calibrated_drive/true_drive*(1+estimate)-1
    error = normalized_estimate[:, 16:] - data['fraction'][:, 16:]
    zero_error = calibrated_drive/true_drive-1-data['fraction'][:, 16:]
    results['estimation'] = {'bias': error.mean(axis=1), 'mse': (error**2).mean(axis=1),
                             'zero_mse': (zero_error**2).mean(axis=1)}
    results['source_onset'] = onset
    return results


def pipeline(cfg, case_names, seed, index, out):
    started = time.perf_counter()
    truth = m.Parameters(n_cavity=cfg['cavity'])
    rng = np.random.default_rng(named_seed(seed,'detector_calibration'))
    def sample(purpose,n,case):
        return m.generate(truth,n,cfg['steps'],named_seed(seed,purpose+'/measurement'),case,
                          schedule_seed=named_seed(seed,purpose+'/schedule'),nuisance_seed=named_seed(seed,purpose+'/nuisance'))
    eta_count = int(rng.binomial(cfg['efficiency_trials'], truth.detector_eta))
    dark_count = int(rng.binomial(cfg['dark_trials'], 1-np.exp(-truth.dark_rate*truth.dt)))
    eta = (eta_count+.5)/(cfg['efficiency_trials']+1)
    dark = -np.log1p(-(dark_count+.5)/(cfg['dark_trials']+1))/truth.dt
    calibrated = replace(truth, detector_eta=eta, dark_rate=dark)
    response = sample('response',cfg['response_records'],{})['records']
    drive_grid = [1.1, 1.3, 1.5]
    drive_nll = [-m.forward(response, replace(calibrated, drive=x), 0., 'baseline')[0][:, -1].sum() for x in drive_grid]
    calibrated = replace(calibrated, drive=drive_grid[int(np.argmin(drive_nll))])
    baseline = sample('training/baseline',cfg['train_each_class'],{})['records']
    n_half = cfg['train_each_class']//2
    source = np.concatenate([sample('training/'+kind,n_half,CASES[name])['records']
                             for kind,name in zip(['step','telegraph'],['source_step_20pct', 'source_telegraph_20pct'])])
    fraction_grid = [.1, .2, .3]
    fraction_nll = []
    for fraction in fraction_grid:
        a = m.forward(source, calibrated, fraction, 'step')[0][:, -1]
        b = m.forward(source, calibrated, fraction, 'telegraph')[0][:, -1]
        fraction_nll.append(-np.sum(np.logaddexp(a, b)-np.log(2.)))
    fraction = fraction_grid[int(np.argmin(fraction_nll))]
    hmm = [fit_classical(x,cfg,named_seed(seed,'hmm/'+kind)) for kind,x in zip(['baseline','source'],[baseline,source])]
    null = sample('threshold',cfg['null_calibration'],{})['records']
    calibration_scores, _, _ = predict(null, calibrated, fraction, hmm)
    thresholds = {name:m.threshold(np.max(value, axis=1), cfg['alpha']) for name,value in calibration_scores.items()}
    arrays = {'response_records': response, 'training_baseline': baseline, 'training_source': source,
              'null_calibration_records': null}
    for name,value in calibration_scores.items(): arrays['null_maxima__'+name] = np.max(value, axis=1)
    all_outcomes = {}
    for case_index, name in enumerate(case_names):
        data = sample('test/'+name,cfg['test_each_scenario'],CASES[name])
        scores, logs, estimate = predict(data['records'], calibrated, fraction, hmm)
        metric = outcomes(data, scores, thresholds, estimate, calibrated.drive, truth.drive)
        metric['predictive_delta'] = logs['physical_history']-logs['classical_hmm']
        metric['click_count'] = data['records'].sum(axis=1)
        all_outcomes[name] = metric
        for key,value in data.items(): arrays[name+'__'+key] = value
        arrays[name+'__fraction_relative_to_fitted_baseline'] = estimate
        arrays[name+'__effective_drive_estimate'] = calibrated.drive*(1+estimate)
        for method in METHODS:
            arrays[name+'__score__'+method] = scores[method]
            for key,value in metric[method].items(): arrays[name+'__outcome__'+method+'__'+key] = value
        for key,value in metric['estimation'].items(): arrays[name+'__estimate_metric__'+key] = value
        arrays[name+'__predictive_delta'] = metric['predictive_delta']
        print('pipeline', index, name, 'elapsed', round(time.perf_counter()-started, 1), flush=True)
    raw_path = out/f'pipeline_{index}_raw.npz'
    np.savez_compressed(raw_path, **arrays)
    detail = {'seed': seed, 'truth': asdict(truth), 'calibrated_parameters': asdict(calibrated),
              'calibration': {'eta_count': eta_count, 'eta_trials': cfg['efficiency_trials'],
                              'dark_count': dark_count, 'dark_trials': cfg['dark_trials'],
                              'drive_grid': drive_grid, 'drive_negative_loglikelihood': drive_nll},
              'source_training_fraction_grid': fraction_grid, 'source_training_negative_loglikelihood': fraction_nll,
              'selected_fraction': fraction, 'hmm_models': hmm, 'thresholds': thresholds,
              'raw_sha256': sha(raw_path), 'elapsed_seconds': time.perf_counter()-started}
    write(out/f'pipeline_{index}.json', detail)
    return all_outcomes, detail


def aggregate(rows, cfg, case_names):
    rng = np.random.default_rng(named_seed(622222,'summary_bootstrap'))
    def interval(values, mask=None, root=False):
        # Cluster pipeline then independently resample records within each draw.
        numerator = sum(np.sum(v if mask is None else v[s]) for v,s in zip(values, mask or [None]*len(values)))
        denominator = sum(len(v) if mask is None else int(s.sum()) for v,s in zip(values, mask or [None]*len(values)))
        mean = numerator/denominator if denominator else None
        # Equal record budgets permit a vectorized cluster/record bootstrap.
        # This avoids millions of Python loops for the many null-only cells.
        if denominator:
            stacked = np.stack(values)
            clusters = rng.integers(len(values), size=(cfg['bootstrap'],len(values)))
            indices = rng.integers(stacked.shape[1], size=(*clusters.shape,stacked.shape[1]))
            sampled = stacked[clusters[:,:,None],indices]
            selected = np.ones_like(sampled,dtype=bool) if mask is None else np.stack(mask)[clusters[:,:,None],indices]
            counts = selected.sum(axis=(1,2)); totals = (sampled*selected).sum(axis=(1,2))
            draws = totals[counts>0]/counts[counts>0]
            bounds = np.quantile(draws,[.025,.975]).tolist()
        else:
            bounds = [None,None]
        if root:
            mean = np.sqrt(mean) if mean is not None else None
            bounds = [np.sqrt(x) if x is not None else None for x in bounds]
        pipeline_values = [float(np.mean(v if mask is None else v[s])) if (len(v) if mask is None else s.sum()) else None for v,s in zip(values, mask or [None]*len(values))]
        if root: pipeline_values = [np.sqrt(v) if v is not None else None for v in pipeline_values]
        return {'value': mean, 'hierarchical_bootstrap_95': bounds, 'records': denominator,
                'pipeline_values': pipeline_values}
    result = {}
    for case in case_names:
        metrics = [r[case] for r in rows]
        entry = {'methods': {}, 'has_source_change_generator': CASES[case].get('source', 'baseline') != 'baseline'}
        for method in METHODS:
            selected = [x[method] for x in metrics]
            entry['methods'][method] = {
                'record_alarm_fraction': interval([x['alarm'] for x in selected]),
                'no_event_alarm_fraction': interval([x['alarm'] for x in selected], [x['no_event'] for x in selected]),
                'detection_within32': interval([x['detected32'] for x in selected], [x['eligible'] for x in selected]),
                'prealarm_fraction_of_eligible_events': interval([x['prealarm'] for x in selected], [x['eligible'] for x in selected]),
                'restricted_delay32_bins': interval([x['restricted_delay32'] for x in selected], [x['eligible'] for x in selected]),
                'no_event_records': sum(int(x['no_event'].sum()) for x in selected),
                'late_onset_records': sum(int((~x['no_event'] & ~x['eligible']).sum()) for x in selected)}
        entry['physical_fraction_bias'] = interval([x['estimation']['bias'] for x in metrics])
        entry['physical_fraction_rmse'] = interval([x['estimation']['mse'] for x in metrics], root=True)
        entry['zero_change_fraction_rmse'] = interval([x['estimation']['zero_mse'] for x in metrics], root=True)
        entry['physical_minus_hmm_predictive_nats_per_record'] = interval([x['predictive_delta'] for x in metrics])
        entry['mean_binary_clicks'] = interval([x['click_count'] for x in metrics])
        entry['paired_physical_minus_hmm_detection32'] = interval(
            [x['physical_history']['detected32'].astype(float)-x['classical_hmm']['detected32'] for x in metrics],
            [x['physical_history']['eligible'] for x in metrics])
        result[case] = entry
    return result


def cutoff_check():
    cases = {}
    for name in ['baseline', 'step', 'alternating']:
        schedule = np.zeros(96, dtype=int)
        if name == 'step': schedule[24:] = 1
        if name == 'alternating': schedule[16:] = (np.arange(80)//8)%2
        predictions = []
        for cavity in [4,5]:
            p = m.Parameters(n_cavity=cavity); rho = m.init_state(p); values = []
            for s in schedule:
                no,yes,full = m.maps(p, .2*s)
                values.append(np.trace((yes@rho).reshape((4*cavity,4*cavity), order='F')).real)
                rho = full@rho
            predictions.append(np.array(values))
        cases[name] = {'max_abs_probability_difference': float(np.max(np.abs(predictions[0]-predictions[1]))),
                       'mean_abs_probability_difference': float(np.mean(np.abs(predictions[0]-predictions[1]))),
                       'cavity4_probability': predictions[0], 'cavity5_probability': predictions[1], 'schedule': schedule}
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--max-seconds', type=int, default=1800)
    args = parser.parse_args()
    if args.out.exists(): raise FileExistsError('Use a new output directory; never overwrite inspected results')
    args.out.mkdir(parents=True)
    started = time.perf_counter()
    completed = threading.Event()
    def watchdog():
        if not completed.wait(args.max_seconds):
            write(args.out/'timeout.json', {'seconds':args.max_seconds, 'pid':os.getpid(), 'status':'process_timeout'})
            os._exit(124)
    threading.Thread(target=watchdog, daemon=True).start()
    cfg = dict(MAIN)
    case_names = list(CASES)
    if args.smoke:
        cfg.update(seeds=[729901], cavity=2, response_records=16, train_each_class=16,
                   null_calibration=24, test_each_scenario=12, hmm_starts=1, hmm_iterations=30, bootstrap=50)
        case_names = ['stable_source','source_step_20pct','stable_source_efficiency_loss','stable_source_afterpulse']
    provenance = {'config':cfg, 'cases': {k:CASES[k] for k in case_names}, 'source_sha256':source_hashes(),
                  'random_stream_namespaces':all_seed_namespaces(cfg,case_names),
                  'versions':{'python':platform.python_version(), 'numpy':np.__version__, 'scipy':scipy.__version__},
                  'mode':'software_smoke_not_evidence' if args.smoke else 'first_main',
                  'pid':os.getpid(), 'wall_time_limit_seconds':args.max_seconds}
    write(args.out/'provenance_start.json', provenance)
    rows, details = [], []
    for index,seed in enumerate(cfg['seeds']):
        r,d = pipeline(cfg, case_names, seed, index, args.out); rows.append(r); details.append(d)
    result = {'config':cfg, 'cases':aggregate(rows,cfg,case_names), 'pipeline_calibrations':details,
              'method_scope':'Same binary sensor records; all algorithms classical. Known quantum model structure and extra calibration are assumptions, not a matched conventional optical instrument.',
              'interval_scope':'Hierarchical percentile bootstrap across four pipelines and records, conditional on this model family. Only four calibration clusters; coverage not calibrated.',
              'estimation_units':'Effective-drive error divided by true baseline drive (truth used only for scoring). Constant zero-change comparator uses the fitted baseline drive, not the true baseline. Estimates are causal mixture posterior means, not uniquely identified source values.',
              'cutoff_check':None if args.smoke else cutoff_check(),
              'elapsed_seconds':time.perf_counter()-started, 'provenance_sha256':sha(args.out/'provenance_start.json')}
    assert source_hashes() == provenance['source_sha256']
    write(args.out/'results.json', result)
    completed.set()
    print('COMPLETE',args.out,'seconds',round(result['elapsed_seconds'],1),flush=True)


if __name__ == '__main__': main()
