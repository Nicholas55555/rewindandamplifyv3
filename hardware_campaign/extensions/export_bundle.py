"""Bounded supplementary QPY export with exact full-Z references."""
import argparse,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
import numpy as np
import qiskit
from qiskit import qpy
from qiskit.quantum_info import Statevector
from adapters import ROOT,specs,compiled

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def worker(out):
    sys.path.insert(0,str(ROOT/'qrsm_photon_poc'))
    from dilation_synthesis import enforce_memory_limit
    guard=enforce_memory_limit(4096)
    started=time.monotonic();circuits=[];rows=[];arrays={};sources={}
    for index,(name,builder,args) in enumerate(specs()):
        begin=time.monotonic();qc,meta,target=builder(*args)
        if qc.num_qubits>20:raise RuntimeError('Full-vector width guard20')
        qc=compiled(qc);qc.name=name
        actual=Statevector.from_instruction(qc).probabilities()
        error=float(np.max(abs(actual-target)))
        if error>1e-9:raise AssertionError((name,error))
        work=meta.get('workspace_qubits',[]);dirty=float(sum(p for i,p in enumerate(actual) if any((i>>q)&1 for q in work)))
        if dirty>1e-10:raise AssertionError('dirty ideal workspace')
        key=f'p{index:03d}';arrays[key]=target
        counts=dict(qc.count_ops());depth=qc.depth();qc.measure_all()
        circuits.append(qc)
        for path in meta['source_paths']:sources[path]=sha(ROOT/path)
        row={'name':name,'index':index,'qpy_file':'logical.qpy','num_qubits':qc.num_qubits,'metadata':meta,
             'reference':{'file':'ideal_probabilities.npz','key':key,'shape':list(target.shape),'basis_order':'q0 is least significant; environment/work included'},
             'ideal_probability_key':key,'generic_compilation':{'basis':['u','cx'],'optimization_level':1,'seed':13,'gate_counts':counts,'depth':depth},
             'validation':{'maximum_probability_error':error,'dirty_workspace_probability':dirty,'all_checks_passed':True},
             'local_build_seconds':time.monotonic()-begin}
        rows.append(row);write(out/'progress.json',{'status':'building','completed':rows})
        print(f'{index+1}/25 {name}: {qc.num_qubits}q {counts.get("cx",0)}CX error{error:.3g}',flush=True)
    with (out/'logical.qpy').open('wb') as f:qpy.dump(circuits,f)
    if (out/'logical.qpy').stat().st_size>50*1024**2:raise RuntimeError('QPY exceeds50MiB shard limit')
    with (out/'logical.qpy').open('rb') as f:loaded=qpy.load(f)
    for a,b in zip(circuits,loaded):
        if a!=b or len(b.cregs)!=1 or b.cregs[0].name!='meas':raise AssertionError('QPY roundtrip')
    np.savez_compressed(out/'ideal_probabilities.npz',**arrays)
    for path in [HERE/'adapters.py',HERE/'export_bundle.py',HERE/'test_adapters.py',HERE/'PROTOCOL.md']:
        sources[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    manifest={'schema':'ra-hardware-bundle-v1','bundle':'coverage_extensions','qpy_file':'logical.qpy',
              'ideal_probabilities_file':'ideal_probabilities.npz','classical_register':'meas','circuits':rows,
              'source_sha256':sources,'artifact_sha256':{p:sha(out/p) for p in ['logical.qpy','ideal_probabilities.npz']},
              'versions':{'python':platform.python_version(),'numpy':np.__version__,'qiskit':qiskit.__version__},
              'all_checks_passed':True,'qpy_roundtrip_all_equal':True,'elapsed_s':time.monotonic()-started,
              'scope':'Supplementary logical controls, no QPU result in this file. Catalogue1024 is the generic cost benchmark; fixed-round history is not full online BBHT; finite-horizon conditioning is approximate.'}
    write(out/'manifest.json',manifest);write(out/'progress.json',{'status':'complete','circuits':len(rows)})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'bundle_v1');parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if args.worker:worker(args.out)
    else:
        if args.out.exists():raise SystemExit('Refusing existing output directory')
        args.out.mkdir(parents=True)
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        start=time.monotonic()
        with (args.out/'build.log').open('w',encoding='utf-8') as log:
            try:
                proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--out',str(args.out.resolve())],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
                status={'status':'completed' if proc.returncode==0 else 'failed','returncode':proc.returncode}
            except subprocess.TimeoutExpired:status={'status':'timeout','returncode':None}
        status.update(elapsed_s=time.monotonic()-start,timeout_s=600,process_memory_limit_mib=4096)
        write(args.out/'build_status.json',status);print(json.dumps(status,indent=2))
        if status['status']!='completed':raise SystemExit(1)
