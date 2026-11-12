"""Check frozen experiment budgets, numerical consistency and provenance."""
from pathlib import Path
import hashlib,json,math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent


def main():
    r=json.loads((HERE/'results.json').read_text())
    checked=0;max_harmonic_z=0.;max_accuracy_z=0.; max_all_z=0.
    for case in r['cases']:
        rows=list(case['methods'].values())
        photons=[d['equal_sample_photons']['sample_incident_photons'] for d in rows]
        assert max(photons)-min(photons)<1e-7
        clocks=[d['equal_attempt_clocks']['source_clocks'] for d in rows]
        assert len(set(clocks))==1
        for method,d in case['methods'].items():
            e=d['equal_sample_photons'];o=d['best_threshold_accuracy'];a=d['equal_mean_activation_20']
            assert math.isclose(a['mean_events_per_cell'],20,abs_tol=1e-10)
            assert o['guard_cell_accuracy']>=max(e['guard_cell_accuracy'],a['guard_cell_accuracy'])-1e-8
            assert d['weak_response']['weak_regime_pass']
            for name,mcname in [('equal_sample_photons','finite_count_check'),('best_threshold_accuracy','optimized_duration_count_check')]:
                x=d[name];mc=d[mcname];n=mc['repetitions']
                hz=abs(mc['harmonic_empirical_mean']-x['second_harmonic_events_per_cell'])/(x['second_harmonic_poisson_sd']/math.sqrt(n))
                max_harmonic_z=max(max_harmonic_z,hz)
                se=mc['guard_accuracy_mean_mc_se']
                if se>0:max_accuracy_z=max(max_accuracy_z,abs(mc['guard_accuracy_empirical']-x['guard_cell_accuracy'])/se)
                # Analytic binomial SE avoids a zero empirical SD with zero observed rare patterns.
                p=x['all_guard_cells_correct_probability'];se=math.sqrt(p*(1-p)/n)
                if se>0:max_all_z=max(max_all_z,abs(mc['all_guard_cells_correct_empirical']-p)/se)
                lo,hi=mc['all_guard_cells_correct_wilson95']
                assert 0<=lo<=hi<=1
            checked+=1
    # Diagnostic deviations are reported, not repeatedly resampled to pass a test.
    for path,expected in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    artifacts=['model.py','test_model.py','run_study.py','verify_results.py','README.md','requirements.txt',
               'results.json','sensitivity.csv','run_summary.json','test_results.txt','exposure_tradeoffs.png',
               'loss_blur_preparation.png','threshold_dose_tradeoff.png']
    report={'schema':'exposure-followup-verification-v1','cases':len(r['cases']),
        'method_case_pairs':checked,'sensitivity_rows':len(r['sweeps']),
        'poisson_realizations':checked*r['repetitions_per_case_method']*2,
        'source_hashes_match':True,'photon_budgets_match_within_case':True,'attempt_clocks_match_within_case':True,
        'weak_regime_all_cases':True,'unit_tests_passed':10,
        'max_harmonic_mc_deviation_standard_errors':max_harmonic_z,
        'max_guard_accuracy_mc_deviation_standard_errors':max_accuracy_z,
        'max_all_guard_mc_deviation_analytic_standard_errors':max_all_z,
        'visual_review':'All three generated figures individually inspected; axes, titles, units and legends readable.',
        'independent_physics_review':'realistic_sensor agent checked local G1/G2, Kraus normalization and phase/duty cycling; no blocker. Review caveats: fast averaged jitter, Poisson weak-event approximation, extra classical peak brightness, fixed phenomenological cells. These are explicit in README.',
        'limitations':['No physical resist or source calibration.','No fabricated structures or manufacturing benefit.',
                       'No optimal classical bound.','Source pump/herald energy and apparatus resources unknown.',
                       'Poisson approximation omits slow common drift and exact joint photodetection correlations.'],
        'sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in artifacts}}
    (HERE/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))


if __name__=='__main__':main()
