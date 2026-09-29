#!/usr/bin/env python3
"""Reproduce StreamPulse's bounded API audits; Python 3.11, standard library only."""
import argparse, collections, concurrent.futures, datetime as dt, hashlib, json, math, pathlib, time, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
E=ROOT/'reports/audit-evidence'
UTC=dt.timezone.utc

def fetch(url, path, delay=0):
    if delay: time.sleep(delay)
    start=dt.datetime.now(UTC).isoformat(); req=urllib.request.Request(url,headers={'User-Agent':'StreamPulse-hackathon-data-audit/1.0'})
    meta={'url':url,'retrieved_at':start}
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            raw=r.read();meta.update(status=r.status,sha256=hashlib.sha256(raw).hexdigest(),headers={k:v for k,v in r.headers.items() if k.lower() in ('retry-after','x-ratelimit-remaining','content-type')})
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return json.loads(raw),meta
    except Exception as exc:
        meta.update(error=str(exc),status=getattr(exc,'code',None));return None,meta

def water():
    logs=[];years=[];all_rows=[]
    url='https://hubeau.eaufrance.fr/api/v1/temperature/station?code_station=05174000&size=1'
    d,m=fetch(url,ROOT/'data/reference/station_05174000.json');logs.append(m)
    for y in range(2010,2026):
        url=f'https://hubeau.eaufrance.fr/api/v1/temperature/chronique?code_station=05174000&date_debut_mesure={y}-01-01&date_fin_mesure={y}-12-31&size=20000&fields=code_station,date_mesure_temp,heure_mesure_temp,resultat,code_qualification,code_unite,symbole_unite'
        rows=[];page=1;expected=None;ok=True
        while url:
            d,m=fetch(url,E/f'water/{y}-{page}.json',1);logs.append(m)
            if d is None:ok=False;break
            expected=d.get('count');rows+=d['data'];url=d.get('next');page+=1
        times=[dt.datetime.fromisoformat(x['date_mesure_temp']+'T'+x['heure_mesure_temp']) for x in rows]
        counts=collections.Counter(times); conflicts=sum(len({x['resultat'] for x in rows if x['date_mesure_temp']+'T'+x['heure_mesure_temp']==t.isoformat()})>1 for t,n in counts.items() if n>1)
        rec={'year':y,'reported_count':expected,'rows':len(rows),'unique_timestamps':len(counts),'duplicate_rows':len(rows)-len(counts),'conflicting_timestamps':conflicts,'first':min(times).isoformat() if times else None,'last':max(times).isoformat() if times else None,'complete_download':ok and len(rows)==expected,'qualification_counts':dict(collections.Counter(str(x['code_qualification']) for x in rows))}
        years.append(rec);all_rows+=rows;print('water',y,len(rows),flush=True)
    ts=sorted({dt.datetime.fromisoformat(x['date_mesure_temp']+'T'+x['heure_mesure_temp']) for x in all_rows});gaps=[]
    for a,b in zip(ts,ts[1:]):
        hours=(b-a).total_seconds()/3600
        if hours>1:gaps.append({'previous_record':a.isoformat(),'next_record':b.isoformat(),'elapsed_hours':hours,'missing_hourly_slots':int(hours)-1 if hours.is_integer() else None,'first_missing_expected':(a+dt.timedelta(hours=1)).isoformat(),'last_missing_expected':(b-dt.timedelta(hours=1)).isoformat()})
    gaps.sort(key=lambda x:x['elapsed_hours'],reverse=True)
    (E/'water_requests.json').write_text(json.dumps(logs,indent=2));(E/'water_summary.json').write_text(json.dumps({'years':years,'largest_gaps':gaps[:30]},indent=2))
    lines=['# Hub\'eau station 05174000: 2010–2025 audit','',f'Audit generated {dt.datetime.now(UTC).isoformat()}. Exact URLs, retrieval timestamps, HTTP status and SHA-256: `audit-evidence/water_requests.json`. Raw responses: `audit-evidence/water/`.','', 'Counts describe returned records, not independently verified sensor accuracy. Times below remain source clock values; timezone UNVERIFIED.','', '| Year | API count | Downloaded | Unique timestamps | Duplicate rows | First | Last | Complete download |','|---|---:|---:|---:|---:|---|---|---|']
    for r in years:lines.append(f"| {r['year']} | {r['reported_count']} | {r['rows']} | {r['unique_timestamps']} | {r['duplicate_rows']} | {r['first']} | {r['last']} | {r['complete_download']} |")
    lines+=['','## Largest internal gaps','', 'Expected hourly slots are a descriptive assumption, not proof the instrument was scheduled hourly throughout. Boundary censoring before the first/after the last record is not counted as an internal gap.','', '| Last record before gap | First record after gap | Missing expected interval | Missing hourly slots |','|---|---|---|---:|']
    for g in gaps[:15]:lines.append(f"| {g['previous_record']} | {g['next_record']} | {g['first_missing_expected']} → {g['last_missing_expected']} | {g['missing_hourly_slots']} |")
    lines+=['','See machine-readable summary for qualification and duplicate-conflict counts. Do not discard a whole partial year: retain eligible uninterrupted windows. API qualification `4` is non-qualified, not independently validated.']
    (ROOT/'reports/audit_hubeau_counts.md').write_text('\n'.join(lines)+'\n')

def weather():
    first=dt.date(2024,3,14);last=dt.date(2025,8,21);dates=[];d=first
    while d<=last:dates.append(d);d+=dt.timedelta(days=7)
    if dates[-1]!=last:dates.append(last)
    # Boundary probes distinguish "first sampled" from an alleged exhaustive first date.
    dates=[first-dt.timedelta(days=1)]+dates
    logs=[]
    for day in dates:
        url=f'https://single-runs-api.open-meteo.com/v1/forecast?latitude=43.512148&longitude=1.387766&hourly=temperature_2m&models=ecmwf_ifs&run={day}T00:00&forecast_days=8&timezone=GMT'
        data,m=fetch(url,E/f'weather/{day}.json',2);m['run_date']=str(day);m['boundary_probe']=day<first
        if data:
            h=data.get('hourly',{});times=h.get('time',[]);vals=h.get('temperature_2m',[]);expected=[(dt.datetime.combine(day,dt.time())+dt.timedelta(hours=i)).isoformat(timespec='minutes') for i in range(192)]
            m.update(n_times=len(times),n_values=len(vals),non_null=sum(isinstance(v,(int,float)) and math.isfinite(v) for v in vals),time_start=times[0] if times else None,time_end=times[-1] if times else None,exact_192_hour_axis=times==expected,unit=data.get('hourly_units',{}).get('temperature_2m'),utc_offset_seconds=data.get('utc_offset_seconds'))
            m['eight_full_days']=m['exact_192_hour_axis'] and len(vals)==192 and m['non_null']==192 and m['unit']=='°C' and m['utc_offset_seconds']==0
        else:m['eight_full_days']=False
        logs.append(m);print('weather',day,m.get('status'),m.get('non_null'),flush=True)
    (E/'weather_requests.json').write_text(json.dumps(logs,indent=2));sample=[m for m in logs if not m['boundary_probe']];good=[m for m in sample if m['eight_full_days']];failed=[m for m in sample if not m['eight_full_days']]
    lines=['# Open-Meteo Single Runs weekly coverage audit','',f'Generated {dt.datetime.now(UTC).isoformat()}. Model `ecmwf_ifs`; coordinates 43.512148, 1.387766; `temperature_2m`; 00 UTC; `forecast_days=8`; `timezone=GMT`.','',f'{len(sample)} sampled dates from {first} to {last}; weekly cadence anchored at {first}, plus endpoint if necessary. One earlier boundary probe. Requests were serial with at least 2 seconds between completion and the next request (maximum 0.5 requests/second; actual rate lower). No automatic retries.','',f'First sampled full run: {good[0]["run_date"] if good else "NONE"}. Full runs: {len(good)}/{len(sample)}. Exact earliest available date across unsampled history: UNVERIFIED. Every intervening daily run: UNVERIFIED.','',f'HTTP 429 responses: {sum(m.get("status")==429 for m in logs)}. Other request failures/incomplete runs: {len(failed)}. Check request evidence for HTTP status and headers.','', 'A full run means exactly 192 consecutive hourly timestamps from run-date 00:00 through day 8 23:00, 192 finite temperature values, Celsius and zero UTC offset. These are eight calendar days including initialization day; they are not eight full future days after a noon issuance.','', 'Docs: https://open-meteo.com/en/docs/single-runs-api (accessed during this audit). Documentation identifies early ECMWF coverage as IFS Cycle 49R1 hindcasts. Retrieval proves data availability now, not historical operational publication.','', '## Every sampled request','', '| Run date | HTTP | Finite values | Exact axis | Eight full days | Error |','|---|---:|---:|---|---|---|']
    for m in logs:lines.append(f"| {m['run_date']} | {m.get('status')} | {m.get('non_null')} | {m.get('exact_192_hour_axis')} | {m['eight_full_days']} | {m.get('error','')} |")
    lines+=['','Exact URLs, retrieval times and SHA-256 hashes: `audit-evidence/weather_requests.json`. Raw responses: `audit-evidence/weather/`.']
    (ROOT/'reports/audit_open_meteo.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--only',choices=['water','weather','both'],default='both');args=p.parse_args();E.mkdir(parents=True,exist_ok=True)
    jobs=[water,weather] if args.only=='both' else [water if args.only=='water' else weather]
    with concurrent.futures.ThreadPoolExecutor(len(jobs)) as ex:
        for f in [ex.submit(j) for j in jobs]:f.result()
