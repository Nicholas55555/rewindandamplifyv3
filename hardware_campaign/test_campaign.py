"""Offline safety/order tests. All cloud methods are inert mocks; no credentials.

Tests exercise the actual campaign guards and persistence paths, not a duplicate
runner. Temporary directories contain only disposable plans and mock results.
"""
from contextlib import redirect_stdout
import io
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import XGate, CXGate, Measure

import campaign


class CampaignUnitTests(unittest.TestCase):
    def test_quota_reserves_other_jobs_and_buffer(self):
        campaign.quota_guard(100, 60, 35)
        for available, cap, reserved in [(100,61,35),(100,0,0),(10,11,0)]:
            with self.assertRaises(RuntimeError):
                campaign.quota_guard(available,cap,reserved)

    def test_quota_fails_closed_on_nonfinite_or_negative_values(self):
        for values in [(float('nan'),1,0),(float('inf'),1,0),(100,float('nan'),0),
                       (100,1,float('nan')),(100,1,-1),(-1,1,0)]:
            with self.subTest(values=values):
                with self.assertRaises((RuntimeError, ValueError)):
                    campaign.quota_guard(*values)

    def test_remaining_requires_authoritative_known_schema(self):
        with self.assertRaises(RuntimeError): campaign.remaining({'some_unrecognized_field':600})

    def test_duplicate_measurement_is_rejected(self):
        qc=QuantumCircuit(2,1);qc.measure(0,0);qc.measure(1,0)
        with self.assertRaises(ValueError): campaign.measurement_map(qc)

    def test_missing_measurement_is_rejected(self):
        qc=QuantumCircuit(2,2);qc.measure(0,0)
        with self.assertRaises(ValueError): campaign.measurement_map(qc)

    def test_independent_wire_gate_after_terminal_measurement_is_valid(self):
        qc=QuantumCircuit(2,2);qc.measure(0,0);qc.x(1);qc.measure(1,1)
        self.assertEqual(campaign.measurement_map(qc),[0,1])
        np.testing.assert_allclose(campaign.measured_probabilities(qc),[0,0,1,0],atol=1e-14)

    def test_reuse_of_measured_quantum_wire_is_rejected(self):
        qc=QuantumCircuit(2,2);qc.measure(0,0);qc.x(0);qc.measure(1,1)
        with self.assertRaises(ValueError): campaign.measurement_map(qc)

    def test_submission_options_have_positive_shots_and_twirling_multiple(self):
        campaign.validate_options(2048,90,'plain')
        campaign.validate_options(2048,90,'suppressed')
        for args in [(0,90,'plain'),(-1,90,'plain'),(2048,0,'plain'),(33,90,'suppressed')]:
            with self.assertRaises(ValueError): campaign.validate_options(*args)

    def test_compaction_preserves_nonidentity_classical_bit_order(self):
        qc=QuantumCircuit(5,2);qc.x(4);qc.h(1);qc.cx(1,3)
        qc.measure(4,0);qc.measure(3,1)
        compact=campaign.compact(qc)
        self.assertEqual(compact.num_qubits,3)
        self.assertEqual(campaign.measurement_map(compact),[2,1])
        np.testing.assert_allclose(campaign.measured_probabilities(compact),[0,.5,0,.5],atol=1e-14)

    def test_calibrated_duration_is_critical_path_not_sum(self):
        target=Target(num_qubits=2)
        target.add_instruction(XGate(),{(0,):InstructionProperties(duration=2.),(1,):InstructionProperties(duration=3.)})
        target.add_instruction(CXGate(),{(0,1):InstructionProperties(duration=5.)})
        target.add_instruction(Measure(),{(0,):InstructionProperties(duration=7.),(1,):InstructionProperties(duration=11.)})
        qc=QuantumCircuit(2,2);qc.x(0);qc.x(1);qc.cx(0,1);qc.measure(range(2),range(2))
        self.assertEqual(campaign.duration_bound(qc,target),19.)

    def test_reference_keys_accommodate_frozen_bundle_schemas(self):
        for row in [{'ideal_probability_key':'a'},{'ideal_z_probabilities_npz_key':'a'},
                    {'reference':{'key':'a'}},{'reference':{'npz_key':'a'}}]:
            self.assertEqual(campaign.ref_key(dict(name='test',**row)),'a')
        with self.assertRaises(ValueError): campaign.ref_key({'name':'missing'})

    def test_lossless_gzip_qpy_preserves_actual_measurement_circuit(self):
        qc=QuantumCircuit(3,2);qc.h(0);qc.cx(0,2);qc.measure(2,0);qc.measure(0,1)
        with tempfile.TemporaryDirectory() as directory:
            plain=Path(directory)/'isa.qpy';compressed=Path(directory)/'isa.qpy.gz'
            campaign.save_qpy(plain,[qc])
            compressed.write_bytes(gzip.compress(plain.read_bytes(),mtime=0))
            self.assertEqual(campaign.load_qpy(compressed),[qc])
            self.assertEqual(campaign.compiled_path(Path(directory),{'compiled_qpy_file':'isa.qpy.gz'}),compressed)

    def test_remote_reconciliation_rejects_multiple_tag_matches(self):
        service=SimpleNamespace(jobs=Mock(return_value=[object(),object()]))
        with self.assertRaises(RuntimeError): campaign.reconcile(service,{'unique_tag':'fixed-test-tag'})
        service.jobs.assert_called_once_with(limit=10,job_tags=['fixed-test-tag'])


class CampaignPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.here=Path(self.temp.name).resolve();self.dest=self.here/'runs'/'test';self.dest.mkdir(parents=True)
        self.plan={'backend':'inert_test_backend','shots':10,'max_execution_time':60,'mode':'plain',
                   'pubs':[{'name':'second_logical','kind':'science','pub_index':0},
                           {'name':'first_logical','kind':'science','pub_index':1}]}
        campaign.dump(self.dest/'plan.json',self.plan)
        self.args=SimpleNamespace(label='test')
        self.patches=[patch.object(campaign,'HERE',self.here),
                      patch.object(campaign,'verify_plan',return_value=self.plan)]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_global_submission_lock_is_exclusive_and_released(self):
        with campaign.submission_lock():
            self.assertTrue((self.here/'submission.lock').exists())
            with self.assertRaises(FileExistsError):
                with campaign.submission_lock():pass
        self.assertFalse((self.here/'submission.lock').exists())

    def test_global_submission_lock_releases_on_failure(self):
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            with campaign.submission_lock():
                raise RuntimeError('synthetic failure')
        self.assertFalse((self.here/'submission.lock').exists())

    def test_selected_clone_preserves_science_circuit_and_all_calibrations(self):
        self.plan.update(compiled_qpy_file='isa.qpy',rep_delay_seconds=.0001,
                         duration_estimate_seconds=.006)
        for i,row in enumerate(self.plan['pubs']):
            row.update(duration_seconds=.0001,measurement_physical_qubits=[4])
        self.plan['pubs'].append({'name':'cal_zero','kind':'calibration','pub_index':2,
                                 'duration_seconds':.0001,'measurement_physical_qubits':[4],
                                 'prepared_bits':[0]})
        circuits=[]
        for i in range(3):
            qc=QuantumCircuit(1,1);qc.ry(.2*i,0);qc.measure(0,0);circuits.append(qc)
        campaign.save_qpy(self.dest/'isa.qpy',circuits)
        campaign.dump(self.dest/'backend_properties.json',{})
        campaign.dump(self.dest/'plan.json',self.plan)
        args=SimpleNamespace(source='test',label='subset',names=['first_logical'],
                             shots=320,cap=90,mode='plain')
        with redirect_stdout(io.StringIO()):campaign.clone_plan(args)
        out=self.here/'runs/subset';plan=campaign.read(out/'plan.json')
        chosen=campaign.load_qpy(campaign.compiled_path(out,plan))
        self.assertEqual(chosen,[circuits[1],circuits[2]])
        self.assertEqual([r['name'] for r in plan['pubs']],['first_logical','cal_zero'])
        self.assertEqual([r['pub_index'] for r in plan['pubs']],[0,1])
        self.assertEqual(plan['pubs'][0]['measurement_physical_qubits'],[4])
        self.assertAlmostEqual(plan['duration_estimate_seconds'],320*2*.0002)
        self.assertEqual(plan['paired_source_plan_sha256'],campaign.digest(self.dest/'plan.json'))

    def test_bundle_checks_nested_source_and_artifact_hashes(self):
        bundle=self.here/'bundle';bundle.mkdir()
        source=self.here/'source.py';source.write_text('frozen source',encoding='utf8')
        artifact=bundle/'logical.qpy';artifact.write_bytes(b'frozen artifact')
        manifest={'artifact_sha256':{'logical.qpy':campaign.digest(artifact)},
                  'circuits':[{'metadata':{'source_sha256':{'source.py':campaign.digest(source)}}}]}
        with patch.object(campaign,'ROOT',self.here):
            self.assertEqual(len(campaign.verify_bundle(bundle,manifest)),2)
            source.write_text('changed source',encoding='utf8')
            with self.assertRaises(RuntimeError): campaign.verify_bundle(bundle,manifest)

    def test_verify_plan_protects_saved_reference_file(self):
        bundle=self.here/'bundle';bundle.mkdir()
        (bundle/'manifest.json').write_text('{}',encoding='utf8')
        (bundle/'logical.qpy').write_bytes(b'logical')
        (bundle/'ideal_probabilities.npz').write_bytes(b'reference')
        (self.dest/'isa.qpy').write_bytes(b'compiled')
        plan={'bundle':'bundle','compiled_qpy_sha256':campaign.digest(self.dest/'isa.qpy'),
              'manifest_sha256':campaign.digest(bundle/'manifest.json'),
              'logical_qpy_sha256':{'logical.qpy':campaign.digest(bundle/'logical.qpy')},
              'reference_file':'ideal_probabilities.npz','reference_sha256':campaign.digest(bundle/'ideal_probabilities.npz')}
        campaign.dump(self.dest/'plan.json',plan)
        # Stop only our verify_plan mock to exercise the actual implementation.
        self.patches[1].stop()
        with patch.object(campaign,'ROOT',self.here):
            campaign.verify_plan(self.dest)
            (bundle/'ideal_probabilities.npz').write_bytes(b'changed reference')
            with self.assertRaises(RuntimeError): campaign.verify_plan(self.dest)

    def test_unresolved_intent_never_blindly_resubmits(self):
        intent={'unique_tag':'inert-test-tag','plan_sha256':campaign.digest(self.dest/'plan.json')}
        campaign.dump(self.dest/'submission_intent.json',intent)
        service=SimpleNamespace(jobs=Mock(return_value=[]))
        with patch.object(campaign,'service',return_value=service):
            with self.assertRaisesRegex(RuntimeError,'[Uu]nresolved|resubmission'):
                campaign.submit(self.args)
        self.assertFalse((self.dest/'job.json').exists())

    def test_existing_remote_intent_reconciles_same_job(self):
        intent={'unique_tag':'inert-test-tag','plan_sha256':campaign.digest(self.dest/'plan.json')}
        campaign.dump(self.dest/'submission_intent.json',intent)
        job=SimpleNamespace(job_id=lambda:'existing-inert-job')
        service=SimpleNamespace(jobs=Mock(return_value=[job]))
        with patch.object(campaign,'service',return_value=service),redirect_stdout(io.StringIO()):
            campaign.submit(self.args)
        self.assertEqual(campaign.read(self.dest/'job.json')['job_id'],'existing-inert-job')

    def test_changed_plan_after_intent_is_rejected(self):
        campaign.dump(self.dest/'submission_intent.json',{'unique_tag':'x','plan_sha256':'wrong'})
        with patch.object(campaign,'service',return_value=Mock()):
            with self.assertRaisesRegex(RuntimeError,'[Pp]lan changed'):
                campaign.submit(self.args)

    def fake_job(self, counts=None, backend_name='inert_test_backend',status='DONE'):
        counts=counts or [{'00':10},{'11':10}]
        class Result(list):pass
        result=Result([SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda c=c:c)),metadata={'test_only':True}) for c in counts])
        result.metadata={'test_only':True}
        backend=SimpleNamespace(name=backend_name,configuration=lambda:SimpleNamespace(simulator=False))
        return SimpleNamespace(status=lambda:status,job_id=lambda:'inert-job',
                               result=Mock(return_value=result),backend=lambda:backend,
                               metrics=lambda:{'test_only':True},usage=lambda:{'test_only':True})

    def fetch_with(self,job):
        campaign.dump(self.dest/'job.json',{'job_id':'inert-job'})
        service=SimpleNamespace(job=lambda _:job)
        with patch.object(campaign,'service',return_value=service),\
             patch.object(campaign,'usage_snapshot',return_value={'usage_remaining_seconds':500}),\
             redirect_stdout(io.StringIO()):
            campaign.fetch(self.args)

    def test_fetch_preserves_randomized_pub_order_and_raw_counts(self):
        self.fetch_with(self.fake_job())
        rows=campaign.read(self.dest/'raw.json')['rows']
        self.assertEqual([r['name'] for r in rows],['second_logical','first_logical'])
        self.assertEqual([r['counts'] for r in rows],[{'00':10},{'11':10}])

    def test_fetch_rejects_shot_mismatch_without_raw_file(self):
        with self.assertRaisesRegex(RuntimeError,'shot count'):
            self.fetch_with(self.fake_job([{'00':9},{'11':10}]))
        self.assertFalse((self.dest/'raw.json').exists())

    def test_fetch_rejects_wrong_backend_without_raw_file(self):
        with self.assertRaisesRegex(RuntimeError,'backend'):
            self.fetch_with(self.fake_job(backend_name='different_backend'))
        self.assertFalse((self.dest/'raw.json').exists())

    def test_fetch_does_not_request_results_of_nonterminal_job(self):
        job=self.fake_job(status='RUNNING');self.fetch_with(job)
        job.result.assert_not_called();self.assertFalse((self.dest/'raw.json').exists())

    def test_fetch_preserves_existing_raw_file(self):
        campaign.dump(self.dest/'raw.json',{'preserve':'exactly'})
        original=(self.dest/'raw.json').read_bytes();job=self.fake_job()
        self.fetch_with(job)
        job.result.assert_not_called();self.assertEqual((self.dest/'raw.json').read_bytes(),original)


if __name__=='__main__':unittest.main()
