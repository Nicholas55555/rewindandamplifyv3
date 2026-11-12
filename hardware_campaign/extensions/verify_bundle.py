"""Offline integrity and semantic replay of the frozen extension bundle."""
import hashlib,json
from pathlib import Path
import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Statevector
from adapters import ROOT,specs

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(folder=HERE/'bundle_v1'):
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['source_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in manifest['artifact_sha256'].items():assert sha(folder/name)==digest,name
    with (folder/'logical.qpy').open('rb') as f:circuits=qpy.load(f)
    maximum=0.;rows=[]
    with np.load(folder/'ideal_probabilities.npz',allow_pickle=False) as arrays:
        for row,qc,(name,builder,args) in zip(manifest['circuits'],circuits,specs(),strict=True):
            assert row['name']==qc.name==name
            assert qc.num_qubits==row['num_qubits'] and len(qc.cregs)==1 and qc.cregs[0].name=='meas'
            wiring={qc.find_bit(x.clbits[0]).index:qc.find_bit(x.qubits[0]).index for x in qc.data if x.operation.name=='measure'}
            assert wiring==dict(enumerate(range(qc.num_qubits)))
            _,metadata,target=builder(*args)
            assert metadata==row['metadata']
            saved=arrays[row['ideal_probability_key']]
            np.testing.assert_allclose(saved,target,rtol=0,atol=1e-13)
            actual=Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities()
            error=float(np.max(abs(actual-target)));maximum=max(maximum,error)
            assert error<1e-9
            rows.append({'name':name,'maximum_probability_error':error})
    return {'all_checks_passed':True,'circuits':len(rows),'maximum_probability_error':maximum,
            'manifest_sha256':sha(folder/'manifest.json'),'rows':rows,
            'scope':'Offline logical verification only; no native hardware or optical result.'}

if __name__=='__main__':print(json.dumps(verify(),indent=2))
