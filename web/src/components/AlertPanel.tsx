import { useEffect, useRef, useState } from "react";
import { FieldCheckPanel } from "./FieldCheckPanel";
import type { Alert } from "../types";
import { View, fmtC } from "../lib/data";
import { fmtDay } from "../lib/time";

export type Acks = Record<string, { by: string; at: string; note: string }>;

interface Props {
  v: View;
  originIdx: number;
  acks: Acks;
  onAck: (id: string, ack: { by: string; at: string; note: string }) => void;
  onPick: (i: number) => void;
  disabled?: boolean;
}

export function AlertPanel({ v, originIdx, acks, onAck, onPick, disabled }: Props) {
  const origin = v.d.origins[originIdx];
  const alert = v.alertFor(origin);
  const product = v.d.product_model;
  const listRef = useRef<HTMLUListElement | null>(null);
  useEffect(() => {
    const list = listRef.current;
    const el = list?.querySelector<HTMLElement>('[aria-current="true"]');
    if (list && el) list.scrollTop = Math.max(0, el.offsetTop - 8);
  }, [origin]);
  return (
    <div className="grid" style={{ gap: 12 }}>
      <div className="card">
        <h2>Thermal watch</h2>
        {disabled ? (
          <p className="muted small" style={{ margin: 0 }}>No alert can be raised while inputs are stale.</p>
        ) : !alert && !v.cell(product, originIdx, 1) ? (
          <div className="alert-box off">
            <h3><span aria-hidden="true">!</span> No alert: ECMWF run missing</h3>
            <p className="small muted" style={{ margin: 0 }}>
              The air-temperature run for {fmtDay(origin)} is missing or empty, so the evaluated product model did not run.
              The chart shows the labelled water-only fallback; alerts are raised only by the evaluated model.
            </p>
          </div>
        ) : alert ? (
          <AlertBox key={alert.alert_id} v={v} a={alert} ack={acks[alert.alert_id]} onAck={onAck} product={product} />
        ) : (
          <div className="alert-box off">
            <h3><span aria-hidden="true">●</span> No watch for days +1 to +3</h3>
            <p className="small muted" style={{ margin: 0 }}>
              Forecast daily means stay below the seasonal 90th percentile for {fmtDay(origin)}+1 to +3.
            </p>
          </div>
        )}
      </div>
      <div className="card">
        <h2>2025 alerts <span className="muted small">({v.d.alerts.length})</span></h2>
        <ul className="alert-list" ref={listRef}>
          {v.d.alerts.map((a) => {
            const i = v.d.origins.indexOf(a.origin_date);
            const acked = !!acks[a.alert_id];
            return (
              <li key={a.alert_id}>
                <button aria-current={a.origin_date === origin} onClick={() => i >= 0 && onPick(i)}>
                  <span className="dot" style={{ background: acked ? "var(--ok)" : "var(--watch)" }} aria-hidden="true" />
                  <span className="num" style={{ minWidth: 64 }}>{fmtDay(a.origin_date)}</span>
                  <span className="small muted">targets {a.target_dates.map((t) => fmtDay(t)).join(", ")}</span>
                  <span className="spacer" />
                  <span className={`chip ${acked ? "ok" : "watch"}`}>{acked ? "ack" : "open"}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function AlertBox({ v, a, ack, onAck, product }: {
  v: View; a: Alert; ack?: { by: string; at: string; note: string };
  onAck: Props["onAck"]; product: string;
}) {
  const [by, setBy] = useState("");
  const [note, setNote] = useState("");
  const i = v.d.origins.indexOf(a.origin_date);
  return (
    <div className="alert-box on">
      <h3><span aria-hidden="true">▲</span> Watch: warm anomaly expected</h3>
      <div className="small">
        {a.target_dates.map((t) => {
          const h = Math.round((Date.parse(t) - Date.parse(a.origin_date)) / 86400000);
          const c = v.cell(product as never, i, h);
          return (
            <div key={t} className="num">
              {fmtDay(t)} (day +{h}): <b>{fmtC(c?.[0] ?? null)}</b> vs watch line {fmtC(v.p90(t))}
            </div>
          );
        })}
      </div>
      <div className="small">
        <b>Follow-up:</b> Confirm temperature and measure dissolved oxygen with a trained monitoring team. Biological sampling is an expert decision. This is a proposed follow-up, not an OAH-prescribed alert trigger.
      </div>
      <div className="small muted mono">{a.alert_id}</div>
      {ack ? (
        <>
          <div className="chip ok">✓ Acknowledged by {ack.by} · {new Date(ack.at).toLocaleString()}</div>
          <FieldCheckPanel alert={a} ack={ack} modelVersion={v.d.model_version} />
        </>
      ) : (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!by.trim()) return;
            onAck(a.alert_id, { by: by.trim(), at: new Date().toISOString(), note: note.trim() });
          }}
        >
          <label className="small" htmlFor="ackby">Acknowledge as</label>
          <input id="ackby" placeholder="Name / role (e.g. field technician)" value={by} onChange={(e) => setBy(e.target.value)} />
          <textarea rows={2} placeholder="Note (optional): e.g. DO probe scheduled 07:00" value={note} onChange={(e) => setNote(e.target.value)} aria-label="Acknowledgement note" />
          <button className="btn primary" type="submit" disabled={!by.trim()}>Acknowledge alert</button>
          <span className="faint small">Demo acknowledgement, kept in this browser only. After acknowledgement, log a demo field check and download its FHIR Bundle; nothing is sent to a server.</span>
        </form>
      )}
    </div>
  );
}
