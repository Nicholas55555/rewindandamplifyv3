"""Read-only integrity/physics checks of the exported logical bundle."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Statevector
from models import aggregated_photon_probabilities,bloch_reference,AtomicConfig

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(folder):
    m=json.loads((folder/'manifest.json').read_text())
    for path,digest in m['source_sha256'].items():assert sha(ROOT/path)==digest,path
    for path,digest in m['artifact_sha256'].items():assert sha(folder/path)==digest,path
    with (folder/'logical.qpy').open('rb') as f:circuits=qpy.load(f)
    refs=np.load(folder/'ideal_probabilities.npz',allow_pickle=False)
    assert len(circuits)==len(m['circuits'])==33
    errors=[]
    for circuit,row in zip(circuits,m['circuits']):
        assert len(circuit.cregs)==1 and circuit.cregs[0].name=='meas'
        for q,instruction in enumerate(circuit.data[-circuit.num_qubits:]):
            assert instruction.operation.name=='measure'
            assert circuit.find_bit(instruction.qubits[0]).index==q
            assert circuit.find_bit(instruction.clbits[0]).index==q
        probs=Statevector.from_instruction(circuit.remove_final_measurements(inplace=False)).probabilities()
        errors.append(float(np.max(abs(probs-refs[row['ideal_probability_key']]))))
        meta=row['metadata'];reference=row['reference']
        if meta['family']=='atomic_finite_pulse':
            b=bloch_reference(meta['detuning_hz'],meta['relative_intensity'],AtomicConfig(**meta['config']))
            p0=float(probs[::2].sum())
            errors.append(abs(p0-(1+b['XYZ'.index(meta['basis'])])/2))
        else:
            actual=aggregated_photon_probabilities(probs,meta['photons_if_prepared'])
            for key,value in reference['occupancy_probabilities'].items():
                errors.append(abs(actual.get(tuple(map(int,key.split(','))),0)-value))
    assert max(errors)<1e-10
    return {'all_checks_passed':True,'circuit_count':len(circuits),
            'maximum_probability_error':max(errors),'source_and_artifact_hashes_passed':True,
            'measurement_wiring_passed':True,'full_statevector_references_passed':True,
            'independent_bloch_and_number_targets_passed':True,
            'manifest_sha256':sha(folder/'manifest.json'),'no_account_or_hardware_access':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path,default=HERE/'bundle_v2')
    print(json.dumps(verify(parser.parse_args().bundle),indent=2))
