"""Ensure a crashed validator cannot pass by reusing a previous run's JSON reports."""
import json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]

@unittest.skipUnless((ROOT/'tools/validator_cli.jar').exists(), 'Run validate_fhir.sh to install the pinned validator first')
class ValidationRunnerTests(unittest.TestCase):
    def run_failure(self, allow_first=False):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            for d in ['scripts','tools','fhir/fsh-generated/resources','fhir/examples','reports/fhir','reports/fhir-validation']: (root/d).mkdir(parents=True,exist_ok=True)
            for f in ['validate_fhir.sh','check_validation.py']:shutil.copyfile(ROOT/'scripts'/f,root/'scripts'/f)
            (root/'tools/validator_cli.jar').symlink_to(ROOT/'tools/validator_cli.jar')
            (root/'fhir/fsh-generated/resources/StructureDefinition-streampulse-forecast-observation.json').write_text('{}')
            (root/'reports/fhir/bundle.json').write_text('{}')
            (root/'reports/fhir-validation/positive.json').write_text(json.dumps({'resourceType':'OperationOutcome','issue':[]}))
            (root/'reports/fhir-validation/missing-performer.json').write_text(json.dumps({'resourceType':'OperationOutcome','issue':[{'severity':'error','details':{'text':'Observation.performer minimum required = 1'}}]}))
            stub=root/'stub-java.sh'
            if allow_first:
                stub.write_text('#!/usr/bin/env bash\nif [[ ! -f called ]]; then\n  touch called\n  printf \'%s\\n\' \'{"resourceType":"OperationOutcome","issue":[]}\' > reports/fhir-validation/positive.json\n  exit 0\nfi\nexit 1\n')
            else:stub.write_text('#!/usr/bin/env bash\nexit 1\n')
            stub.chmod(0o755)
            env=dict(os.environ,SP_JAVA=str(stub),SP_PYTHON=sys.executable)
            p=subprocess.run(['bash','scripts/validate_fhir.sh'],cwd=root,env=env,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            expected='missing-performer' if allow_first else 'positive'
            self.assertFalse((root/f'reports/fhir-validation/{expected}.json').exists(),p.stdout+p.stderr)
    def test_crashed_positive_cannot_reuse_old_success(self):self.run_failure()
    def test_crashed_negative_cannot_reuse_old_expected_error(self):self.run_failure(True)
if __name__=='__main__':unittest.main()
