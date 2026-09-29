#!/usr/bin/env python3
import collections,datetime as dt,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from check_validation import issues
ROOT=pathlib.Path(__file__).resolve().parents[1];folder=ROOT/'reports/fhir-validation';summary={}
for name in ['positive','missing-performer','wrong-subject-type','missing-run-mode']:
    doc=json.loads((folder/(name+'.json')).read_text());all_i=issues(doc);counts=collections.Counter(i.get('severity') for i in all_i)
    summary[name]={'counts':dict(counts),'expected_failure':name!='positive'}
summary['generated_at']=dt.datetime.now(dt.timezone.utc).isoformat();summary['validator']='6.10.4';summary['fhir']='4.0.1';summary['terminology_server']='https://tx.fhir.org/r4'
positive_doc=json.loads((folder/'positive.json').read_text())
summary['positive_documents']=len(positive_doc.get('entry',[])) if positive_doc.get('resourceType')=='Bundle' else 1
summary['standalone_examples']=len(list((ROOT/'fhir/examples').glob('*.json')))
summary['fixture_bundle_sha256']=hashlib.sha256((ROOT/'tests/fixtures/fhir/bundle.json').read_bytes()).hexdigest()
summary['fixture_resource_count']=len(json.loads((ROOT/'tests/fixtures/fhir/bundle.json').read_text())['entry'])
(folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Validation warnings and informational findings','', 'Official HL7 validator 6.10.4; FHIR 4.0.1; pinned OAH definitions and local snapshot profiles loaded. Terminology server: https://tx.fhir.org/r4.','', '## Positive resources','',f'Errors: {summary["positive"]["counts"].get("error",0)}; fatal: {summary["positive"]["counts"].get("fatal",0)}; warnings: {summary["positive"]["counts"].get("warning",0)}.','', 'Every positive warning is enumerated below. CI rejects any unreviewed warning; profiles must actually resolve.','']
positive=issues(json.loads((folder/'positive.json').read_text()))
for i in positive:
    if i.get('severity')=='warning':lines.append('- '+i.get('details',{}).get('text',i.get('diagnostics','')))
if not any(i.get('severity')=='warning' for i in positive):lines.append('- None.')
lines+=['','## Informational findings','', '- OAH indicator and component-code bindings are **preferred**. StreamPulse intentionally uses its declared local CodeSystem for daily aggregates, predictions, interval bounds, source-quality metadata, and watch flags. These are not official OAH codes; informational preferred-binding notices are expected.','- Contained-resource examples are self-contained solely for standalone validation. The exported collection uses separate, resolvable urn:uuid entries.','- Any further informational messages are retained verbatim in positive.json.','', '## Negative controls','', 'The missing-performer fixture intentionally produces the base best-practice warning `All_observations_should_have_a_performer`, in addition to the required OAH cardinality error. This exact warning is reviewed and allowed only for that negative control. No warning is exempted on positive examples.','']
for name,r in summary.items():
    if not isinstance(r,dict) or name=='positive':continue
    lines.append('- '+name+': '+json.dumps(r['counts'])+'; expected conformance failure, asserted by scripts/check_validation.py.')
lines+=['','A passing fixture establishes encoding/conformance behavior, not model skill, actual message delivery, source sensor quality, or authentication. The fixture forecast, all-zero model SHA, and acknowledgement are explicitly synthetic. Actual Claude pipeline outputs must be exported and validated separately.']
(folder/'WARNINGS.md').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,indent=2))
