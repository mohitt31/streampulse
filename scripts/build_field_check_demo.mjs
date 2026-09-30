#!/usr/bin/env node
// Real frozen forecast/alert JSONL + explicitly synthetic field readings. No report writes.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { buildFieldCheckBundle, identifier } from '../web/src/lib/fhirFieldCheck.ts';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [contextFile, outputDir] = process.argv.slice(2);
if (!contextFile || !outputDir) throw new Error('Usage: node --experimental-strip-types scripts/build_field_check_demo.mjs CONTEXT_JSON OUTPUT_DIR');
const context = JSON.parse(fs.readFileSync(contextFile, 'utf8'));
for (const [file, expected] of Object.entries(context.source_hashes)) {
  if (createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex') !== expected) throw new Error('Stale field-check context: ' + file);
}
const jsonl = file => fs.readFileSync(path.join(root, file), 'utf8').trim().split('\n').map(JSON.parse);
const forecasts = jsonl('reports/fhir/demo_forecasts.jsonl');
const alerts = jsonl('reports/fhir/demo_alerts.jsonl');
const alert = alerts[0];
const selected = context.alerts[alert.alert_id];
const input = {
  alert, forecasts: selected.forecasts.map(id => context.resources[id]),
  ack: alert.ack,
  measurements: { temp_c: 22.8, do_mg_l: 7.4, do_pct: 104, measured_at: alert.target_dates[0] + 'T10:30:00Z',
    recorded_at: alert.ack.at, note: 'SYNTHETIC FIELD CHECK for conformance testing; no actual sampling.' },
  site: { location: context.location, supportingResources: selected.closure.filter(id => !selected.forecasts.includes(id)).map(id => context.resources[id]) },
  modelVersion: forecasts[alert.forecast_refs[0]].model_version,
};
// Each selected forecast is the exact Python-exported resource, not rounded UI data.
for (const [i, index] of alert.forecast_refs.entries()) {
  const original = forecasts[index], encoded = input.forecasts[i];
  if (!original.watch || encoded.valueQuantity.value !== original.pred_mean_c || encoded.effectivePeriod.start !== original.target_date) throw new Error('Forecast evidence mismatch');
}
const bundle = buildFieldCheckBundle(input);
fs.mkdirSync(outputDir, { recursive: true });
const write = (name, value) => fs.writeFileSync(path.join(outputDir, name), JSON.stringify(value, null, 2) + '\n');
write('bundle.json', bundle);
write('input.json', input);
const noPct = structuredClone(input); delete noPct.measurements.do_pct;
write('without-saturation.json', buildFieldCheckBundle(noPct));
const negative = structuredClone(bundle);
const oxygen = negative.entry.find(e => e.resource.meta?.profile?.includes('https://mohitt31.github.io/streampulse/fhir/StructureDefinition/streampulse-field-check-observation') && e.resource.valueQuantity.code === 'mg/L').resource;
delete oxygen.valueQuantity.unit;
write('missing-unit.json', negative);
write('id-vectors.json', [
  ['Location', '05174000'], ['Organization', 'demo-monitoring'],
  ['Communication', ['alert', alert.alert_id, alert.origin_date, alert.forecast_refs]],
  ['Communication', ['ack', alert.alert_id, input.ack]],
  ['Observation', { note: '<demo> & café 🌊', station: '05174000', index: 2 }],
].map(([kind, key]) => ({ kind, key, id: identifier(kind, key) })));
console.log(`Browser builder: ${bundle.entry.length} resources; explicit field-check fixtures written to ${outputDir}`);
