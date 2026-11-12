"""Reproduce original after-click query and recount archived hardware observations.

No new experiment, fit, hardware submission or physical-defect identification.
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'rewindandamplify-main'
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / 'experiments'))
from qiskit.quantum_info import Statevector
from qrsm_grover.model import QRSM
from qrsm_grover.queries import exact_after_click, loop_circuit
from qrsm_grover.amplify import steered_gamma
from qrsm_grover.hardware import readout_correct
from analyse_hardware import device_flip_rates


def filtered_after_click(model, selected_step=3, future_steps=3):
    """Independent density-matrix propagation, without enumerating histories."""
    k0,k1 = model.kraus()
    rho = np.zeros(k0.shape,complex);rho[0,0]=1
    channel = lambda r:k0@r@k0.conj().T+k1@r@k1.conj().T
    for _ in range(selected_step-1):rho=channel(rho)
    rho=k1@rho@k1.conj().T
    probability=float(np.trace(rho).real)
    rho/=probability
    conditional=[]
    for _ in range(future_steps):
        conditional.append(float(np.trace(k1@rho@k1.conj().T).real))
        rho=channel(rho)
    return probability,np.array(conditional)


def circuit_statistics(circuit, model):
    p=np.abs(Statevector(circuit).data)**2
    index=np.arange(len(p));marked=((index>>(model.n_memory+2))&1)==1
    event_probability=float(p[marked].sum())
    future_offset=circuit.num_qubits-3
    conditional=[float(p[marked&(((index>>(future_offset+j))&1)==1)].sum()/event_probability) for j in range(3)]
    return {'event_probability':event_probability,'conditional_probabilities':conditional,
            'circuit_qubits':circuit.num_qubits}


def main():
    archive=json.loads((PROJECT/'results/e5_inside_loop/noiseless.json').read_text())
    result={'schema_version':1,
            'evidence_type':'Reproduction of original model and archived IBM-surrogate counts; no new device acquisition',
            'event':{'selected_step':3,'lags':[1,2,3],'future_steps':[4,5,6],
                     'meaning':'P(output bit at step3+lag is1 | output bit at step3 is1)',
                     'time_unit':'dimensionless model step; no calibrated physical seconds'},
            'click_definition':'A1 measurement on the modeled output/light ancilla. IBM uses superconducting qubits to represent these roles; this is not a detected optical photon.',
            'models':{},'hardware_jobs':[],
            'scope':['Defect/no-defect are deliberately specified model alternatives, not unknown physical defects discovered on IBM.',
                     'Exact full reflection preserves conditional future distributions; local reflection is approximate.',
                     'Raw and readout-corrected probabilities differ. Correction assumes independent single-qubit readout flips and clips probabilities.',
                     'Hardware layouts, widths and depths differ, so these are combined-design comparisons, not controlled causal estimates.',
                     'No calibrated optical source, source fault or photolithography measurement is present.',
                     'The finite-time conditional probabilities are not a stationary optical g2 measurement.',
                     'No standard-error significance claim or hidden-state tomography is made.']}
    models={'with_hidden_defect':QRSM(),'no_hidden_defect':QRSM(phi=(),zeta=())}
    for model_id,model in models.items():
        p,conditional=filtered_after_click(model)
        enumerated=exact_after_click(model,3,3)
        archived=archive['models']['one defect' if model.k else 'no defect']['exact']
        np.testing.assert_allclose(p,archived['p_click'],atol=1e-14,rtol=0)
        np.testing.assert_allclose(conditional,enumerated['conditional'],atol=1e-14,rtol=0)
        np.testing.assert_allclose(conditional,archived['conditional'],atol=1e-14,rtol=0)
        gamma=steered_gamma(p,model.gamma)
        circuits={}
        for variant,r,reflection,steer in [('plain',0,'full',None),('full_steered',1,'full',gamma),
                                          ('local_steered',1,'memory+last-1',gamma),
                                          ('memory_only_steered',1,'memory',gamma)]:
            c=loop_circuit(model,3,3,r,reflection,steer)
            v=circuit_statistics(c,model)
            v.update({'r':r,'reflection':reflection,'emission_override_at_step3':steer,
                      'max_conditional_error':float(np.max(np.abs(np.array(v['conditional_probabilities'])-conditional)))})
            circuits[variant]=v
        assert circuits['full_steered']['max_conditional_error']<1e-12
        result['models'][model_id]={
            'parameters':{'drive_theta':model.theta,'emission_gamma':model.gamma,
                          'defect_couplings_phi':list(model.phi),'defect_rotations_zeta':list(model.zeta)},
            'original_event_probability':p,'exact_conditional_probabilities':conditional.tolist(),
            'ideal_circuits':circuits}
    for suffix in ['plain','plain2']:
        raw_path=PROJECT/f'results/hardware/raw_{suffix}.json'
        summary_path=PROJECT/f'results/hardware/summary_{suffix}.json'
        raw=json.loads(raw_path.read_text());summary=json.loads(summary_path.read_text())
        saved={x['name']:x for x in summary['rows']}
        rates=device_flip_rates(raw['calibration'])
        job={'source':str(raw_path.relative_to(ROOT)).replace('\\','/'),
             'job_id':raw['meta'].get('job_id'), 'metadata':raw['meta'],'rows':[]}
        for item in raw['experiments']:
            meta=item['meta']
            if meta['kind']!='loop':continue
            model_id='with_hidden_defect' if meta['k'] else 'no_hidden_defect'
            model=models[model_id]
            counts=item['counts'];shots=sum(counts.values())
            selected_bit=model.n_memory+meta['t0']-1
            future_offset=meta['width']-meta['tau']
            selected=0;future=np.zeros(3,dtype=int)
            distribution=np.zeros(2**item['logical_qubits'])
            for bits,count in counts.items():
                index=int(bits.replace(' ',''),2);distribution[index]+=count/shots
                if (index>>selected_bit)&1:
                    selected+=count
                    for j in range(3):future[j]+=count*((index>>(future_offset+j))&1)
            conditional=future/selected
            np.testing.assert_allclose(conditional,saved[item['name']]['raw']['conditional'],atol=1e-14,rtol=0)
            np.testing.assert_allclose(selected/shots,saved[item['name']]['raw']['kept'],atol=1e-14,rtol=0)
            corrected=readout_correct(distribution,[rates[q] for q in item['physical_qubits']])
            indices=np.arange(len(corrected));mask=((indices>>selected_bit)&1)==1
            corrected_kept=float(corrected[mask].sum())
            corrected_conditional=np.array([corrected[mask&(((indices>>(future_offset+j))&1)==1)].sum()/corrected_kept for j in range(3)])
            np.testing.assert_allclose(corrected_conditional,saved[item['name']]['corrected']['conditional'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(corrected_kept,saved[item['name']]['corrected']['kept'],atol=1e-12,rtol=0)
            job['rows'].append({'name':item['name'],'model_id':model_id,
                                'variant':'plain' if meta['r']==0 else 'local_steered',
                                'shots':shots,'raw_selected_count':selected,
                                'raw_future_joint_counts':future.tolist(),
                                'raw_event_probability':selected/shots,
                                'raw_conditional_probabilities':conditional.tolist(),
                                'corrected_event_probability':corrected_kept,
                                'corrected_conditional_probabilities':corrected_conditional.tolist(),
                                'two_qubit_gates':item['two_qubit_gates'],
                                'physical_qubits':item['physical_qubits'],
                                'logical_qubits':item['logical_qubits'],
                                'source_meta':meta})
        result['hardware_jobs'].append(job)
    source_paths=[Path(__file__),PROJECT/'qrsm_grover/model.py',PROJECT/'qrsm_grover/queries.py',
                  PROJECT/'qrsm_grover/amplify.py',PROJECT/'qrsm_grover/hardware.py',
                  PROJECT/'results/e5_inside_loop/noiseless.json']
    source_paths += [PROJECT/f'results/hardware/{prefix}_{suffix}.json' for prefix in ['raw','summary'] for suffix in ['plain','plain2']]
    result['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    result['verified']=True
    destination=Path(__file__).with_name('original_after_click_verification.json')
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'models':result['models'],'hardware_jobs':result['hardware_jobs']},indent=2))
    print('All archived conditional probabilities and selected counts reproduced. Saved '+str(destination))


if __name__=='__main__':main()
