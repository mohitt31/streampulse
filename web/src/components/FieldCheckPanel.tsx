import { useId, useRef, useState } from 'react';
import type { Alert } from '../types';
import { buildFieldCheckBundle, type FieldCheckBundle } from '../lib/fhirFieldCheck';
import { loadFieldCheckContext } from '../lib/fieldCheckContext';

export function FieldCheckPanel({ alert, ack, modelVersion }: {
  alert: Alert; ack: { by: string; at: string; note: string }; modelVersion: string;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [temp, setTemp] = useState('');
  const [oxygen, setOxygen] = useState('');
  const [saturation, setSaturation] = useState('');
  const [time, setTime] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ bundle: FieldCheckBundle; date: string; spot: number; forecast: number } | null>(null);
  const summary = useRef<HTMLDivElement>(null);
  const firstInput = useRef<HTMLInputElement>(null);
  const download = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.bundle, null, 2) + '\n'], { type: 'application/fhir+json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url;
    link.download = `streampulse-field-check-${alert.alert_id.replace(/[^A-Za-z0-9-]/g, '-')}.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <section className="field-check" aria-labelledby={`${id}-title`}>
      <h4 id={`${id}-title`}>Demo field check</h4>
      <p id={`${id}-scope`} className="small">Not sent anywhere. Entries stay in this view until you leave it; download the Bundle to keep a copy. No actual field visit or authenticated identity is claimed.</p>
      {!open ? <button className="btn" type="button" onClick={() => { setOpen(true); requestAnimationFrame(() => firstInput.current?.focus()); }}>Log field check</button> : (
        <form className="form" aria-label="Log demo field check" aria-describedby={`${id}-scope ${id}-time-help`} onSubmit={async event => {
          event.preventDefault(); setError(''); setBusy(true);
          try {
            if (!temp.trim() || !oxygen.trim() || !time) throw new Error('Temperature, dissolved oxygen and measurement time are required.');
            const context = await loadFieldCheckContext(alert);
            // datetime-local is explicitly labelled UTC. Do not apply the browser's local timezone.
            const measuredAt = time.length === 16 ? time + ':00Z' : time + 'Z';
            const bundle = buildFieldCheckBundle({ alert, ack, ...context, modelVersion,
              measurements: { temp_c: Number(temp), do_mg_l: Number(oxygen), ...(saturation.trim() ? { do_pct: Number(saturation) } : {}),
                measured_at: measuredAt, recorded_at: new Date().toISOString(), note } });
            const forecast = context.forecasts.find(f => f.effectivePeriod.start === measuredAt.slice(0, 10))!;
            setResult({ bundle, date: measuredAt.slice(0, 10), spot: Number(temp), forecast: forecast.valueQuantity.value });
            requestAnimationFrame(() => summary.current?.focus());
          } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not build the FHIR Bundle.'); }
          finally { setBusy(false); }
        }}>
          <label htmlFor={`${id}-temp`}>Measured water temperature (°C)</label>
          <input ref={firstInput} id={`${id}-temp`} type="number" step="any" min="-273.15" required value={temp} onChange={e => setTemp(e.target.value)} />
          <label htmlFor={`${id}-oxygen`}>Dissolved oxygen (mg/L)</label>
          <input id={`${id}-oxygen`} type="number" step="any" min="0" required value={oxygen} onChange={e => setOxygen(e.target.value)} />
          <label htmlFor={`${id}-saturation`}>DO saturation (%) — optional</label>
          <input id={`${id}-saturation`} type="number" step="any" min="0" value={saturation} onChange={e => setSaturation(e.target.value)} />
          <label htmlFor={`${id}-time`}>Measurement time (UTC, historical demo)</label>
          <input id={`${id}-time`} type="datetime-local" step="1" required aria-describedby={`${id}-time-help`} value={time} onChange={e => setTime(e.target.value)} />
          <p id={`${id}-time-help`} className="small">Enter the measurement time on a forecast target day: {alert.target_dates.join(', ')}. The entered calendar date selects the comparison; the sensor's source-clock alignment is UNVERIFIED.</p>
          <label htmlFor={`${id}-note`}>Field check note — optional</label>
          <textarea id={`${id}-note`} rows={2} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} />
          <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Building Bundle…' : result ? 'Update field check' : 'Save demo field check'}</button>
          {error && <p role="alert" className="small">{error}</p>}
        </form>
      )}
      {result && <div ref={summary} tabIndex={-1} className="field-check-result" aria-label="Field check saved">
        <p role="status"><b>Demo field check saved in this view.</b></p>
        <dl className="small">
          <dt>Target calendar day</dt><dd>{result.date}</dd>
          <dt>Forecast daily mean</dt><dd>{result.forecast.toFixed(2)} °C</dd>
          <dt>Entered spot temperature</dt><dd>{result.spot.toFixed(2)} °C</dd>
          <dt>Spot minus forecast (not a forecast error)</dt><dd>{(result.spot - result.forecast).toFixed(2)} °C</dd>
        </dl>
        <p className="small">A spot reading is not a daily mean. This comparison does not validate forecast skill or infer water safety. No dissolved-oxygen forecast exists.</p>
        <button className="btn primary" type="button" onClick={download}>Download FHIR Bundle</button>
      </div>}
    </section>
  );
}
