"""Export checked logical circuits and references. Never submit or use accounts."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
from dataclasses import asdict,replace
import numpy as np
import scipy,qiskit
from qiskit import qpy,transpile
from qiskit.quantum_info import Statevector
from models import *

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical_sensor():
    path=ROOT/'laser_sensor_viability/model.py'
    spec=importlib.util.spec_from_file_location('canonical_atomic_source',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module

def export(out):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    circuits=[];rows=[];arrays={};started=time.time();canonical=canonical_sensor()
    cfg=AtomicConfig()
    atomic=[(f'atomic_d{d:+g}_Z',d,1.,cfg,'Z') for d in [-5,-.5,0,.5,5]]
    atomic += [('atomic_shortT2_d+5_Z',5,1.,replace(cfg,t2_s=.02),'Z'),
               ('atomic_power1.1_d+0.5_Z',.5,1.1,cfg,'Z'),
               ('atomic_d+0.5_X',.5,1.,cfg,'X'),('atomic_d+0.5_Y',.5,1.,cfg,'Y')]
    def add(qc,name,metadata,reference):
        qc.name=name
        probs=Statevector.from_instruction(qc).probabilities()
        if abs(probs.sum()-1)>1e-10:raise ArithmeticError('unnormalized reference')
        index=len(rows);key=f'p{index:03d}';arrays[key]=probs
        native=transpile(qc,basis_gates=['u','cx'],optimization_level=1,seed_transpiler=13)
        row={'name':name,'index':index,'qpy_file':'logical.qpy','num_qubits':qc.num_qubits,
             'metadata':metadata,'reference':reference,'ideal_probability_key':key,
             'generic_compilation':{'basis':['u','cx'],'optimization_level':1,'seed':13,
              'gate_counts':dict(native.count_ops()),'depth':native.depth(),
              'scope':'All-to-all generic estimate; not routed hardware cost.'}}
        # Qiskit2.6.1 cannot QPY-roundtrip an undecomposed Isometry instruction.
        # Export its verified generic unitary decomposition, not an opaque gate.
        rows.append(row);circuits.append(measured(native))
    for name,delta,power,c,basis in atomic:
        qc=atomic_circuit(delta,power,c,basis)
        r=bloch_reference(delta,power,c)
        born=(1+r[2])/2
        measured_p=c.readout_01+(1-c.readout_01-c.readout_10)*born
        cc=canonical.Config(t1_s=c.t1_s,t2_s=c.t2_s,preparation_error=c.preparation_error,
                            pulse_s=c.pulse_s,dark_s=c.dark_s)
        canonical_p=float(canonical.ramsey_probability(delta,power,cc))
        if abs(measured_p-canonical_p)>1e-4:raise ArithmeticError('canonical atomic mismatch')
        v,ks,eigs=channel_isometry(atomic_channel(delta,power,c))
        add(qc,name,{'family':'atomic_finite_pulse','detuning_hz':delta,'relative_intensity':power,
                    'basis':basis,'config':asdict(c),'system_qubit':0,'environment_qubits':[1,2],
                    'preparation_environment_qubit':3,'ground_code':1,'excited_code':0,
                    'source':'laser_sensor_viability/model.py','emulation_only':True},
            {'bloch_xyz':r.tolist(),'system_probability_zero_in_measurement_basis':float((1+r['XYZ'.index(basis)])/2),
             'born_excitation_probability':float(born),'canonical_synthetic_readout_probability':float(measured_p),
             'canonical_strang16_probability':canonical_p,'absolute_exact_vs_strang16':abs(measured_p-canonical_p),
             'choi_eigenvalues':eigs.tolist(),'isometry_completeness_error':float(np.linalg.norm(v.conj().T@v-I2))})
    optical=[('noon_phi0',0,.81,'noon',1.),('noon_phi0.35',.35,.81,'noon',1.),
             ('noon_phi_pi4',np.pi/4,.81,'noon',1.),('noon_phi0.35_plus_pi',.35+np.pi,.81,'noon',1.),
             ('noon_eta0.48',.35,.48,'noon',1.),('noon_prep0.1',.35,.81,'noon',.1),
             ('mixture_phi0',0,.81,'mixture',1.),('mixture_phi_pi4',np.pi/4,.81,'mixture',1.)]
    for name,phi,eta,kind,p in optical:
        qc=photon_circuit(2,phi,eta,kind,p)
        ideal=aggregated_photon_probabilities(Statevector.from_instruction(qc).probabilities(),2)
        reference=fock_reference(2,phi,eta,kind,p)
        error=max(abs(ideal.get(k,0)-v) for k,v in reference.items())
        if error>1e-10:raise ArithmeticError('Fock circuit mismatch')
        add(qc,name,{'family':'photon_noon_or_mixture','kind':kind,'photons_if_prepared':2,'phase_rad':phi,
                     'eta':eta,'object_transmission':.9 if eta==.81 else .6,
                     'detection_efficiency':.9 if eta==.81 else .8,'preparation_success':p,
                     'path_qubits':[0,1],'loss_qubits':[2,3],'source_success_qubit':4,
                     'source':'quantum_lithography_poc/phase_inspection_followup/phase_model.py','emulation_only':True,
                     'incident_mean_photons_before_object_per_attempt':2*p},
            {'occupancy_probabilities':{f'{a},{b}':v for (a,b),v in reference.items()},
             'moments':photon_moments(reference),'independent_fock_max_probability_error':error})
    tail=coherent_tail()
    for label,phi in [('phase0.35',.35),('phase0.35_plus_pi',.35+np.pi)]:
        for n in range(1,9):
            qc=photon_circuit(n,phi,.81)
            reference=fock_reference(n,phi,.81)
            ideal=aggregated_photon_probabilities(Statevector.from_instruction(qc).probabilities(),n)
            error=max(abs(ideal.get(k,0)-v) for k,v in reference.items())
            if error>1e-10:raise ArithmeticError('coherent sector Fock mismatch')
            add(qc,f'coherent_{label}_N{n}',{'family':'photon_coherent_sector','kind':'coherent_sector',
                'photons_if_prepared':n,'phase_rad':phi,'eta':.81,'object_transmission':.9,'detection_efficiency':.9,
                'preparation_success':1.,'poisson_weight':tail['weights'][n],'path_qubits':list(range(n)),
                'loss_qubits':list(range(n,2*n)),'source_success_qubit':2*n,
                'incident_photons_before_object_per_sector_attempt':n,'emulation_only':True},
                {'occupancy_probabilities':{f'{a},{b}':v for (a,b),v in reference.items()},
                 'moments':photon_moments(reference),'independent_fock_max_probability_error':error})
    with (out/'logical.qpy').open('wb') as f:qpy.dump(circuits,f)
    np.savez_compressed(out/'ideal_probabilities.npz',**arrays)
    with (out/'logical.qpy').open('rb') as f:loaded=qpy.load(f)
    for qc,row in zip(loaded,rows):
        actual=Statevector.from_instruction(qc.remove_final_measurements(inplace=False)).probabilities()
        if np.max(abs(actual-arrays[row['ideal_probability_key']]))>1e-10:raise ArithmeticError('QPY mismatch')
    sources=[HERE/'models.py',HERE/'export_bundle.py',HERE/'test_models.py',HERE/'PROTOCOL.md',
             ROOT/'laser_sensor_viability/model.py',ROOT/'quantum_lithography_poc/phase_inspection_followup/phase_model.py',
             ROOT/'quantum_lithography_poc/exposure_followup/model.py']
    manifest={'schema':'ra-hardware-bundle-v1','bundle':'optical_controls','qpy_file':'logical.qpy',
        'ideal_probabilities_file':'ideal_probabilities.npz','classical_register':'meas',
        'bit_order':'Integer keys little-endian: classical bitj records logical qubitj; binary strings highest bit first.',
        'circuits':rows,'coherent_sector_accounting':tail,
        'vacuum_sector':{'N':0,'probability':tail['weights'][0],'occupancy':[0,0],'hardware_execution_required':False},
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources},
        'versions':{'python':sys.version.split()[0],'qiskit':qiskit.__version__,'numpy':np.__version__,'scipy':scipy.__version__},
        'validation':{'qpy_roundtrip':True,'all_independent_physics_comparisons_passed':True,'full_z_references_saved':True},
        'scope':'Superconducting circuit emulation of specified atomic/photonic primitives. No actual optical sensor, exposure or phase-inspection experiment; no quantum advantage.',
        'elapsed_s':time.time()-started}
    manifest['artifact_sha256']={p:sha(out/p) for p in ['logical.qpy','ideal_probabilities.npz']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'circuits':len(rows),'qubits':[min(c.num_qubits for c in circuits),max(c.num_qubits for c in circuits)],
                      'max_generic_cx':max(r['generic_compilation']['gate_counts'].get('cx',0) for r in rows),
                      'qpy_bytes':(out/'logical.qpy').stat().st_size,'out':str(out)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'bundle_v2')
    export(parser.parse_args().out)
