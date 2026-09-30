#!/usr/bin/env python3
"""Fail closed on validator results, including unresolved claimed profiles and unreviewed warnings."""
import argparse,json,pathlib,re

def issues(value):
    if value.get('resourceType')=='OperationOutcome':return value.get('issue',[])
    if value.get('resourceType')=='Bundle':return [i for e in value.get('entry',[]) for i in issues(e.get('resource',{}))]
    raise ValueError('Expected OperationOutcome or Bundle of outcomes')

def main():
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--negative',choices=['missing-performer','wrong-subject-type','missing-run-mode','field-check-missing-unit']);a=p.parse_args()
    data=json.loads(pathlib.Path(a.path).read_text());all_i=issues(data)
    errors=[i for i in all_i if i.get('severity') in ('error','fatal')]
    warnings=[i for i in all_i if i.get('severity')=='warning']
    if any(i.get('severity')=='fatal' for i in all_i):
        raise SystemExit('Fatal validator issue; never an acceptable negative-control result')
    for i in all_i:
        msg=i.get('details',{}).get('text','')+' '+i.get('diagnostics','')
        if any(s in msg.lower() for s in ['has not been checked','unknown profile','could not be found','unable to resolve reference']):
            raise SystemExit('Unresolved conformance/reference evidence: '+msg)
    if a.negative:
        text='\n'.join(json.dumps(i) for i in errors)
        patterns={'missing-performer':r'performer','wrong-subject-type':r'(subject|Location|location-oah)','missing-run-mode':r'(runMode|run-mode)','field-check-missing-unit':r'Observation\.value\[x\]\.unit: minimum required = 1, but only found 0'}
        if not errors or not re.search(patterns[a.negative],text,re.I):
            raise SystemExit('Negative control did not fail for intended reason: '+a.negative)
    elif errors:
        for i in errors:print(json.dumps(i))
        raise SystemExit(f'{a.path}: {len(errors)} validation errors')
    # The missing-performer control deliberately also violates the base best-practice rule.
    # Review only that exact message ID for that one negative control; never exempt positives.
    unreviewed=[]
    for i in warnings:
        ids={e.get('valueCode') for e in i.get('extension',[]) if e.get('url')=='http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id'}
        expected=(a.negative=='missing-performer' and ids=={'All_observations_should_have_a_performer'})
        if not expected:unreviewed.append(i)
    if unreviewed:
        for i in unreviewed:print(json.dumps(i))
        raise SystemExit(f'{a.path}: {len(unreviewed)} unreviewed warnings')
    print(f'{a.path}: {len(errors)} errors, {len(warnings)} warnings, {len(all_i)-len(errors)-len(warnings)} informational; '+('expected negative PASS' if a.negative else 'PASS'))
if __name__=='__main__':main()
