"""Create a separate marginal-only4-pair hardware bundle; no IBM/API access."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from qiskit import ClassicalRegister,qpy
from design import Parameters
from selected_hardware import build,compile_and_verify
from physical_model import json_matrix

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,default=HERE/'hardware_bundle');args=parser.parse_args()
    if args.output_dir.exists():raise FileExistsError(args.output_dir)
    specs=[('selected_four_coherent',[2.]*4,0.),('selected_four_classical',[2.]*4,1.),
           ('passive_four_coherent',[0.]*4,0.),('passive_four_classical',[0.]*4,1.)]
    circuits=[];rows=[];arrays={}
    for index,(name,controls,dephase) in enumerate(specs):
        p=Parameters(theta=3*np.pi/4,gap_dephasing=dephase)
        qc=build(p,controls);compiled,expected,branches,report=compile_and_verify(qc,p,controls)
        compiled.name=name;reg=ClassicalRegister(compiled.num_qubits,'meas');compiled.add_register(reg)
        compiled.measure(range(compiled.num_qubits),reg);circuits.append(compiled)
        key=f'circuit_{index:02d}_ideal_flag_memory_marginal';arrays[key]=expected
        row={'name':name,'index':index,'priority':'selected_design_four_pair' if index<2 else 'passive_negative_control',
             'metadata':qc.metadata,'parameters':asdict(p),'num_qubits':compiled.num_qubits,
             'classical_register':'meas','measurement_qubits':list(range(compiled.num_qubits)),
             'classical_bit_to_logical_qubit':list(range(compiled.num_qubits)),
             'reference_kind':'declared_marginal','reference_marginal_qubits':qc.metadata['flag_qubits']+[0],
             'ideal_z_probabilities_npz_key':key,
             'reference_bit_convention':'The first listed marginal qubit is least significant. Raw Qiskit strings put logicalqubit0 at right. Flag histories below are chronological.',
             'exact_flag_history_probabilities':{''.join(map(str,bits)):float(np.trace(rho).real) for bits,rho in branches.items()},
             'exact_memory_before_basis_rotation':{''.join(map(str,bits)):json_matrix(rho/np.trace(rho).real) for bits,rho in branches.items() if np.trace(rho).real>1e-12},
             'memory_measurement_scope':'Z only; conditional matrix is an ideal reference, not experimentally complete tomography.',
             'generic_compilation':report}
        rows.append(row)
        print(f'{name}: {compiled.num_qubits}qubits, {report["cx_gates"]}CX, MPSerror={report["marginal_max_abs_error"]:.3g}',flush=True)
    args.output_dir.mkdir()
    with (args.output_dir/'logical.qpy').open('wb') as stream:qpy.dump(circuits,stream)
    np.savez_compressed(args.output_dir/'ideal_probabilities.npz',**arrays)
    with (args.output_dir/'logical.qpy').open('rb') as stream:restored=qpy.load(stream)
    assert len(restored)==len(circuits) and all(a==b for a,b in zip(circuits,restored))
    sources=['HARDWARE_EXTENSION.md','selected_hardware.py','export_selected_hardware.py','test_selected_hardware.py','design.py','../physical_model.py','../circuits.py']
    manifest={'schema':'ra-hardware-bundle-v1','reference_extension':'declared-marginal-v1',
              'created_utc':datetime.now(timezone.utc).isoformat(),'study':'Selected four-pair source-control design and passive controls',
              'scope':'Digital emission-mode/HOM-instrument emulation; no optical acquisition, multi-block classifier, physical reset or semiconductor validation.',
              'circuits':rows,'circuit_file':'logical.qpy','reference_file':'ideal_probabilities.npz',
              'source_sha256':{s:digest(HERE/s) for s in sources},
              'artifact_sha256':{s:digest(args.output_dir/s) for s in ['logical.qpy','ideal_probabilities.npz']},
              'submission_status':'Not submitted by this exporter; parent campaign runner owns hardware execution.'}
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('Saved separate selected-design bundle with declared32-entry marginals and successful QPY readback.')


if __name__=='__main__':main()
