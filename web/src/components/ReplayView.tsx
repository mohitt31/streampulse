import { useEffect, useState } from "react";
import { View, fmtC, MODEL_LABEL } from "../lib/data";
import { addDays, daysBetween, fmtDay, fmtDayLong, todayUtc } from "../lib/time";
import { ForecastChart } from "./ForecastChart";
import { SeasonChart } from "./SeasonChart";
import { AlertPanel, type Acks } from "./AlertPanel";

interface Props {
  v: View;
  originIdx: number;
  setOriginIdx: (i: number) => void;
  acks: Acks;
  onAck: (id: string, a: Acks[string]) => void;
}

export function ReplayView({ v, originIdx, setOriginIdx, acks, onAck }: Props) {
  const [mode, setMode] = useState<"replay" | "live">("replay");
  const [playing, setPlaying] = useState(false);
  const [showOutcome, setShowOutcome] = useState(true);
  const [showBaselines, setShowBaselines] = useState(false);
  const [showExplore, setShowExplore] = useState(false);
  const n = v.d.origins.length;
  const model = v.d.product_model;

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setOriginIdx(Math.min(originIdx + 1, n - 1)), 450);
    if (originIdx >= n - 1) setPlaying(false);
    return () => clearInterval(t);
  }, [playing, originIdx, n, setOriginIdx]);

  const live = mode === "live";
  const idx = live ? n - 1 : originIdx;
  const origin = v.d.origins[idx];
  const meta = v.d.meta[idx];
  const lastObs = addDays(origin, -1);
  const today = todayUtc();
  const newest = v.lastObsDate;
  const age = daysBetween(newest, today);

  const nextAlert = () => {
    const i = v.d.origins.findIndex((o, j) => j > originIdx && v.alertFor(o));
    if (i >= 0) setOriginIdx(i);
  };
  const prevAlert = () => {
    for (let j = originIdx - 1; j >= 0; j--) if (v.alertFor(v.d.origins[j])) return setOriginIdx(j);
  };

  const leads = showExplore ? v.d.leads : v.d.timing.product_leads;
  // if the ECMWF run for this day is missing, the product degrades to the water-only model (labelled)
  const eff = v.cell(model, idx, 1) ? model : "water_ridge_v1";

  return (
    <div className="grid cols-main">
      <div className="grid" style={{ gap: 16 }}>
        <div className="card slider-block">
          <div className="row">
            <div className="seg" role="group" aria-label="Mode">
              <button aria-pressed={!live} onClick={() => setMode("replay")}>Historical replay</button>
              <button aria-pressed={live} onClick={() => { setMode("live"); setPlaying(false); }}>Live (today)</button>
            </div>
            <span className="spacer" />
            {!live && (
              <>
                <button className="btn iconbtn" aria-label="Previous day" onClick={() => setOriginIdx(Math.max(0, originIdx - 1))}>‹</button>
                <button className="btn iconbtn" aria-label={playing ? "Pause replay" : "Play replay"} onClick={() => setPlaying(!playing)}>{playing ? "❚❚" : "▶"}</button>
                <button className="btn iconbtn" aria-label="Next day" onClick={() => setOriginIdx(Math.min(n - 1, originIdx + 1))}>›</button>
                <button className="btn" onClick={prevAlert}>‹ Alert</button>
                <button className="btn" onClick={nextAlert}>Alert ›</button>
              </>
            )}
          </div>

          {live ? (
            <div className="stale" role="alert">
              <strong>Inputs are stale: no forecast issued today ({fmtDayLong(today)}).</strong>
              <span className="small">
                The newest usable observation from station {v.d.site.id} is from <b>{fmtDay(newest, true)}</b>, {age} days old.
                StreamPulse only issues a forecast when the previous day's daily mean is complete. The last valid forecast
                ({fmtDay(origin, true)}) is shown greyed out for reference only.
              </span>
            </div>
          ) : (
            <>
              <div className="slider-head">
                <span className="date">{fmtDayLong(origin)}</span>
                <span className="chip warn">REPLAY · simulated issuance</span>
              </div>
              <input
                type="range" min={0} max={n - 1} value={originIdx}
                onChange={(e) => setOriginIdx(+e.target.value)}
                aria-label="Forecast issue date" aria-valuetext={fmtDayLong(origin)}
              />
              <div className="issuance">
                Issued <b>{fmtDay(origin, true)} 12:00 UTC</b> · water observations through <b>{fmtDay(lastObs)}</b>{" "}
                ({meta.inputs.length}/7 days in window) · air forecast{" "}
                {meta.run ? <b>ECMWF IFS run {fmtDay(meta.run.slice(0, 10))} 00 UTC</b> : <b>unavailable (water-only fallback)</b>}
              </div>
            </>
          )}
        </div>

        <div className="leads" aria-live="polite">
          {leads.map((h) => {
            const c = v.cell(eff, idx, h);
            const target = addDays(origin, h);
            const obs = v.obs(target);
            const p90 = v.p90(target);
            const exploratory = h > 3;
            return (
              <div key={h} className={`lead ${c?.[3] && !live && !exploratory ? "watch" : ""}`} style={live ? { opacity: 0.45 } : undefined}>
                <span className="lbl">Day +{h} · {fmtDay(target)}{exploratory ? " · exploratory" : ""}</span>
                <span className="val num">{fmtC(c?.[0] ?? null)}</span>
                <span className="rng num">90% range {c?.[1] != null ? `${c[1].toFixed(1)}–${c[2]!.toFixed(1)} °C` : "–"}</span>
                <span className="rng num">watch line {fmtC(p90)}</span>
                {live ? (
                  <span className="chip neutral">withheld</span>
                ) : c?.[3] ? (
                  <span className="chip watch">▲ Above watch line</span>
                ) : (
                  <span className="chip ok">● Below watch line</span>
                )}
                {showOutcome && !live && obs != null && c && (
                  <span className="outcome num">Actual {obs.toFixed(1)} °C (error {(c[0] - obs >= 0 ? "+" : "") + (c[0] - obs).toFixed(1)})</span>
                )}
              </div>
            );
          })}
        </div>

        <div className="card">
          <div className="row" style={{ marginBottom: 6 }}>
            <h2 style={{ margin: 0 }}>{MODEL_LABEL[eff]}{eff !== model && <span className="chip warn" style={{ marginLeft: 8 }}>fallback: ECMWF run missing</span>}</h2>
            <span className="spacer" />
            <label className="check"><input type="checkbox" checked={showOutcome} onChange={(e) => setShowOutcome(e.target.checked)} /> What actually happened</label>
            <label className="check"><input type="checkbox" checked={showBaselines} onChange={(e) => setShowBaselines(e.target.checked)} /> Baselines</label>
            <label className="check"><input type="checkbox" checked={showExplore} onChange={(e) => setShowExplore(e.target.checked)} /> Days 4–7 cards</label>
          </div>
          <ForecastChart v={v} originIdx={idx} model={eff} showOutcome={showOutcome && !live} showBaselines={showBaselines} stale={live} />
        </div>

        <div className="card">
          <h2>2025 season at a glance <span className="muted small">(click to jump)</span></h2>
          <SeasonChart v={v} originIdx={idx} onPick={(i) => { setMode("replay"); setOriginIdx(i); }} />
        </div>
      </div>

      <AlertPanel v={v} originIdx={idx} acks={acks} onAck={onAck} onPick={(i) => { setMode("replay"); setOriginIdx(i); }} disabled={live} />
    </div>
  );
}
