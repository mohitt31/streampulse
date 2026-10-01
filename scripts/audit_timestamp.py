#!/usr/bin/env python3
"""Capture the actual Hub'eau documentation and inspect timezone claims."""
import datetime as dt, hashlib, json,pathlib,re,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];E=ROOT/'reports/audit-evidence';E.mkdir(parents=True,exist_ok=True)
urls={'temperature_page.html':'https://hubeau.eaufrance.fr/page/api-temperature-continu','temperature_openapi.json':'https://hubeau.eaufrance.fr/api/v1/temperature/api-docs'};results=[];schema=None
for filename,url in urls.items():
    now=dt.datetime.now(dt.timezone.utc).isoformat();m={'url':url,'retrieved_at':now}
    try:
        with urllib.request.urlopen(url,timeout=30) as r:raw=r.read();m['status']=r.status
        (E/filename).write_bytes(raw);m['sha256']=hashlib.sha256(raw).hexdigest();m['timezone_terms']={t:bool(re.search(t,raw.decode('utf-8'),re.I)) for t in ['\\bUTC\\b','fuseau','timezone','heure locale']}
        if filename.endswith('.json'):schema=json.loads(raw)
    except Exception as exc:m['error']=str(exc)
    results.append(m)
(E/'timestamp_requests.json').write_text(json.dumps(results,indent=2)+'\n')
properties=(schema or {}).get('definitions',{}).get('Chronique',{}).get('properties',{})
lines=['# Hub\'eau temperature timestamp convention audit','',f'Generated {dt.datetime.now(dt.timezone.utc).isoformat()}.','', '## Ruling: timezone UNVERIFIED','', 'The documentation and Swagger schema inspected do not state whether `date_mesure_temp` / `heure_mesure_temp` use UTC, local civil time, fixed standard time, or a producer-specific clock. The API returns separate date and time fields without UTC offset. This is a finding about the inspected sources, not proof that no producer documentation exists.','', 'Exact requests, retrieval timestamps, HTTP status and SHA-256 hashes are in `audit-evidence/timestamp_requests.json`. Sources:','']
for m in results:lines.append('- '+m['url']+' — '+m['retrieved_at']+'; HTTP '+str(m.get('status'))+'; '+m.get('error','captured'))
lines+=['','## Schema fields','', '```json',json.dumps({k:properties.get(k,'UNVERIFIED: source retrieval failed') for k in ('date_mesure_temp','heure_mesure_temp')},indent=2,ensure_ascii=False),'```','', '## Safest handling','', '- Preserve raw date and source-clock time. Do not append Z or infer Europe/Paris from coordinates.','- Keep the pipeline\'s daily source-calendar `date` unchanged. FHIR raw examples use date-only effectiveDateTime and retain the original hour in a note. Forecast effectivePeriod uses the same date for start and end at date precision: that source calendar day; no midnight UTC boundary is invented.','- Actual generation and acknowledgement timestamps must be explicitly timezone-aware. Simulated issuance remains the contract\'s UTC timestamp and is a separate extension.','- Weather alignment needs producer confirmation or an explicitly declared source-clock assumption plus sensitivity analysis. Do not call it fully verified while unresolved.','- DST-shaped duplicates or yearly counts are not proof of timezone. Do not borrow the separate hydrometry API\'s convention.','- Telemetry availability / publication delay is separate from timestamp convention and remains UNVERIFIED.']
(ROOT/'reports/audit_timestamp.md').write_text('\n'.join(lines)+'\n')
