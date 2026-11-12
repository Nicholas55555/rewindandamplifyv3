"""Separate numerical derivative/uncertainty audit of completed frozen fits.

Does not alter fits or select models using held-out records. Local normal
intervals are reported only for interior positive-curvature solutions, with
global sign degeneracy and small-sample limitations stated explicitly.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import inference_model as m


def hessian(fun,x,h):
    n=len(x); eye=np.eye(n)*h; matrix=np.zeros((n,n)); center=fun(x)
    for i in range(n):
        matrix[i,i]=(fun(x+eye[i])-2*center+fun(x-eye[i]))/h**2
        for j in range(i):
            value=(fun(x+eye[i]+eye[j])-fun(x+eye[i]-eye[j])
                   -fun(x-eye[i]+eye[j])+fun(x-eye[i]-eye[j]))/(4*h*h)
            matrix[i,j]=matrix[j,i]=value
    return matrix


def audit(path):
    row=json.loads(path.read_text(encoding='utf-8')); cfg=row['config']
    seed=int(row['case'].split('_')[1]); controls=row['protocol_controls']
    truth=m.Parameters(**row['generator_parameters']); fitted=m.Parameters(**row['joint_parameters'])
    train=m.sample(truth,controls,cfg['train_records']//len(controls),cfg['bins'],seed,row['detector_dead_bins_truth'])
    digest=hashlib.sha256(b''.join(x.tobytes() for x in train)).hexdigest()
    if digest!=row['training_sha256']:
        raise AssertionError('Training regeneration mismatch')
    x=m.vector(fitted)
    def objective(x):
        return -m.all_logs(train,m.parameters(x,truth),controls,row['detector_dead_bins_fit']).sum()
    value=objective(x)
    if abs(value-row['joint_fit']['best']['negative_loglikelihood'])>1e-7:
        raise AssertionError('Frozen likelihood mismatch')
    out={'case':row['case'],'fit_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'training_regeneration_matches':True,'reproduced_negative_loglikelihood':float(value),
         'parameter_order':list(m.NAMES),'boundary_parameters':row['joint_fit']['best']['boundary_parameters'],
         'derivative_note':'Live L-BFGS-B used jac=None and default absolute finite-difference eps. Its finite_diff_rel_step option did not take effect. This separate audit uses explicit central steps.',
         'uncertainty_scope':'Local approximate likelihood curvature, conditional on family and calibration. Does not cover global aliases, boundaries, model mismatch or optimization uncertainty.',
         'confidence_coverage_calibrated':False,
         'fixed_protocol_sign_alias':row['case'].startswith('fixed_'),
         'profile_note':'One-start nuisance-optimized coarse coupling profile is a diagnostic, not a confidence or identified set.'}
    if np.any(x<.002) or np.any(x>.998):
        out['normal_intervals_available']=False
        out['reason']='At least one fitted parameter is on/near an optimization bound; regular unconstrained normal approximation is not reported.'
    else:
        matrices=[hessian(objective,x,h) for h in (.001,.0005)]
        eig=np.linalg.eigvalsh(matrices[-1])
        discrepancy=np.linalg.norm(matrices[0]-matrices[1])/max(1.,np.linalg.norm(matrices[-1]))
        gradient=[]
        for j in range(5):
            dx=np.eye(5)[j]*.0005
            gradient.append((objective(x+dx)-objective(x-dx))/.001)
        out.update(hessian_scaled_coordinates=matrices[-1].tolist(),eigenvalues=eig.tolist(),
                   central_step_relative_disagreement=float(discrepancy),
                   central_gradient_per_training_record=(np.array(gradient)/cfg['train_records']).tolist())
        regular=eig[0]>0 and discrepancy<.01
        out['normal_intervals_available']=bool(regular)
        if regular:
            covariance=np.linalg.inv(matrices[-1])
            se=np.sqrt(np.diag(covariance))*m.SCALE
            out['local_normal_approximate_95pct_intervals']={name:{'estimate':getattr(fitted,name),'standard_error':float(s),
                'interval':[float(getattr(fitted,name)-1.95996398454*s),float(getattr(fitted,name)+1.95996398454*s)]}
                for name,s in zip(m.NAMES,se)}
            out['intervals_leave_search_bounds']=[name for j,name in enumerate(m.NAMES)
                if out['local_normal_approximate_95pct_intervals'][name]['interval'][0]<m.BOUNDS[j,0]
                or out['local_normal_approximate_95pct_intervals'][name]['interval'][1]>m.BOUNDS[j,1]]
            out['intervals_leave_physical_domain']=[name for name in m.NAMES if name!='defect_detuning'
                and (out['local_normal_approximate_95pct_intervals'][name]['interval'][0]<0
                     or (name=='detector_eta' and out['local_normal_approximate_95pct_intervals'][name]['interval'][1]>1))]
            out['interval_warning']='Intervals crossing physical/search bounds expose weak identification and failure of a global Gaussian approximation. They are not calibrated physical confidence sets; no clipping is used to hide this.'
        else:
            out['reason']='Nonpositive or numerically unstable likelihood curvature.'
    profile=row.get('coupling_profile',[])
    if profile:
        best=min([value]+[r['fit']['best']['negative_loglikelihood'] for r in profile])
        out['profile_diagnostic']=[{'g':r['fixed_g'],'twice_delta_negative_loglikelihood':2*(r['fit']['best']['negative_loglikelihood']-best),
                                   'converged':r['fit']['best']['success']} for r in profile]
        out['profile_beats_unconstrained_fit_by_nats']=max(0.,value-best)
    return out


if __name__=='__main__':
    directory=HERE/'inference_results'
    output=HERE/'parameter_validation_v2';output.mkdir(exist_ok=True)
    for path in sorted(directory.glob('*_dead*_fit*.json')):
        target=output/path.name
        if target.exists():
            previous=json.loads(target.read_text())
            if previous['fit_sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError('Previously audited fit changed')
            continue
        result=audit(path)
        result['audit_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(result['case'],'local_intervals',result['normal_intervals_available'],'boundaries',result['boundary_parameters'],flush=True)
