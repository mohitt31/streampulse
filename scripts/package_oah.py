#!/usr/bin/env python3
"""Install only compiled OAH conformance definitions into the local FHIR package cache."""
import json,pathlib,shutil,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
PIN='b907cf0869b59d82d9138b3d147fca66f333d911'
source=ROOT/'vendor/oah/fsh-generated/resources'
cache=pathlib.Path.home()/'.fhir/packages/hl7.eu.fhir.oah#0.1.0-ci-build/package'
cache.mkdir(parents=True,exist_ok=True)
old=cache/'package.json'
if old.exists():
    p=json.loads(old.read_text())
    if p.get('streampulseUpstreamCommit')!=PIN:
        raise SystemExit('Refusing to replace a different OAH cache package; move that package aside explicitly, then rerun.')
resources=[]
for path in source.glob('*.json'):
    r=json.loads(path.read_text())
    if r.get('resourceType') in ('StructureDefinition','CodeSystem','ValueSet'):
        shutil.copyfile(path,cache/path.name);resources.append(path.name)
if not resources:raise SystemExit('No generated OAH definitions; run SUSHI first')
package={'name':'hl7.eu.fhir.oah','version':'0.1.0-ci-build','type':'fhir.ig','canonical':'http://hl7.eu/fhir/ig/oah','fhirVersions':['4.0.1'],'description':'Locally compiled, unchanged OAH definitions at pinned source; not an official published package.','dependencies':{'hl7.fhir.r4.core':'4.0.1','hl7.fhir.uv.xver-r5.r4':'0.1.0'},'streampulseUpstreamCommit':PIN}
old.write_text(json.dumps(package,indent=2)+'\n')
out=ROOT/'fhir/packages';out.mkdir(exist_ok=True)
with tarfile.open(out/'oah-pinned.tgz','w:gz') as tar:
    for name in ['package.json']+sorted(resources):tar.add(cache/name,arcname='package/'+name)
print(f'Installed {len(resources)} pinned OAH definitions at {cache}')
