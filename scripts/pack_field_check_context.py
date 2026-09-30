#!/usr/bin/env python3
"""Reuse the Python exporter's exact forecast IDs and dependency closure, read-only.

No model runs or report writes. Browser inputs include full-precision forecast evidence,
not rounded chart cells. Demo mode uses the user's real FHIR demo JSONL inputs for CI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from streampulse.fhir_export import build_bundle, read_daily, read_jsonl, identifier

ROOT = Path(__file__).resolve().parents[1]


def references(value):
    if isinstance(value, dict):
        if isinstance(value.get('reference'), str):
            yield value['reference']
        for v in value.values():
            yield from references(v)
    elif isinstance(value, list):
        for v in value:
            yield from references(v)


def pack(demo=False):
    fp = ROOT / ('reports/fhir/demo_forecasts.jsonl' if demo else 'reports/forecasts.jsonl')
    ap = ROOT / ('reports/fhir/demo_alerts.jsonl' if demo else 'reports/alerts.jsonl')
    forecasts, alerts = read_jsonl(fp), read_jsonl(ap)
    daily = read_daily(ROOT / 'data/processed/daily_water.csv')
    metadata = json.loads((ROOT / 'data/reference/station_05174000.json').read_text())
    bundle = build_bundle(daily, forecasts, alerts, metadata)
    all_resources = {e['fullUrl']: e['resource'] for e in bundle['entry']}
    location = next(r for r in all_resources.values() if r['resourceType'] == 'Location')
    result = {'location': location, 'alerts': {}, 'resources': {}, 'source_hashes': {
        str(fp.relative_to(ROOT)): hashlib.sha256(fp.read_bytes()).hexdigest(),
        str(ap.relative_to(ROOT)): hashlib.sha256(ap.read_bytes()).hexdigest()}}
    provenance = {}
    for url, r in all_resources.items():
        if r['resourceType'] == 'Provenance':
            for target in r['target']:
                provenance.setdefault(target['reference'], []).append(url)
    for alert in alerts:
        ids = []
        for index in alert['forecast_refs']:
            f = forecasts[index]
            if not f['watch']:
                raise ValueError('Alert references a non-watch forecast')
            url = 'urn:uuid:' + identifier('Observation', f)
            ids.append(url)
        pending = list(ids)
        for url in ids:
            pending.extend(provenance.get(url, []))
        closure = set()
        while pending:
            url = pending.pop()
            if url in closure:
                continue
            r = all_resources[url]
            closure.add(url)
            pending.extend(references(r))
        result['alerts'][alert['alert_id']] = {'forecasts': ids, 'closure': sorted(closure)}
        result['resources'].update({url: all_resources[url] for url in closure})
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--output', type=Path, default=ROOT / 'web/public/data/field-checks.json')
    a = p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(pack(a.demo), ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Wrote field-check context: {a.output} ({a.output.stat().st_size} bytes)')
