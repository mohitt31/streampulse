"""Export the agreed StreamPulse CSV/JSONL contract to a self-contained FHIR R4 collection.

Python 3.11, standard library only. No network calls, hidden current time, or model inference.
Local codes/profile URLs are explicitly defined in fhir/input/fsh/streampulse.fsh.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import uuid
from xml.sax.saxutils import escape

BASE = 'https://mohitt31.github.io/streampulse/fhir'
CS = BASE + '/CodeSystem/streampulse'
OAH = 'http://hl7.eu/fhir/ig/oah'
STATION = '05174000'
NAMESPACE = uuid.UUID('b8bb0a90-0807-5e83-84c2-2f0581637a83')
MODELS = {'water_ridge_v1': 'Water-history ridge v1', 'weather_corr_v1': 'Weather correction v1', 'persistence': 'Persistence baseline', 'climatology': 'Climatology baseline'}
ACTION = 'confirm_temperature_and_measure_DO'
METADATA_URL = 'https://hubeau.eaufrance.fr/api/v1/temperature/station?code_station=05174000&size=1'

class ContractError(ValueError):
    """Input is incomplete, inconsistent, or cannot be represented truthfully."""

def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def identifier(kind, value):
    return str(uuid.uuid5(NAMESPACE, kind + ':' + canon(value)))

def ref(resource):
    return {'reference': 'urn:uuid:' + resource['id']}

def cc(code, display=None):
    coding = {'system': CS, 'code': code}
    if display: coding['display'] = display
    return {'coding': [coding]}

def quantity(value, code='Cel', unit='°C'):
    return {'value': value, 'system': 'http://unitsofmeasure.org', 'code': code, 'unit': unit}

def narrative(text):
    return {'status': 'generated', 'div': '<div xmlns="http://www.w3.org/1999/xhtml"><p>' + escape(text) + '</p></div>'}

def resource(kind, key, text, **fields):
    return {'resourceType': kind, 'id': identifier(kind, key), 'text': narrative(text), **fields}

def require(obj, keys, context):
    missing = set(keys) - set(obj)
    if missing: raise ContractError(f'{context}: missing {sorted(missing)}')

def finite(value, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError(f'{context}: expected a finite number')
    return value

def date(value, context):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ContractError(f'{context}: expected YYYY-MM-DD')
    try: return dt.date.fromisoformat(value)
    except ValueError as exc: raise ContractError(f'{context}: invalid date') from exc

def instant(value, context):
    if not isinstance(value, str) or 'T' not in value:
        raise ContractError(f'{context}: expected timezone-aware timestamp')
    try: result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc: raise ContractError(f'{context}: invalid timestamp') from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ContractError(f'{context}: timezone required; do not invent a source timezone')
    if not re.search(r'T\d\d:\d\d:\d\d', value):
        raise ContractError(f'{context}: seconds required for FHIR instant')
    return result

def read_jsonl(path):
    result = []
    for n, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip(): continue
        try: value = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except ValueError as exc: raise ContractError(f'{path}:{n}: invalid JSON') from exc
        if not isinstance(value, dict): raise ContractError(f'{path}:{n}: expected object')
        result.append(value)
    return result

def read_daily(path):
    result = {}
    with Path(path).open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        need = {'date', 'mean_c', 'n_hours', 'n_quarters', 'qual_codes', 'eligible'}
        if not need.issubset(reader.fieldnames or []): raise ContractError('daily_water.csv: missing required columns')
        for n, row in enumerate(reader, 2):
            key = row['date']; date(key, f'daily row {n}')
            if key in result: raise ContractError(f'duplicate daily date: {key}')
            if row['eligible'].strip().lower() not in ('true', 'false'):
                raise ContractError(f'{key}: eligible must be true/false')
            eligible = row['eligible'].strip().lower() == 'true'
            try: hours = int(row['n_hours']); quarters = int(row['n_quarters'])
            except ValueError as exc: raise ContractError(f'{key}: invalid coverage counts') from exc
            if hours < 0 or not 0 <= quarters <= 4: raise ContractError(f'{key}: invalid coverage counts')
            try: mean = float(row['mean_c'])
            except ValueError:
                if eligible: raise ContractError(f'{key}: eligible daily value is not numeric')
                mean = None
            if eligible: finite(mean, key)
            result[key] = dict(date=key, mean_c=mean, n_hours=hours, n_quarters=quarters, qual_codes=row['qual_codes'], eligible=eligible)
    return result

def source_url(start, end=None):
    return ('https://hubeau.eaufrance.fr/api/v1/temperature/chronique?code_station=' + STATION
            + '&date_debut_mesure=' + start + '&date_fin_mesure=' + (end or start) + '&size=20000')

def build_bundle(daily, forecasts, alerts, metadata, *, demo_fixture=False):
    """forecast_refs are zero-based indices into parsed, nonblank JSONL records."""
    rows = metadata.get('data', [])
    if len(rows) != 1 or rows[0].get('code_station') != STATION:
        raise ContractError('expected exactly one cached Hub\'eau station 05174000')
    meta = rows[0]
    for key in ('libelle_station', 'uri_station', 'longitude', 'latitude'): 
        if key not in meta: raise ContractError(f'station metadata missing {key}')
    if not -90 <= finite(meta['latitude'], 'latitude') <= 90 or not -180 <= finite(meta['longitude'], 'longitude') <= 180:
        raise ContractError('invalid station coordinates')
    records = {}
    def add(r):
        key = 'urn:uuid:' + r['id']
        if key in records and records[key] != r: raise ContractError(f'ID collision: {key}')
        records[key] = r
        return r
    org = add(resource('Organization', 'demo-processor', 'StreamPulse DEMO processing organization. Not an environmental authority or the original sensor operator.', active=True, name='StreamPulse DEMO processing organization'))
    recipient = add(resource('Organization', 'demo-monitoring', 'StreamPulse DEMO monitoring coordinator organization. No real authority affiliation or message delivery is asserted.', active=True, name='StreamPulse DEMO monitoring coordinator'))
    location = add(resource('Location', STATION, f"{meta['libelle_station']}; Hub'eau station {STATION}, {meta.get('libelle_commune', '')}. Source: {METADATA_URL}",
        meta={'profile': [OAH+'/StructureDefinition/location-oah']},
        identifier=[{'system':'https://id.eaufrance.fr/StationMesureEauxSurface','value':STATION}],
        status='active',name=meta['libelle_station'],mode='instance',
        description='Historical demonstration site near Toulouse; official OAH sampling-site membership UNVERIFIED. Station URI: '+meta['uri_station'],
        position={'longitude':meta['longitude'],'latitude':meta['latitude']}))
    daily_resources = {}
    def get_daily(day):
        if day in daily_resources: return daily_resources[day]
        if day not in daily: raise ContractError(f'missing input observation date {day}')
        row = daily[day]
        if not row['eligible']: raise ContractError(f'ineligible input observation date {day}')
        mean=finite(row['mean_c'],f'{day} mean_c')
        r=add(resource('Observation', {'station':STATION,'daily':row},
            f"Derived source-calendar daily mean {mean} °C on {day}; {row['n_hours']} hours, {row['n_quarters']} six-hour portions. Source qualification: {row['qual_codes']}. FHIR final describes the completed aggregation, not source quality. Source timezone UNVERIFIED. {source_url(day)}",
            meta={'profile':[OAH+'/StructureDefinition/observation-indicators-oah']},status='final',
            code=cc('daily-mean-water-temperature','Daily mean water temperature'),subject=ref(location),effectiveDateTime=day,
            performer=[ref(org)],valueQuantity=quantity(mean),method=cc('daily-aggregation'),
            component=[{'code':cc('n-hours'),'valueQuantity':quantity(row['n_hours'],'1','hours counted')},
                {'code':cc('n-quarters'),'valueQuantity':quantity(row['n_quarters'],'1','portions counted')},
                {'code':cc('source-qualification'),'valueString':row['qual_codes'] or 'not supplied'}]))
        daily_resources[day]=r
        return r
    forecast_resources=[];checked=[]
    required={'station_id','mode','model_id','model_version','origin_date','issued_simulated','generated_at','lead_days','target_date','pred_mean_c','pi90_low_c','pi90_high_c','p90_reference_c','watch','weather_run_init','input_obs_dates'}
    for index,f in enumerate(forecasts):
        context=f'forecast[{index}]';require(f,required,context)
        if f['station_id']!=STATION: raise ContractError(f'{context}: unsupported station')
        if f['mode'] not in ('replay','operational'): raise ContractError(f'{context}: invalid mode')
        if f['model_id'] not in MODELS: raise ContractError(f'{context}: unsupported model_id')
        if not isinstance(f['model_version'],str) or not re.fullmatch(r'[0-9a-fA-F]{7,40}',f['model_version']):
            raise ContractError(f'{context}: model_version must be a git SHA (7–40 hexadecimal characters)')
        origin=date(f['origin_date'],context);target=date(f['target_date'],context)
        lead=f['lead_days']
        if type(lead) is not int or not 1<=lead<=7 or target!=origin+dt.timedelta(days=lead):
            raise ContractError(f'{context}: target_date must equal origin_date + lead_days (1–7)')
        simulated=instant(f['issued_simulated'],context);generated=instant(f['generated_at'],context)
        if simulated.astimezone(dt.timezone.utc).date()!=origin: raise ContractError(f'{context}: simulated UTC day differs from origin_date')
        if generated<simulated: raise ContractError(f'{context}: real generation precedes forecast origin')
        if f['weather_run_init'] is not None:
            run=instant(f['weather_run_init'],context)
            if run>simulated: raise ContractError(f'{context}: weather initialization after origin')
        if f['model_id']=='weather_corr_v1' and f['weather_run_init'] is None:
            raise ContractError(f'{context}: weather model requires weather_run_init')
        vals=[finite(f[k],context+' '+k) for k in ('pi90_low_c','pred_mean_c','pi90_high_c','p90_reference_c')]
        if not vals[0]<=vals[1]<=vals[2]: raise ContractError(f'{context}: unordered prediction interval')
        if type(f['watch']) is not bool: raise ContractError(f'{context}: watch must be boolean')
        dates=f['input_obs_dates']
        if not isinstance(dates,list) or not dates or len(set(dates))!=len(dates): raise ContractError(f'{context}: unique nonempty input_obs_dates required')
        if any(date(day,context)>=origin for day in dates): raise ContractError(f'{context}: input date reaches or exceeds origin day')
        inputs=[get_daily(day) for day in sorted(dates)]
        model=add(resource('Device', [f['model_id'],f['model_version']], 'StreamPulse model software '+f['model_id']+' version '+f['model_version']+'. No medical-device or operational approval implied.',
            meta={'profile':[BASE+'/StructureDefinition/streampulse-model-device']},status='active',
            deviceName=[{'name':f['model_id'],'type':'model-name'}],version=[{'value':f['model_version']}],owner=ref(org)))
        # Equal date-only period boundaries represent that source calendar day at day precision.
        # Do not manufacture midnight UTC boundaries for an undocumented source clock.
        note=('Forecast reconstructed in historical replay.' if f['mode']=='replay' else 'Operational-labelled input; telemetry readiness is not established by this export.')
        note+=' effectivePeriod uses date-only boundaries for the target source-calendar day. issued is real generation; forecast-origin is the simulated/operational origin. Watch is supplied by the pipeline; its decision rule is not specified by this contract.'
        if f['weather_run_init']:note+=' Weather initialization: '+f['weather_run_init']+'. Historical publication latency UNVERIFIED.'
        if demo_fixture:note+=' SYNTHETIC FORECAST FIXTURE: not a trained model result or skill claim.'
        out=add(resource('Observation', f, f"{note} Predicted daily mean {f['pred_mean_c']} °C for {f['target_date']}.",
            meta={'profile':[BASE+'/StructureDefinition/streampulse-forecast-observation']},
            extension=[{'url':BASE+'/StructureDefinition/forecast-origin','valueDateTime':f['issued_simulated']},{'url':BASE+'/StructureDefinition/run-mode','valueCode':f['mode']}],
            status='final',code=cc('predicted-daily-mean-water-temperature','Predicted daily mean water temperature'),subject=ref(location),
            effectivePeriod={'start':f['target_date'],'end':f['target_date']},issued=f['generated_at'],performer=[ref(org)],method=cc(f['model_id'],MODELS[f['model_id']]),device=ref(model),
            derivedFrom=[ref(r) for r in inputs],valueQuantity=quantity(f['pred_mean_c']),
            component=[{'code':cc('pi90-low'),'valueQuantity':quantity(f['pi90_low_c'])},{'code':cc('pi90-high'),'valueQuantity':quantity(f['pi90_high_c'])},
                {'code':cc('p90-reference'),'valueQuantity':quantity(f['p90_reference_c'])},{'code':cc('watch'),'valueCodeableConcept':cc('watch-on' if f['watch'] else 'watch-off')}],note=[{'text':note}]))
        # URL is a source identifier, not a fabricated FHIR Reference to an API payload.
        entities=[{'role':'source','what':ref(r)} for r in inputs]
        entities.append({'role':'source','what':{'identifier':{'system':'urn:ietf:rfc:3986','value':source_url(min(dates),max(dates))},'display':'Hub\'eau upstream retrieval URL; exact pipeline snapshot/hash is not supplied by the contract'}})
        if f['weather_run_init']:
            # Contract lacks provider/model/request identity: never assert this guessed URL as actual provenance.
            note_url='Weather run initialization is supplied, but provider, model and exact request URL are UNVERIFIED by the interface.'
        else:note_url='No weather run supplied.'
        add(resource('Provenance', [out['id'],f['generated_at']], 'Forecast generation lineage. '+note_url,
            target=[ref(out)],recorded=f['generated_at'],occurredDateTime=f['generated_at'],activity={'coding':[{'system':'http://terminology.hl7.org/CodeSystem/v3-DataOperation','code':'CREATE','display':'create'}]},
            agent=[{'who':ref(model),'onBehalfOf':ref(org)},{'who':ref(org)}],entity=entities))
        forecast_resources.append(out);checked.append((f,generated))
    seen_alerts=set()
    for i,a in enumerate(alerts):
        context=f'alert[{i}]';require(a,{'alert_id','station_id','origin_date','target_dates','forecast_refs','action','status','ack'},context)
        if not isinstance(a['alert_id'],str) or not a['alert_id'] or a['alert_id'] in seen_alerts:raise ContractError(f'{context}: unique nonempty alert_id required')
        seen_alerts.add(a['alert_id'])
        if a['station_id']!=STATION or a['action']!=ACTION or a['status'] not in ('open','acknowledged'):raise ContractError(f'{context}: unsupported station/action/status')
        indices=a['forecast_refs']
        if not isinstance(indices,list) or not indices or any(type(j) is not int or not 0<=j<len(forecasts) for j in indices) or len(set(indices))!=len(indices):raise ContractError(f'{context}: invalid zero-based forecast_refs')
        if any(forecasts[j]['station_id']!=a['station_id'] or forecasts[j]['origin_date']!=a['origin_date'] for j in indices):raise ContractError(f'{context}: forecast station/origin mismatch')
        if not isinstance(a['target_dates'],list) or len(set(a['target_dates']))!=len(a['target_dates']) or set(a['target_dates'])!={forecasts[j]['target_date'] for j in indices}:raise ContractError(f'{context}: target_dates mismatch')
        if a['status']=='open' and a['ack'] is not None:raise ContractError(f'{context}: open alert cannot have acknowledgement')
        if a['status']=='acknowledged' and not isinstance(a['ack'],dict):raise ContractError(f'{context}: acknowledged alert needs ack object')
        text='DEMO monitoring follow-up: confirm temperature and measure dissolved oxygen using an appropriate protocol; review site conditions. A watch is not proof of ecological damage or human health risk. This record contains no delivery timestamp because the interface supplies none.'
        alert=add(resource('Communication', ['alert',a['alert_id'],a['origin_date'],indices],text,
            status='preparation',category=[cc('confirm-temperature-and-measure-do')],
            about=[ref(location)]+[ref(forecast_resources[j]) for j in indices],sender=ref(org),recipient=[ref(recipient)],
            payload=[{'contentString':text}],note=[{'text':'Application review state: '+a['status']+'. Communication remains preparation: transport/delivery is not asserted.'}]))
        if a['ack'] is not None:
            ack=a['ack'];require(ack,{'by','at','note'},context+' ack')
            if not isinstance(ack['by'],str) or not ack['by'] or not isinstance(ack['note'],str):raise ContractError(f'{context}: invalid acknowledgement actor/note')
            at=instant(ack['at'],context+' ack.at')
            if at<max(checked[j][1] for j in indices):raise ContractError(f'{context}: acknowledgement precedes real forecast generation')
            add(resource('Communication',['ack',a['alert_id'],ack], 'DEMO acknowledgement by '+ack['by']+'. '+ack['note'],
                status='completed',category=[cc('acknowledgement')],inResponseTo=[ref(alert)],about=[ref(location)]+[ref(forecast_resources[j]) for j in indices],
                sent=ack['at'],sender=ref(recipient),recipient=[ref(org)],payload=[{'contentString':'Acknowledged by demo actor '+ack['by']+': '+ack['note']}],
                note=[{'text':'Records the supplied acknowledgement event, not authenticated identity, external message delivery, or completed sampling.'}]))
    entries=[{'fullUrl':key,'resource':r} for key,r in sorted(records.items())]
    bundle={'resourceType':'Bundle','id':identifier('Bundle',entries),'type':'collection','entry':entries}
    if demo_fixture:bundle['meta']={'tag':[{'system':CS,'code':'synthetic-fixture','display':'Synthetic forecast fixture'}]}
    assert_references(bundle)
    return bundle

def assert_references(bundle):
    urls={e['fullUrl'] for e in bundle['entry']}
    if len(urls)!=len(bundle['entry']):raise ContractError('duplicate fullUrl')
    def visit(obj):
        if isinstance(obj,dict):
            if 'reference' in obj and obj['reference'] not in urls:raise ContractError('unresolved reference '+str(obj['reference']))
            for v in obj.values():visit(v)
        elif isinstance(obj,list):
            for v in obj:visit(v)
    visit(bundle)

def export(daily_path,forecast_path,alert_path,metadata_path,output,*,demo_fixture=False):
    bundle=build_bundle(read_daily(daily_path),read_jsonl(forecast_path),read_jsonl(alert_path),json.loads(Path(metadata_path).read_text()),demo_fixture=demo_fixture)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(bundle,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    return bundle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daily',default='data/processed/daily_water.csv')
    parser.add_argument('--forecasts',default='reports/forecasts.jsonl')
    parser.add_argument('--alerts',default='reports/alerts.jsonl')
    parser.add_argument('--station-metadata',default='data/reference/station_05174000.json')
    parser.add_argument('--output',default='reports/fhir/bundle.json')
    parser.add_argument('--demo-fixture',action='store_true',help='Explicitly label synthetic fixture forecasts')
    args=parser.parse_args()
    try:bundle=export(args.daily,args.forecasts,args.alerts,args.station_metadata,args.output,demo_fixture=args.demo_fixture)
    except (ContractError,OSError,ValueError,TypeError) as exc:parser.exit(2,f'FHIR export failed: {exc}\n')
    print(f"Exported {len(bundle['entry'])} resources to {args.output}; external reference count 0")

if __name__=='__main__':main()
