import copy,datetime as dt,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from streampulse.fhir_export import *

class ExportTests(unittest.TestCase):
    def setUp(self):
        f=ROOT/'tests/fixtures/fhir';self.daily=read_daily(f/'daily_water.csv');self.forecasts=read_jsonl(f/'forecasts.jsonl');self.alerts=read_jsonl(f/'alerts.jsonl');self.meta=json.loads((ROOT/'data/reference/station_05174000.json').read_text())
    def build(self):return build_bundle(self.daily,self.forecasts,self.alerts,self.meta)
    def fail(self,pattern):
        with self.assertRaisesRegex(ContractError,pattern):self.build()
    def test_deterministic_and_reference_closed(self):
        a=self.build();b=self.build();self.assertEqual(canon(a),canon(b));assert_references(a)
    def test_truthful_replay_and_date_precision(self):
        b=self.build();r=next(e['resource'] for e in b['entry'] if e['resource'].get('device'))
        self.assertEqual(r['issued'],self.forecasts[0]['generated_at']);self.assertEqual(r['extension'][0]['valueDateTime'],self.forecasts[0]['issued_simulated'])
        self.assertEqual(r['effectivePeriod'],{'start':'2025-07-04','end':'2025-07-04'});self.assertNotIn('referenceRange',r)
    def test_communication_subject_absent(self):
        comm=[e['resource'] for e in self.build()['entry'] if e['resource']['resourceType']=='Communication'];self.assertEqual(len(comm),2)
        for r in comm:self.assertNotIn('subject',r)
        a=next(r for r in comm if 'inResponseTo' not in r);self.assertEqual(a['status'],'preparation');self.assertNotIn('sent',a)
    def test_future_observation_rejected(self):self.forecasts[0]['input_obs_dates']=['2025-07-01'];self.fail('input date')
    def test_missing_observation_rejected(self):self.daily.pop('2025-06-24');self.fail('missing input')
    def test_ineligible_observation_rejected(self):self.daily['2025-06-24']['eligible']=False;self.fail('ineligible')
    def test_invalid_interval_rejected(self):self.forecasts[0]['pi90_low_c']=99;self.fail('interval')
    def test_nan_rejected(self):self.forecasts[0]['pred_mean_c']=float('nan');self.fail('finite')
    def test_bool_number_rejected(self):self.forecasts[0]['pred_mean_c']=True;self.fail('finite')
    def test_target_mismatch_rejected(self):self.forecasts[0]['target_date']='2025-07-03';self.fail('target_date')
    def test_naive_issued_rejected(self):self.forecasts[0]['generated_at']='2026-09-29T12:00:00';self.fail('timezone')
    def test_wrong_station_rejected(self):self.forecasts[0]['station_id']='other';self.fail('station')
    def test_index_out_of_range_rejected(self):self.alerts[0]['forecast_refs']=[1];self.fail('forecast_refs')
    def test_negative_index_rejected(self):self.alerts[0]['forecast_refs']=[-1];self.fail('forecast_refs')
    def test_ack_must_be_real_time(self):self.alerts[0]['ack']['at']='2025-07-01T13:00:00Z';self.fail('precedes')
    def test_open_alert_has_no_ack(self):self.alerts[0]['status']='open';self.fail('open alert')
    def test_open_alert_export(self):self.alerts[0]['status']='open';self.alerts[0]['ack']=None;self.assertEqual(sum(e['resource']['resourceType']=='Communication' for e in self.build()['entry']),1)
    def test_escaped_untrusted_note(self):
        self.alerts[0]['ack']['note']='<script>alert(1)</script>'
        ack=next(e['resource'] for e in self.build()['entry'] if 'inResponseTo' in e['resource']);self.assertIn('&lt;script&gt;',ack['text']['div'])
    def test_future_weather_rejected(self):self.forecasts[0]['weather_run_init']='2025-07-02T00:00:00Z';self.fail('initialization')
    def test_weather_requires_run(self):self.forecasts[0]['model_id']='weather_corr_v1';self.fail('requires weather_run')
    def test_operational_label_supported(self):self.forecasts[0]['mode']='operational';self.assertTrue(self.build())
    def test_bad_model_sha(self):self.forecasts[0]['model_version']='<git sha>';self.fail('git SHA')
    def test_watch_not_rederived(self):
        self.forecasts[0]['watch']=True;self.forecasts[0]['p90_reference_c']=99;self.assertTrue(self.build())
    def test_export_cli_equivalent(self):
        f=ROOT/'tests/fixtures/fhir'
        with tempfile.TemporaryDirectory() as td:
            b=export(f/'daily_water.csv',f/'forecasts.jsonl',f/'alerts.jsonl',ROOT/'data/reference/station_05174000.json',Path(td)/'bundle.json');self.assertEqual(b,self.build())

if __name__=='__main__':unittest.main()
