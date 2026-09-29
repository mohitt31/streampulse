#!/usr/bin/env python3
"""Build labelled synthetic-forecast fixtures atop real Hub'eau observations, and standalone examples."""
import copy,csv,datetime as dt,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from streampulse.fhir_export import *
FIX=ROOT/'tests/fixtures/fhir'

def standalone(root,bundle):
    lookup={e['fullUrl']:e['resource'] for e in bundle['entry']};seen=set();todo=[]
    def scan(v):
        if isinstance(v,dict):
            if 'reference' in v:
                u=v['reference']
                if u in lookup and u not in seen and lookup[u]['id']!=root['id']:seen.add(u);todo.append(u)
            for w in v.values():scan(w)
        elif isinstance(v,list):
            for w in v:scan(w)
    scan(root);i=0
    while i<len(todo):scan(lookup[todo[i]]);i+=1
    result=copy.deepcopy(root)
    if todo:result['contained']=[copy.deepcopy(lookup[u]) for u in sorted(todo)]
    def rewrite(v):
        if isinstance(v,dict):
            if 'reference' in v and v['reference'].startswith('urn:uuid:'):v['reference']='#'+v['reference'][9:]
            for w in v.values():rewrite(w)
        elif isinstance(v,list):
            for w in v:rewrite(w)
    rewrite(result);return result

def dump(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

def main():
    FIX.mkdir(parents=True,exist_ok=True)
    # Bootstrap fixtures from saved audit data, never synthesize measured inputs.
    rawpath=ROOT/'reports/audit-evidence/water/2025-1.json'
    if rawpath.exists() and not (FIX/'daily_water.csv').exists():
        raw=json.loads(rawpath.read_text())['data'];days={}
        for r in raw:
            if '2025-06-24'<=r['date_mesure_temp']<='2025-06-30':days.setdefault(r['date_mesure_temp'],{})[r['heure_mesure_temp']]=r
        with (FIX/'daily_water.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['date','mean_c','n_hours','n_quarters','qual_codes','eligible']);writer.writeheader()
            for day,items in sorted(days.items()):
                rows=list(items.values());writer.writerow(dict(date=day,mean_c=sum(r['resultat'] for r in rows)/len(rows),n_hours=len(rows),n_quarters=len({int(r['heure_mesure_temp'][:2])//6 for r in rows}),qual_codes=';'.join(sorted({r['code_qualification'] for r in rows})),eligible=True))
        daily=read_daily(FIX/'daily_water.csv');generated=dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        f=dict(station_id=STATION,mode='replay',model_id='water_ridge_v1',model_version='0000000000000000000000000000000000000000',origin_date='2025-07-01',issued_simulated='2025-07-01T12:00:00Z',generated_at=generated.isoformat().replace('+00:00','Z'),lead_days=3,target_date='2025-07-04',pred_mean_c=22.1,pi90_low_c=21.2,pi90_high_c=23.0,p90_reference_c=21.9,watch=True,weather_run_init=None,input_obs_dates=sorted(daily))
        (FIX/'forecasts.jsonl').write_text(json.dumps(f)+'\n')
        a=dict(alert_id='demo-warmth-20250701',station_id=STATION,origin_date='2025-07-01',target_dates=['2025-07-04'],forecast_refs=[0],action=ACTION,status='acknowledged',ack={'by':'demo-coordinator','at':(generated+dt.timedelta(minutes=1)).isoformat().replace('+00:00','Z'),'note':'Synthetic demo acknowledgement; no field sampling performed.'})
        (FIX/'alerts.jsonl').write_text(json.dumps(a)+'\n')
    bundle=export(FIX/'daily_water.csv',FIX/'forecasts.jsonl',FIX/'alerts.jsonl',ROOT/'data/reference/station_05174000.json',FIX/'bundle.json',demo_fixture=True)
    entries=[e['resource'] for e in bundle['entry']]
    selected={
        'location':next(r for r in entries if r['resourceType']=='Location'),
        'organization':next(r for r in entries if r['resourceType']=='Organization' and 'processing' in r['name']),
        'model-device':next(r for r in entries if r['resourceType']=='Device'),
        'daily-source-observation':next(r for r in entries if r['resourceType']=='Observation' and r['code']['coding'][0]['code']=='daily-mean-water-temperature'),
        'forecast':next(r for r in entries if r['resourceType']=='Observation' and r['code']['coding'][0]['code']=='predicted-daily-mean-water-temperature'),
        'alert':next(r for r in entries if r['resourceType']=='Communication' and 'inResponseTo' not in r),
        'acknowledgement':next(r for r in entries if r['resourceType']=='Communication' and 'inResponseTo' in r),
        'provenance':next(r for r in entries if r['resourceType']=='Provenance')}
    # Add a real hourly value, preserving date-only precision because timezone is undocumented.
    if rawpath.exists():
        raw=json.loads(rawpath.read_text())['data'][0]
        dump(ROOT/'data/reference/source_hourly_record.json',{'source_url':source_url(raw['date_mesure_temp']),'record':raw})
    raw=json.loads((ROOT/'data/reference/source_hourly_record.json').read_text())['record']
    source=resource('Observation',['hourly-source',raw],f"Real Hub'eau sensor value {raw['resultat']} °C on source date {raw['date_mesure_temp']}, source clock {raw['heure_mesure_temp']}; timezone UNVERIFIED. Performer is the DEMO organization responsible for this representation, not an asserted sensor operator. Qualification {raw['code_qualification']}.",
        meta={'profile':[OAH+'/StructureDefinition/observation-indicators-oah']},status='final',
        code={'coding':[{'system':OAH+'/CodeSystem/temporarySystem-oah-eu','code':'waterTemperature','display':'Water temperature'}]},subject=ref(selected['location']),
        effectiveDateTime=raw['date_mesure_temp'],performer=[ref(selected['organization'])],valueQuantity=quantity(raw['resultat']),
        note=[{'text':f"Original source date/time: {raw['date_mesure_temp']} {raw['heure_mesure_temp']}; timezone UNVERIFIED; {source_url(raw['date_mesure_temp'])}"}])
    selected['source-temperature']=source
    bundle['entry'].append({'fullUrl':'urn:uuid:'+source['id'],'resource':source})
    for name,r in selected.items():dump(ROOT/f'fhir/examples/{name}.json',standalone(r,bundle))
    bad=copy.deepcopy(json.loads((ROOT/'fhir/examples/daily-source-observation.json').read_text()));removed={v['reference'][1:] for v in bad.pop('performer')};bad['contained']=[r for r in bad.get('contained',[]) if r['id'] not in removed];dump(ROOT/'fhir/negative-controls/missing-performer.json',bad)
    bad=copy.deepcopy(json.loads((ROOT/'fhir/examples/daily-source-observation.json').read_text()));locid=bad['subject']['reference'][1:]
    bad['contained']=[r for r in bad['contained'] if r['id']!=locid]
    bad['contained'].append({'resourceType':'Patient','id':locid,'active':True});dump(ROOT/'fhir/negative-controls/wrong-subject-type.json',bad)
    bad=copy.deepcopy(json.loads((ROOT/'fhir/examples/forecast.json').read_text()));bad['extension']=[e for e in bad['extension'] if not e['url'].endswith('/run-mode')];dump(ROOT/'fhir/negative-controls/missing-run-mode.json',bad)
    print('Built collection Bundle, 9 standalone examples and 3 negative controls; predictions and acknowledgement are explicitly synthetic.')
if __name__=='__main__':main()
