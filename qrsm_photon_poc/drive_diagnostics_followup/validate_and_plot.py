"""Recount stored bits, thresholds, first alarms, delay and drive errors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
import io
import importlib.util
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model as m
import run_study as r


def validate(directory):
    result = json.loads((directory/'results.json').read_text())
    provenance = json.loads((directory/'provenance_start.json').read_text())
    assert r.sha(directory/'provenance_start.json') == result['provenance_sha256']
    assert r.source_hashes() == provenance['source_sha256']
    cfg = result['config']
    pooled = {name:{method:[] for method in r.METHODS} for name in result['cases']}
    estimation = {name:[] for name in result['cases']}
    checks = []
    hashes = {}
    for index in range(len(cfg['seeds'])):
        path = directory/f'pipeline_{index}_raw.npz'
        detail_path = directory/f'pipeline_{index}.json'
        detail = json.loads(detail_path.read_text())
        assert r.sha(path) == detail['raw_sha256']
        hashes[path.name] = r.sha(path); hashes[detail_path.name] = r.sha(detail_path)
        with np.load(path) as data:
            for method in r.METHODS:
                maxima = data['null_maxima__'+method]
                expected_rank = int(np.ceil((len(maxima)+1)*.95))
                cut = np.sort(maxima)[expected_rank-1]
                assert abs(cut-detail['thresholds'][method]) < 1e-12
            for name in result['cases']:
                records = data[name+'__records']
                latent = data[name+'__source_states']
                fraction = data[name+'__fraction']
                n, steps = records.shape
                assert records.shape == (cfg['test_each_scenario'],cfg['steps'])
                assert np.all((records==0)|(records==1))
                event = latent.any(axis=1)
                onset = np.where(event, latent.argmax(axis=1), steps)
                eligible = event & (onset <= steps-32)
                for method in r.METHODS:
                    score = data[name+'__score__'+method]
                    crossed = score > detail['thresholds'][method]
                    alarm = crossed.any(axis=1)
                    first = np.where(alarm, crossed.argmax(axis=1)+1, steps+1)
                    detected = eligible & alarm & (first>onset) & (first<=onset+32)
                    pre = eligible & alarm & (first<=onset)
                    delay = np.where(detected, first-onset, 32)
                    for key,expected in {'alarm':alarm,'first_alarm':first,'eligible':eligible,
                                         'detected32':detected,'prealarm':pre,'restricted_delay32':delay,'no_event':~event}.items():
                        np.testing.assert_array_equal(data[name+'__outcome__'+method+'__'+key], expected)
                    pooled[name][method].append({'alarm':alarm, 'detected':detected,'eligible':eligible,'delay':delay,'pre':pre})
                estimated_drive = data[name+'__effective_drive_estimate']
                true_drive = detail['truth']['drive']*(1+fraction)
                error = (estimated_drive-true_drive)/detail['truth']['drive']
                constant_error = (detail['calibrated_parameters']['drive']-true_drive)/detail['truth']['drive']
                expected = {'bias':error[:,16:].mean(axis=1), 'mse':(error[:,16:]**2).mean(axis=1),
                            'zero_mse':(constant_error[:,16:]**2).mean(axis=1)}
                for key,value in expected.items():
                    np.testing.assert_allclose(data[name+'__estimate_metric__'+key], value, atol=1e-14)
                estimation[name].append(expected)
                if 'deadtime' in name:
                    for record,nu_onset in zip(records,data[name+'__nuisance_onset']):
                        assert not np.any(record[nu_onset-1:-1] & record[nu_onset:])
                if not result['cases'][name]['has_source_change_generator']:
                    assert not np.any(latent)
                if name in ['stable_source_afterpulse','stable_source_combined_detector']:
                    assert np.all(records >= data[name+'__pre_afterpulse_clicks'])
                if name.startswith('source_step'):
                    assert np.all(np.diff(latent.astype(int),axis=1)>=0)
            checks.append({'pipeline':index,'raw_hashes_thresholds_onsets_delay_estimation_and_detector_controls':'passed'})
    for name,row in result['cases'].items():
        for method in r.METHODS:
            values=pooled[name][method]
            summary=row['methods'][method]
            alarm=np.concatenate([x['alarm'] for x in values]); eligible=np.concatenate([x['eligible'] for x in values])
            assert abs(alarm.mean()-summary['record_alarm_fraction']['value'])<1e-12
            assert eligible.sum()==summary['detection_within32']['records']
            if eligible.sum():
                for key,summary_key in [('detected','detection_within32'),('pre','prealarm_fraction_of_eligible_events'),('delay','restricted_delay32_bins')]:
                    x=np.concatenate([v[key] for v in values])
                    assert abs(x[eligible].mean()-summary[summary_key]['value'])<1e-12
        for key,summary_key,root in [('bias','physical_fraction_bias',False),('mse','physical_fraction_rmse',True),('zero_mse','zero_change_fraction_rmse',True)]:
            value=np.concatenate([x[key] for x in estimation[name]]).mean()
            if root:value=np.sqrt(value)
            assert abs(value-row[summary_key]['value'])<1e-12
    stream=io.StringIO()
    spec=importlib.util.spec_from_file_location('drive_diagnostics_test_model',HERE/'test_model.py')
    test_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(test_module)
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_module)
    test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    assert test_result.wasSuccessful()
    receipt={'all_checks_passed':True,'source_manifest_matches':True,'results_sha256':r.sha(directory/'results.json'),
             'review_source_sha256':r.sha(Path(__file__)),'artifact_sha256':hashes,'pipeline_checks':checks,
             'summary_metrics_recounted':True,'unit_tests':{'tests_run':test_result.testsRun,'passed':True,'output':stream.getvalue()},
             'scope':'Independent recount from archived bits/scores plus exact unit tests; no refit or threshold changes. Bootstrap coverage and physical model correctness are not proved.'}
    r.write(directory/'validation.json',receipt)
    return result


def plots(directory,result):
    names=result['cases']; source=[n for n in names if names[n]['has_source_change_generator']]
    null=[n for n in names if not names[n]['has_source_change_generator']]
    labels={'stable_source':'Nominal baseline','source_step_20pct':'+20% field step','source_telegraph_20pct':'+20% telegraph',
            'source_step_10pct':'+10% field step','source_telegraph_fast':'Faster telegraph',
            'stable_source_efficiency_loss':'Efficiency loss','stable_source_dark_increase':'More dark counts',
            'stable_source_emitter_detuning':'Emitter detuning','stable_source_cavity_loss':'Cavity-loss drift',
            'stable_source_deadtime':'Detector dead time','stable_source_afterpulse':'Afterpulsing',
            'stable_source_combined_detector':'Combined detector drift','source_step_with_efficiency_loss':'Field step + efficiency loss'}
    colors=['#137177','#cb7435','#6851a1']; legend=['Physical-history model','3-state classical HMM','Count contrast']
    fig,axes=plt.subplots(1,2,figsize=(15,7),gridspec_kw={'width_ratios':[1,1.12]})
    for ax,selection,key,title in zip(axes,[source,null],['detection_within32','record_alarm_fraction'],
                                     ['Source changes: detected within 32 bins','No source change: false source alarms per record']):
        y=np.arange(len(selection))
        for j,method in enumerate(r.METHODS):
            entries=[names[n]['methods'][method][key] for n in selection]
            values=np.array([x['value'] for x in entries])*100
            cis=np.array([x['hierarchical_bootstrap_95'] for x in entries])*100
            ax.barh(y+(j-1)*.22,values,height=.2,label=legend[j],color=colors[j])
            ax.errorbar(values,y+(j-1)*.22,xerr=np.maximum(0,np.vstack([values-cis[:,0],cis[:,1]-values])),fmt='none',color='#222',capsize=2,lw=.8)
        ax.set_yticks(y,[labels[n] for n in selection]);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Percent of specified held-out records');ax.set_title(title,fontsize=12)
        ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    axes[1].axvline(5,color='#444',ls='--',lw=1,label='Nominal 5% target')
    axes[0].legend(loc='lower right',fontsize=9)
    fig.suptitle('Retained-state drive simulation — same observed bits, independently calibrated thresholds',fontsize=14)
    fig.text(.5,.015,'96 arbitrary-time bins. Misses/prealarms are retained. Four-pipeline bootstrap intervals have uncalibrated coverage; no physical-laser validation.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(directory/'drive_detection.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,5.5));selection=list(names);x=np.arange(len(selection))
    ax.bar(x-.18,[names[n]['physical_fraction_rmse']['value'] for n in selection],.36,label='Causal physical-model estimate',color=colors[0])
    ax.bar(x+.18,[names[n]['zero_change_fraction_rmse']['value'] for n in selection],.36,label='Keep calibrated baseline unchanged',color='#859396')
    ax.set_xticks(x,[labels[n] for n in selection],rotation=32,ha='right',fontsize=9)
    ax.set_ylabel('RMS effective-drive error / true baseline drive');ax.set_title('Estimating amplitude is conditional on the model; detector drift can be misattributed')
    ax.legend();ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);fig.tight_layout();fig.savefig(directory/'drive_estimation.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
    result=validate(args.run);plots(args.run,result)
    print(json.dumps({'all_checks_passed':True,'run':str(args.run),'plots':2},indent=2))
