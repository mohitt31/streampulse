import type { Alert } from '../types';

export const BASE = 'https://mohitt31.github.io/streampulse/fhir';
export const CS = `${BASE}/CodeSystem/streampulse`;
const NAMESPACE = 'b8bb0a90-0807-5e83-84c2-2f0581637a83';
const UCUM = 'http://unitsofmeasure.org';
export interface Resource { resourceType: string; id: string; [key: string]: unknown }
export interface ForecastObservation extends Resource {
  resourceType: 'Observation';
  effectivePeriod: { start: string; end: string };
  valueQuantity: { value: number; code: string; system: string };
  issued: string;
  subject: { reference: string };
  device: { reference: string };
  extension: { url: string; valueDateTime?: string; valueCode?: string }[];
  component: { code: { coding: { system: string; code: string }[] }; valueCodeableConcept?: { coding: { system: string; code: string }[] } }[];
}
export interface FieldCheckSite { location: Resource; supportingResources: Resource[] }
export interface Measurements {
  temp_c: number; do_mg_l: number; do_pct?: number; measured_at: string; note?: string;
  /** Actual entry time. UI always supplies it; deterministic fixtures may use ack.at. */
  recorded_at?: string;
}
export interface FieldCheckInput {
  alert: Alert; forecasts: ForecastObservation[]; ack: { by: string; at: string; note: string };
  measurements: Measurements; site: FieldCheckSite; modelVersion: string;
}
export interface FieldCheckBundle {
  resourceType: 'Bundle'; id: string; type: 'collection';
  meta: { tag: { system: string; code: string; display: string }[] };
  entry: { fullUrl: string; resource: Resource }[];
}

/** Python fhir_export.identifier scheme: UUIDv5(namespace, kind + ':' + sorted JSON).
 * New identity keys use strings/integers only, avoiding cross-language float spelling.
 * Existing forecast/input/model IDs and resources come unchanged from the Python exporter.
 */
export function canonical(value: unknown): string {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (typeof value === 'object' && value) {
    const object = value as Record<string, unknown>;
    return '{' + Object.keys(object).sort().map(k => JSON.stringify(k) + ':' + canonical(object[k])).join(',') + '}';
  }
  throw new Error('Non-JSON or non-finite value');
}

function sha1(bytes: Uint8Array): Uint8Array {
  const length = Math.ceil((bytes.length + 9) / 64) * 64;
  const input = new Uint8Array(length);
  input.set(bytes); input[bytes.length] = 0x80;
  const view = new DataView(input.buffer);
  view.setUint32(length - 8, Math.floor(bytes.length / 0x20000000));
  view.setUint32(length - 4, bytes.length * 8 >>> 0);
  const state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0];
  const rotate = (x: number, n: number) => (x << n) | (x >>> (32 - n));
  const w = new Int32Array(80);
  for (let offset = 0; offset < length; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getInt32(offset + i * 4);
    for (let i = 16; i < 80; i++) w[i] = rotate(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    let [a, b, c, d, e] = state;
    for (let i = 0; i < 80; i++) {
      const f = i < 20 ? (b & c) | (~b & d) : i < 40 ? b ^ c ^ d : i < 60 ? (b & c) | (b & d) | (c & d) : b ^ c ^ d;
      const k = i < 20 ? 0x5a827999 : i < 40 ? 0x6ed9eba1 : i < 60 ? 0x8f1bbcdc : 0xca62c1d6;
      const next = (rotate(a, 5) + f + e + k + w[i]) | 0;
      e = d; d = c; c = rotate(b, 30); b = a; a = next;
    }
    [a, b, c, d, e].forEach((v, i) => { state[i] = (state[i] + v) | 0; });
  }
  const output = new Uint8Array(20), out = new DataView(output.buffer);
  state.forEach((v, i) => out.setInt32(i * 4, v));
  return output;
}

export function identifier(kind: string, key: unknown): string {
  const ns = Uint8Array.from(NAMESPACE.replaceAll('-', '').match(/../g)!, h => parseInt(h, 16));
  const name = new TextEncoder().encode(kind + ':' + canonical(key));
  const bytes = new Uint8Array(ns.length + name.length); bytes.set(ns); bytes.set(name, ns.length);
  const digest = sha1(bytes).slice(0, 16);
  digest[6] = (digest[6] & 0x0f) | 0x50; digest[8] = (digest[8] & 0x3f) | 0x80;
  const hex = [...digest].map(x => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

const ref = (r: Resource) => ({ reference: 'urn:uuid:' + r.id });
const cc = (code: string) => ({ coding: [{ system: CS, code }] });
const narrative = (text: string) => ({ status: 'generated', div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>' + text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;') + '</p></div>' });
const resource = (kind: string, key: unknown, text: string, fields: Record<string, unknown>): Resource => ({ resourceType: kind, id: identifier(kind, key), text: narrative(text), ...fields });
function requireValue(condition: unknown, message: string): asserts condition { if (!condition) throw new Error(message); }
function day(value: string): string {
  requireValue(/^\d{4}-\d{2}-\d{2}$/.test(value), 'Expected a calendar date');
  const parsed = new Date(value + 'T00:00:00Z');
  requireValue(Number.isFinite(+parsed) && parsed.toISOString().slice(0, 10) === value, 'Invalid calendar date');
  return value;
}
function instant(value: string): number {
  requireValue(/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,3})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(value), 'A timestamp with seconds and an explicit timezone is required');
  day(value.slice(0, 10));
  const parsed = Date.parse(value); requireValue(Number.isFinite(parsed), 'Invalid timestamp'); return parsed;
}
function finite(value: number, label: string): number { requireValue(typeof value === 'number' && Number.isFinite(value), `${label} must be a finite number`); return value; }
export function allReferences(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(allReferences);
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    return [...(typeof obj.reference === 'string' ? [obj.reference] : []), ...Object.values(obj).flatMap(allReferences)];
  }
  return [];
}

/** Synchronous, pure, deterministic. No fetch, storage, clock, random ID or model inference. */
export function buildFieldCheckBundle(input: FieldCheckInput): FieldCheckBundle {
  const { alert, forecasts, ack, measurements: m, site, modelVersion } = input;
  requireValue(alert.station_id === '05174000' && alert.action === 'confirm_temperature_and_measure_DO', 'Unsupported station or action');
  requireValue(alert.alert_id && forecasts.length > 0 && forecasts.length === alert.forecast_refs.length, 'Expected exactly the watch forecasts for this alert');
  requireValue(new Set(alert.forecast_refs).size === alert.forecast_refs.length && alert.forecast_refs.every(i => Number.isInteger(i) && i >= 0), 'Invalid forecast indices');
  requireValue(new Set(forecasts.map(f => f.id)).size === forecasts.length, 'Duplicate forecast');
  requireValue(typeof ack.by === 'string' && ack.by.trim().length > 0 && typeof ack.note === 'string', 'Acknowledgement actor and note required');
  requireValue(/^[0-9a-fA-F]{7,40}$/.test(modelVersion), 'Model version must be a Git SHA');
  const recorded = m.recorded_at ?? ack.at;
  requireValue(instant(recorded) >= instant(ack.at) && instant(recorded) >= instant(m.measured_at), 'Measurement and acknowledgement cannot be after entry time');
  requireValue(finite(m.temp_c, 'Temperature') >= -273.15, 'Temperature is below absolute zero');
  requireValue(finite(m.do_mg_l, 'Dissolved oxygen') >= 0, 'Dissolved oxygen cannot be negative');
  if (m.do_pct !== undefined) requireValue(finite(m.do_pct, 'DO saturation') >= 0, 'DO saturation cannot be negative');
  requireValue(m.note === undefined || typeof m.note === 'string', 'Measurement note must be text');
  day(alert.origin_date);
  const location = site.location;
  requireValue(location.resourceType === 'Location' && location.id === identifier('Location', alert.station_id), 'Location does not match alert station');
  const records = new Map<string, Resource>();
  const add = (r: Resource) => {
    const url = 'urn:uuid:' + r.id, previous = records.get(url);
    requireValue(!previous || canonical(previous) === canonical(r), `Conflicting resource identity: ${url}`);
    records.set(url, structuredClone(r)); return r;
  };
  add(location); site.supportingResources.forEach(add); forecasts.forEach(add);
  const targets = forecasts.map(f => f.effectivePeriod.start).sort();
  requireValue(canonical(targets) === canonical([...alert.target_dates].sort()), 'Alert target dates do not match forecasts');
  const measurementDay = m.measured_at.slice(0, 10);
  requireValue(targets.includes(measurementDay), 'Measurement calendar day must match a target day of this historical alert');
  for (const f of forecasts) {
    requireValue(f.subject.reference === ref(location).reference && f.valueQuantity.code === 'Cel' && f.valueQuantity.system === UCUM, 'Forecast site or unit mismatch');
    requireValue(f.effectivePeriod.start === f.effectivePeriod.end, 'Expected source-calendar daily forecast');
    requireValue(f.extension.some(e => e.url === BASE + '/StructureDefinition/forecast-origin' && e.valueDateTime?.startsWith(alert.origin_date + 'T')), 'Forecast origin mismatch');
    requireValue(f.component.some(c => c.code.coding.some(x => x.system === CS && x.code === 'watch') && c.valueCodeableConcept?.coding.some(x => x.system === CS && x.code === 'watch-on')), 'Only watch forecasts may be linked to this alert');
    requireValue(instant(ack.at) >= instant(f.issued), 'Acknowledgement precedes actual forecast generation');
    const model = records.get(f.device.reference);
    requireValue(model?.resourceType === 'Device' && Array.isArray(model.version) && model.version.some(v => (v as { value?: string }).value === modelVersion), 'Missing or mismatched model Device');
  }
  const org = add(resource('Organization', 'demo-processor', 'StreamPulse DEMO processing organization. Not an environmental authority or the original sensor operator.', { active: true, name: 'StreamPulse DEMO processing organization' }));
  const coordinator = add(resource('Organization', 'demo-monitoring', 'StreamPulse DEMO monitoring coordinator organization. No real authority affiliation or message delivery is asserted.', { active: true, name: 'StreamPulse DEMO monitoring coordinator' }));
  const text = 'DEMO monitoring follow-up: confirm temperature and measure dissolved oxygen using an appropriate protocol; review site conditions. A watch is not proof of ecological damage or human health risk. This record contains no delivery timestamp because the interface supplies none.';
  const about = [ref(location), ...forecasts.map(ref)];
  const alertResource = add(resource('Communication', ['alert', alert.alert_id, alert.origin_date, alert.forecast_refs], text, {
    status: 'preparation', category: [cc('confirm-temperature-and-measure-do')], about, sender: ref(org), recipient: [ref(coordinator)], payload: [{ contentString: text }],
    note: [{ text: 'Application review state: acknowledged. Communication remains preparation: transport/delivery is not asserted.' }],
  }));
  const ackResource = add(resource('Communication', ['ack', alert.alert_id, ack], 'DEMO acknowledgement by ' + ack.by + '. ' + ack.note, {
    status: 'completed', category: [cc('acknowledgement')], inResponseTo: [ref(alertResource)], about,
    sent: ack.at, sender: ref(coordinator), recipient: [ref(org)], payload: [{ contentString: 'Acknowledged by demo actor ' + ack.by + ': ' + ack.note }],
    note: [{ text: 'Records the supplied acknowledgement event, not authenticated identity, external message delivery, or completed sampling.' }],
  }));
  const related = forecasts.filter(f => f.effectivePeriod.start === measurementDay);
  const identity = { alert: alertResource.id, acknowledgement: ackResource.id, at: m.measured_at, recorded, by: ack.by,
    temp: String(m.temp_c), oxygen: String(m.do_mg_l), saturation: m.do_pct === undefined ? null : String(m.do_pct), note: m.note ?? '' };
  const rows: [string, number, string, string][] = [
    ['field-water-temperature', m.temp_c, 'Cel', '°C'], ['field-dissolved-oxygen', m.do_mg_l, 'mg/L', 'mg/L'],
  ];
  if (m.do_pct !== undefined) rows.push(['field-do-saturation', m.do_pct, '%', '%']);
  const demoText = 'DEMO user-entered spot measurement; no actual field visit, authenticated operator, external delivery or health assessment is asserted. A spot temperature is not the forecast daily mean. Source-clock alignment is UNVERIFIED.';
  const measurements = rows.map(([code, value, unitCode, unit]) => add(resource('Observation', ['field-check', identity, code], demoText, {
    meta: { profile: [BASE + '/StructureDefinition/streampulse-field-check-observation'], tag: [{ system: CS, code: 'field-check-demo' }] },
    status: 'final', code: cc(code), subject: ref(location), performer: [ref(coordinator)], effectiveDateTime: m.measured_at,
    valueQuantity: { value, system: UCUM, code: unitCode, unit },
    note: [{ text: demoText }, { text: 'Workflow context (not numerical derivation): alert ' + ref(alertResource).reference + '; acknowledgement ' + ref(ackResource).reference + '; forecast(s) ' + related.map(f => ref(f).reference).join(', ') + '. Entered by demo actor ' + ack.by + '.' }, { text: m.note?.trim() || 'No measurement note supplied.' }],
  })));
  add(resource('Provenance', ['field-check', identity], demoText, {
    target: measurements.map(ref), recorded, occurredDateTime: m.measured_at,
    activity: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v3-DataOperation', code: 'CREATE', display: 'create' }] },
    agent: [{ who: ref(coordinator) }],
  }));
  const entry = [...records.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([fullUrl, r]) => ({ fullUrl, resource: r }));
  for (const reference of allReferences(entry)) requireValue(records.has(reference), 'Unresolved FHIR reference: ' + reference);
  return { resourceType: 'Bundle', id: identifier('Bundle', ['field-check', identity, entry.map(e => e.fullUrl)]), type: 'collection',
    meta: { tag: [{ system: CS, code: 'field-check-demo', display: 'Demonstration field check; no external delivery' }] }, entry };
}
