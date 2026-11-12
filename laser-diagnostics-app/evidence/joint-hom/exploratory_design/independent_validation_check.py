"""Independent bosonic/HMM replay by the separate reviewing agent.
Portable adaptation changes only ROOT and receipt-output handling.
Original reviewed source SHA256:28a067d30f8a974418e242f82e22316229649b4fa12efb9db13c2abeb8798d20.
"""
import sys,json,hashlib,itertools,math
from pathlib import Path
from dataclasses import replace
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'quantum_dot_bridge/qrsm_hom_followup'
HERE=BASE/'exploratory_design';OUT=HERE/'validation_run'
sys.path.insert(0,str(BASE))
from physical_model import Parameters,bosonic_instrument,gap_superoperator

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
r=read(OUT/'results.json');prov=read(OUT/'provenance.json')
assert r['provenance']==prov
for p,h in prov['source_sha256'].items():assert sha(HERE/p)==h,p
assert sha(OUT/'records.npz')==r['records_sha256']
assert sha(HERE/'design_results.json')==prov['design_results_sha256']
assert len(prov['rng_namespaces'])==len(set(map(tuple,prov['rng_namespaces'])))==73
blocks=np.array(list(itertools.product(range(3),repeat=4)))
raw=np.load(OUT/'records.npz',allow_pickle=False)
maximum=0.
def equal(a,b,tol=2e-11):
    global maximum
    error=float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    maximum=max(maximum,error)
    assert error<tol,(error,tol)
def generator(*ns):return np.random.default_rng(np.random.SeedSequence(20261112047,spawn_key=ns))

def law(p):
    # Independent bosonic CP maps; explicit vectorized density propagation.
    gap=gap_superoperator(p)
    states=[(np.eye(2)/2).reshape(-1,order='F')]
    for t,control in enumerate(r['controls_over_gamma']):
        sym,anti=bosonic_instrument(p,control)
        coin=(1+p.mode_overlap)/2*anti+(1-p.mode_overlap)/2*sym
        bunch=(1+p.mode_overlap)/2*sym+(1-p.mode_overlap)/2*anti
        maps=[(1-p.eta**2)*(sym+anti),p.eta**2*((1-p.e01)*bunch+p.e10*coin),p.eta**2*(p.e01*bunch+(1-p.e10)*coin)]
        states=[m@(gap@state if t else state) for state in states for m in maps]
    result=np.array([(state[0]+state[3]).real for state in states])
    assert result.min()>0 and abs(result.sum()-1)<1e-11
    return result/result.sum()

nominal=Parameters(**r['parameters']);p=law(nominal);q=law(replace(nominal,gap_dephasing=1.))
equal(p,r['exact_nominal_block_law_quantum']);equal(q,r['exact_nominal_block_law_classical'])
counts=[int(generator(1,i).binomial(20000,x)) for i,x in enumerate([.01,.02,.8])]
assert counts==r['calibration']['counts']
estimated=dict(zip(['e01','e10','eta'],np.array(counts)/20000))
assert estimated==r['calibration']['estimated']
fitted=replace(nominal,**estimated);pq=law(fitted);pc=law(replace(fitted,gap_dephasing=1.))
ratio=np.log(pq/pc);exact=np.log(p/q)
train=raw['predictor_training_blocks'];hold=raw['predictor_heldout_blocks']
for data,ns in [(train,(2,)),(hold,(3,))]:
    # Differences at machine roundoff do not affect these discrete draws.
    np.testing.assert_array_equal(data,blocks[generator(*ns).choice(81,size=20000,p=p)])
index_train=train@np.array([27,9,3,1]);index_hold=hold@np.array([27,9,3,1])
emp=np.bincount(index_train,minlength=81)+.5;emp/=emp.sum()
predictors={'physical_coherent_calibrated':pq,'physical_classical_calibrated':pc,'exact_classical_categorical_oracle':p,'saturated_categorical_fit':emp}
for report in r['classical_hmms']:
    model={k:np.array(v) for k,v in report['model'].items()}
    initial=model['initial'];transition=model['transition'];emission=model['emission'][0]
    equal(initial.sum(),1);equal(transition.sum(1),1);equal(emission.sum(1),1)
    # Unscaled, explicit four-step forward calculation, independent of author HMM scorer.
    probs=[]
    for record in blocks:
        state=initial*emission[:,record[0]]
        for observation in record[1:]:state=(state@transition)*emission[:,observation]
        probs.append(state.sum())
    probs=np.array(probs);equal(probs.sum(),1)
    predictors[f'hmm_{report["states"]}']=probs
    equal(np.log(probs[index_train]).sum(),report['training_log_likelihood'],tol=1e-8)
    assert report['start']==int(np.argmax(report['all_start_final_scores']))
    assert report['all_start_iterations']==[200]*10

def interval(values):
    mean=float(np.mean(values));se=float(np.std(values,ddof=1)/np.sqrt(len(values)))
    return mean,[mean-1.95996398454*se,mean+1.95996398454*se]
base=np.log(pq[index_hold])/4
for name,probs in predictors.items():
    saved=r['prediction_scores'][name]
    equal(probs,saved['block_probabilities'])
    values=np.log(probs[index_hold])/4
    equal(values,raw['prediction_'+name])
    for v,key in [(values,'log_score_nats_per_attempted_pair'),(values-base,'paired_gain_vs_calibrated_physical')]:
        mean,ci=interval(v)
        equal(mean,saved[key]['mean']);equal(ci,saved[key]['approximate_interval95'])

def wilson(k,n):
    z=1.959963984540054;p0=k/n;den=1+z*z/n
    c=(p0+z*z/(2*n))/den;d=z*np.sqrt(p0*(1-p0)/n+z*z/(4*n*n))/den
    return [max(0,c-d),min(1,c+d)]

total_records=0;budgets=[]
for j,trial in enumerate(r['power_trials']):
    budget=trial['independent_blocks'];cal=raw[f'blocks{budget}_null_calibration_counts']
    np.testing.assert_array_equal(cal,generator(4,j).multinomial(budget,q,size=2000))
    assert np.all(cal.sum(1)==budget)
    threshold=np.sort(cal@ratio)[1900];equal(threshold,trial['threshold_calibrated'])
    assert trial['attempted_pairs']==4*budget and trial['source_excitations']==8*budget
    total_records+=len(cal)
    for k,row in enumerate(trial['cases']):
        records=raw[f'blocks{budget}_{row["name"]}_counts'];plaw=law(Parameters(**row['true_parameters']))
        np.testing.assert_array_equal(records,generator(5,j,k).multinomial(budget,plaw,size=2000))
        assert records.shape==(2000,81) and np.all(records.sum(1)==budget)
        values=records@ratio;hits=int(np.sum(values>threshold));exacthits=int(np.sum(records@exact>=math.log(4)))
        assert hits==row['flags'] and exacthits==row['exact_nominal_model_log4_flags']
        equal(wilson(hits,2000),row['wilson95']);equal(wilson(exacthits,2000),row['exact_nominal_model_log4_wilson95'])
        equal(values.mean(),row['mean_calibrated_llr'])
        equal(np.mean(records@(blocks>0).sum(1)),row['mean_usable_pairs'])
        total_records+=len(records)
    budgets.append({'blocks':budget,'nominal_flag_rate':trial['cases'][0]['flag_rate'],'null_flag_rate':trial['cases'][1]['flag_rate']})
assert total_records==96000
receipt={'all_checks_passed':True,'reviewer':'independent visual_deck agent','source_sha256':{'review_script':sha(__file__)},
 'input_sha256':{n:sha(OUT/n) for n in ['results.json','records.npz','provenance.json']},
 'checks':['All source/protocol/design hashes and73 unique RNG namespaces.','Independent bosonic density-map propagation of nominal, calibrated and all nuisance four-pair laws.','All40,000 training/prediction blocks and96,000 null/heldout record count vectors replay exactly.','All6 thresholds,42 case flags, exact-log4 flags, Wilson intervals and source budgets independently recounted.','Independent explicit four-step HMM forward scoring; training-only selected starts; all20 starts reached200-iteration cap.','All six prediction laws, per-block scores and paired intervals checked.'],
 'maximum_numeric_difference':maximum,'budgets':budgets,
 'scope':['Prospective simulation conditional on exploratorily selected design, known source model and perfect between-block resets.','Nominal simple-hypothesis power does not certify quantum memory or distinguish all classical nuisance explanations.','All20 HMM starts reaching iteration cap does not establish globally optimal classical fitting.','No optical physical measurement or quantum computational advantage.']}
import argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
if args.output is not None:
    if args.output.exists():raise FileExistsError(args.output)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'all_checks_passed':True,'output':str(args.output) if args.output else None,'maximum_numeric_difference':maximum},indent=2))
