"""Independent-shot Wilson-based contrasts for frozen raw event counts.

These intervals exclude temporal drift, context-dependent gates/readout and
model error; they are not paired-shot or end-to-end performance guarantees.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analyze import wilson


def difference(k1,n1,k2,n2):
    if min(n1,n2)<=0 or not 0<=k1<=n1 or not 0<=k2<=n2:
        raise ValueError('Valid nonempty binomial samples required')
    p1,p2=k1/n1,k2/n2;low1,high1=wilson(k1,n1);low2,high2=wilson(k2,n2)
    delta=p1-p2
    return {'probability_difference':delta,
            'independent_shot_wilson_based_interval95':[
                max(-1.,delta-math.sqrt((p1-low1)**2+(high2-p2)**2)),
                min(1.,delta+math.sqrt((high1-p1)**2+(p2-low2)**2))],
            'first':{'successes':k1,'shots':n1,'probability':p1},
            'second':{'successes':k2,'shots':n2,'probability':p2},
            'scope':'Independent stationary Bernoulli shots; interval excludes between-circuit drift, calibration uncertainty, hardware context and model error. Increased event yield alone does not imply a correct selected answer.'}


def compare(path1,name1,path2,name2):
    path1,path2=Path(path1),Path(path2)
    analyses=[json.loads(p.read_text(encoding='utf8')) for p in (path1,path2)]
    rows=[]
    for analysis,name in zip(analyses,(name1,name2)):
        selected=[r for r in analysis['rows'] if r['name']==name]
        if len(selected)!=1:raise ValueError('Circuit name missing or ambiguous')
        rows.append(selected[0])
    events=[r['observables']['selected'] for r in rows]
    result=difference(events[0]['successes'],events[0]['shots'],events[1]['successes'],events[1]['shots'])
    result.update(first_name=name1,second_name=name2,
                  selected_history_tv_vs_unsteered=[r['observables']['selected_history_tv_to_unsteered_target'] for r in rows],
                  native_two_qubit_gate_counts=[r['native_two_qubit_gate_count'] for r in rows],
                  input_analysis_sha256=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (path1,path2)],
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first_analysis',type=Path);parser.add_argument('first_name')
    parser.add_argument('second_analysis',type=Path);parser.add_argument('second_name');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.first_analysis,args.first_name,args.second_analysis,args.second_name)
    if args.output.exists():raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
