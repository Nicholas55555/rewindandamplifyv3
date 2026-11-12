"""Freeze the original QRSM suite and independent unamplified conditional references."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from qiskit import qpy, transpile
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'rewindandamplify-main'))
from qrsm_grover.hardware import suite, ONE, NONE, Experiment, measured, steer_for
from qrsm_grover.queries import loop_circuit

def main():
    dest = Path(__file__).parent / 'original_bundle_v2'
    dest.mkdir(exist_ok=True)
    if (dest / 'manifest.json').exists():
        raise SystemExit('Immutable bundle already exists')
    experiments = suite()
    for tag, model in [('loop-defect', ONE), ('loop-nodefect', NONE)]:
        for kind in ['full', 'memory']:
            body = loop_circuit(model, 3, 3, 1, kind, steer_for(model, 3))
            experiments.append(Experiment(f'{tag}-{kind}-r1', measured(body),
                dict(kind='loop', group=tag, k=model.k, t0=3, tau=3,
                     reflection=kind, r=1, steer=steer_for(model, 3), width=body.num_qubits)))
    arrays, rows = {}, []
    for i, exp in enumerate(experiments):
        initial = Statevector.from_instruction(exp.circuit.remove_final_measurements(inplace=False))
        exp.circuit = transpile(exp.circuit, basis_gates=['u','cx'], optimization_level=0)
        exported = Statevector.from_instruction(exp.circuit.remove_final_measurements(inplace=False))
        assert initial.equiv(exported)
        p = exported.probabilities()
        assert abs(p.sum()-1) < 1e-10
        key = f'p{i:03d}'
        arrays[key] = p
        meta = exp.meta
        ref = {}
        if meta['kind'] in ['history', 'loop']:
            model = NONE if meta['k'] == 0 else ONE
            t = meta.get('T', meta.get('t0',0)+meta.get('tau',0))
            history_bits=list(range(model.n_memory,model.n_memory+t))
            if meta['kind']=='loop':
                history_bits=list(range(model.n_memory,model.n_memory+meta['t0']))+list(range(exp.circuit.num_qubits-meta['tau'],exp.circuit.num_qubits))
            ref = dict(unsteered_history_probabilities=model.history_probabilities(t).tolist(),
                       memory_qubits=model.n_memory, chronological_history_qubits=history_bits)
        rows.append(dict(name=exp.name,index=i,num_qubits=exp.circuit.num_qubits,
                         metadata=meta,reference=ref,ideal_probability_key=key))
    with (dest/'logical.qpy').open('wb') as f:
        qpy.dump([x.circuit for x in experiments],f)
    with (dest/'logical.qpy').open('rb') as f:
        loaded=qpy.load(f)
    assert all(a.circuit == b for a,b in zip(experiments,loaded))
    np.savez_compressed(dest/'ideal_probabilities.npz',**arrays)
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'rewindandamplify-main/qrsm_grover').glob('*.py'))}
    hashes['hardware_campaign/build_original.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest=dict(schema='ra-hardware-bundle-v1',circuits=rows,source_sha256=hashes,
                  scope='Original gate-model QRSM plus full and memory-only loop controls. Programmed defect models, no unknown real light source diagnosed.',
                  qpy_file='logical.qpy',ideal_probabilities_file='ideal_probabilities.npz')
    for name in ['logical.qpy','ideal_probabilities.npz']:
        manifest[name+'_sha256']=hashlib.sha256((dest/name).read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(circuits=len(rows),max_qubits=max(x.circuit.num_qubits for x in experiments),path=str(dest))))

if __name__=='__main__': main()
