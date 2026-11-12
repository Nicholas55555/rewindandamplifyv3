"""Run deterministic exploratory control scan; never touches frozen main output."""
import argparse
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy
from design import Parameters,distribution,setting,settings

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'design_results.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    sources=['PROTOCOL.md','design.py','test_design.py','run_design.py','../physical_model.py']
    hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in sources}
    begin=time.perf_counter();rows=[]
    for i,(theta,a,label,controls) in enumerate(settings()):
        row=setting(Parameters(theta=theta),controls)
        row.update({'index':i,'pattern':label,'amplitude_over_gamma':a});rows.append(row)
    best=max(rows,key=lambda r:r['score_nats_per_attempted_pair'])
    original=setting(Parameters(),[0.,1.,-1.,0.])
    sensitivity=[]
    for name,base in [('selected',best),('original_prefix',original)]:
        for eta in [1.,.8,.5,.2]:
            p=Parameters(**{**base['parameters'],'eta':eta})
            r=setting(p,base['shift_pattern_over_gamma']);r.update({'design':name,'acquisition':'nominal_confusion'})
            sensitivity.append(r)
        p=Parameters(**{**base['parameters'],'eta':1.,'e01':0.,'e10':0.})
        r=setting(p,base['shift_pattern_over_gamma']);r.update({'design':name,'acquisition':'ideal_detector'})
        sensitivity.append(r)
    errors=[]
    for d in [0.,1.]:
        p=Parameters(**{**best['parameters'],'gap_dephasing':d})
        errors.append(float(np.max(abs(distribution(p,best['shift_pattern_over_gamma'])-distribution(p,best['shift_pattern_over_gamma'],True)))))
    result={'schema':'qrsm-hom-exploratory-design-v1','created_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'Deterministic model-based exploration after weak main result; no held-out samples or empirical data used.',
            'source_sha256':hashes,'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
            'runtime_s':time.perf_counter()-begin,'enumerated_settings':len(rows),'selected':best,'original_prefix':original,
            'all_settings':rows,'loss_sensitivity':sensitivity,'independent_bosonic_max_probability_errors':errors,
            'power_scope':'Independent four-pair blocks with perfectly reset I/2 environment, known acquisition parameters. Bound is sufficient, not necessary; normal estimate is approximate. Reset time/fidelity/control energy not priced.',
            'outcome_order':'lexicographic four-tuples of 0=no pair,1=bunch,2=coincidence'}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output),'theta':best['theta_radians'],'pattern':best['shift_pattern_over_gamma'],
                      'selected_information':best['information'],'original_information':original['information'],
                      'runtime_s':result['runtime_s']},indent=2))


if __name__=='__main__':main()
