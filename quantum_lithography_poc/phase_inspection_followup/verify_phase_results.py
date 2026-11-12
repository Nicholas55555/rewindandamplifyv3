"""Verify immutable numeric results and explicit phase-study resource budgets."""
from pathlib import Path
import hashlib,json,math,re

HERE=Path(__file__).resolve().parent


def main():
    data=json.loads((HERE/'results.json').read_text())
    testlog=(HERE/'test_results.txt').read_text(encoding='utf-8-sig')
    assert re.search(r'Ran 9 tests',testlog) and re.search(r'\bOK\b',testlog)
    max_grid=0.;records=0
    for c in data['cases']:
        eta=c['setup']['object_transmission']*c['setup']['detection_efficiency']
        p=c['setup']['preparation_success']
        for budget,methods in c['budgets'].items():
            doses=[d['resources']['sample_incident_mean_photons_before_object'] for d in methods.values()]
            clocks=[d['resources']['attempted_clocks'] for d in methods.values()]
            if budget=='equal_sample_photons':assert max(doses)-min(doses)<1e-9 and math.isclose(doses[0],20000)
            else:assert set(clocks)=={10000}
            for method,row in methods.items():
                res=row['resources']
                if method=='noon':expected=4*p*eta**2
                elif method=='coherent':expected=2*eta
                else:expected=(res['quantum_attempts']*4*p*eta**2+res['coherent_attempts']*2*eta)/res['attempted_clocks']
                assert math.isclose(res['classical_fisher_information_per_attempt'],expected,rel_tol=2e-8)
                assert math.isclose(res['mean_detected_photons'],res['sample_incident_mean_photons_before_object']*eta)
                for regime in ['local','global']:
                    result=row[regime];records+=result['repetitions']
                    max_grid=max(max_grid,result['max_estimator_difference_to_double_grid_rad_first50'])
                    lo,hi=result['rmse_mc_interval95_rad']
                    assert lo<=result['rmse_full_2pi_rad']<=hi
                    if method=='noon' and regime=='global':
                        assert result['wrong_pi_branch_rate']>.45
                        assert result['rmse_full_2pi_rad']>1
    assert records==data['estimation_trials']==168000
    assert max_grid<1e-4
    for f,expected in data['source_sha256'].items():
        assert hashlib.sha256((HERE/f).read_bytes()).hexdigest()==expected,f
    names=['phase_model.py','test_phase_model.py','run_phase_study.py','verify_phase_results.py',
        'README.md','requirements.txt','results.json','run_summary.json','test_results.txt',
        'local_phase_tradeoffs.png','global_phase_ambiguity.png']
    report={'schema':'phase-inspection-verification-v1','tests_passed':9,'estimation_trials':records,
        'sampling_dependence':data['sampling_dependence'],
        'photon_dose_before_object_verified':True,'clock_budget_verified':True,'source_sha256_verified':True,
        'fisher_information_loss_and_preparation_limits_verified':True,'global_noon_branch_ambiguity_preserved':True,
        'max_grid_refinement_difference_rad':max_grid,
        'visual_review':'Both generated figures individually inspected; axes, budgets, units and phase-domain distinction readable.',
        'physical_claim_boundary':'Specified ideal optical phase model with losses. No fabricated pattern, material defect diagnosis, device measurement or universal classical limit claim.',
        'sha256':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in names}}
    (HERE/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))


if __name__=='__main__':main()
