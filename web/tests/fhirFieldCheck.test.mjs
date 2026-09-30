import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildFieldCheckBundle, allReferences, identifier } from '../src/lib/fhirFieldCheck.ts';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sp-field-check-'));
const python = process.env.SP_PYTHON || 'python3';
execFileSync(python, ['scripts/pack_field_check_context.py', '--demo', '--output', path.join(tmp, 'context.json')], { cwd: root });
execFileSync(process.execPath, ['--experimental-strip-types', 'scripts/build_field_check_demo.mjs', path.join(tmp, 'context.json'), tmp], { cwd: root });
const fixture = JSON.parse(fs.readFileSync(path.join(tmp, 'input.json'), 'utf8'));
const code = r => r.code?.coding?.[0]?.code;

test('pure deterministic builder preserves source resources, complete reference closure and profile/unit mapping', () => {
  const before = JSON.stringify(fixture);
  const a = buildFieldCheckBundle(fixture), b = buildFieldCheckBundle(fixture);
  assert.deepEqual(a, b); assert.equal(JSON.stringify(fixture), before);
  const byUrl = new Map(a.entry.map(e => [e.fullUrl, e.resource]));
  assert.equal(byUrl.size, a.entry.length);
  for (const ref of allReferences(a)) assert.ok(byUrl.has(ref), ref);
  for (const forecast of fixture.forecasts) assert.deepEqual(byUrl.get('urn:uuid:' + forecast.id), forecast);
  const checks = a.entry.map(e => e.resource).filter(r => r.meta?.profile?.some(p => p.endsWith('/streampulse-field-check-observation')));
  assert.deepEqual(checks.map(r => r.valueQuantity.code).sort(), ['%', 'Cel', 'mg/L']);
  for (const r of checks) {
    assert.equal(r.effectiveDateTime, fixture.measurements.measured_at);
    assert.equal(r.subject.reference, 'urn:uuid:' + fixture.site.location.id);
    assert.equal(r.performer[0].reference, 'urn:uuid:' + identifier('Organization', 'demo-monitoring'));
    assert.equal(r.basedOn, undefined); assert.equal(r.derivedFrom, undefined);
    assert.ok(r.note.some(n => n.text.includes('Workflow context')));
  }
  const ack = a.entry.find(e => e.resource.inResponseTo)?.resource;
  assert.equal(byUrl.get(ack.inResponseTo[0].reference).resourceType, 'Communication');
});

test('UUIDv5 keys and alert/acknowledgement IDs agree with Python exporter', () => {
  execFileSync(python, ['-c', `import json,sys;sys.path.insert(0,'src');from streampulse.fhir_export import identifier\nfor x in json.load(open(sys.argv[1])): assert identifier(x['kind'],x['key'])==x['id'],x`, path.join(tmp, 'id-vectors.json')], { cwd: root });
});

test('omitted saturation remains absent; valid supersaturation is retained', () => {
  const input = structuredClone(fixture); delete input.measurements.do_pct;
  assert.equal(buildFieldCheckBundle(input).entry.filter(e => code(e.resource) === 'field-do-saturation').length, 0);
  assert.equal(buildFieldCheckBundle(fixture).entry.find(e => code(e.resource) === 'field-do-saturation').resource.valueQuantity.value, 104);
});

test('rejects invalid measurements, times, contexts and missing references', () => {
  const cases = [
    x => { x.measurements.temp_c = NaN; }, x => { x.measurements.do_mg_l = -1; },
    x => { x.measurements.do_pct = Infinity; }, x => { x.measurements.measured_at = '2025-06-21T10:30:00'; },
    x => { x.measurements.measured_at = '2025-02-30T10:30:00Z'; },
    x => { x.measurements.measured_at = '2025-01-01T10:30:00Z'; },
    x => { x.measurements.measured_at = '2099-06-21T10:30:00Z'; },
    x => { x.ack.at = '2020-01-01T00:00:00Z'; }, x => { x.ack.by = ' '; },
    x => { x.modelVersion = 'abcdef0'; }, x => { x.site.location.id = 'wrong'; },
    x => { x.site.supportingResources = []; }, x => { x.forecasts.push(x.forecasts[0]); },
    x => { x.forecasts[0].subject.reference = 'urn:uuid:wrong'; },
  ];
  for (const mutate of cases) { const input = structuredClone(fixture); mutate(input); assert.throws(() => buildFieldCheckBundle(input)); }
});

test('untrusted notes are escaped in XHTML and are text, never executable markup', () => {
  const input = structuredClone(fixture); input.ack.by = '<img src=x onerror=alert(1)>'; input.measurements.note = '<script>alert(1)</script>';
  const result = buildFieldCheckBundle(input);
  assert.ok(result.entry.every(e => !e.resource.text?.div.includes('<img')));
  assert.ok(result.entry.every(e => !e.resource.text?.div.includes('<script')));
});
