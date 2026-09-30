import { useState } from "react";
import type { Network } from "../types";
import { fmtC, pct } from "../lib/data";
import { addDays, fmtDay } from "../lib/time";

interface Props { net: Network; oi: number; origin: string; onPick: (code: string) => void }

/** Ranks stations for a fixed daily visit budget using forecast margin above each site's watch line. */
export function VisitPlanner({ net, oi, origin, onPick }: Props) {
  const [lead, setLead] = useState(1);
  const [k, setK] = useState(1);
  const [reveal, setReveal] = useState(false);

  const rows = net.stations
    .filter((s) => s.status === "ok")
    .map((s) => {
      const c = oi >= 0 ? net.replay[s.code_station]?.[oi]?.[lead - 1] ?? null : null;
      const margin = c && c[1] != null ? c[0] - c[1] : null;
      return { s, c, margin };
    })
    .sort((a, b) => (b.margin ?? -99) - (a.margin ?? -99));
  const plan = rows.filter((r) => r.margin != null && r.margin >= 0).slice(0, k);
  const planned = new Set(plan.map((r) => r.s.code_station));
  const target = addDays(origin, lead);
  const b = net.budget?.leads?.[String(lead)];
  const bk = b?.budgets?.[String(k)] ?? b?.budgets?.[String(Math.min(k, 2))];

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
        <h2 style={{ margin: 0 }}>Field-visit planner</h2>
        <span className="spacer" />
        <div className="seg" role="group" aria-label="Forecast lead">
          {[1, 2, 3].map((h) => <button key={h} aria-pressed={lead === h} onClick={() => setLead(h)}>Day +{h}</button>)}
        </div>
        <div className="seg" role="group" aria-label="Visits available per day">
          {[1, 2].map((n) => <button key={n} aria-pressed={k === n} onClick={() => setK(n)}>{n} team{n > 1 ? "s" : ""}</button>)}
        </div>
      </div>
      <p className="small muted" style={{ marginTop: 0 }}>
        Issued {fmtDay(origin, true)} for {fmtDay(target, true)}. With {k} visit{k > 1 ? "s" : ""} a day, rank rivers by how far the forecast sits
        above that river's own seasonal 90th-percentile line and send teams to the top {k} that reach it. A visit means: confirm temperature, measure dissolved oxygen.
      </p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Rank</th><th>River</th><th className="r">Forecast</th><th className="r">Watch line</th><th className="r">Margin</th><th>Plan</th>{reveal && <th className="r">Observed</th>}</tr></thead>
          <tbody>
            {rows.map((r, i) => {
              const go = planned.has(r.s.code_station);
              const hit = r.c && r.c[1] != null && r.c[3] != null ? r.c[3] >= r.c[1] : null;
              return (
                <tr key={r.s.code_station} onClick={() => onPick(r.s.code_station)} style={{ cursor: "pointer", background: go ? "var(--watch-soft)" : undefined }}>
                  <td className="num">{r.margin == null ? "–" : i + 1}</td>
                  <td>{r.s.name}{r.s.primary ? " ★" : ""}</td>
                  <td className="r num">{r.c ? fmtC(r.c[0]) : "no forecast"}</td>
                  <td className="r num">{r.c && r.c[1] != null ? fmtC(r.c[1]) : "–"}</td>
                  <td className="r num">{r.margin == null ? "–" : `${r.margin >= 0 ? "+" : ""}${r.margin.toFixed(1)} °C`}</td>
                  <td>{go ? <span className="chip watch">▲ visit</span> : r.margin != null && r.margin >= 0 ? <span className="small muted">over budget</span> : <span className="small muted">no visit</span>}</td>
                  {reveal && <td className="r num">{r.c?.[3] != null ? <span className={hit ? "pass" : "muted"}>{r.c[3].toFixed(1)} {hit ? "✓ above line" : "below"}</span> : "–"}</td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <label className="small row" style={{ gap: 6, marginTop: 8 }}>
        <input type="checkbox" checked={reveal} onChange={(e) => setReveal(e.target.checked)} /> Show what actually happened
      </label>
      {plan.length === 0 && <p className="small muted">No river is forecast above its watch line for this lead: no visit is proposed today.</p>}

      {bk && b && (
        <>
          <h3 style={{ marginTop: 16 }}>Whole 2025 season with this budget <span className="chip">exploratory · post-hoc</span></h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Ranking by</th><th className="r">Visits made</th><th className="r">On an exceedance day</th><th className="r">Wasted trips</th><th className="r">Hit rate</th><th className="r">Exceedances visited</th></tr></thead>
              <tbody>
                {(["streampulse", "persistence"] as const).map((m) => {
                  const x = bk[m];
                  return (
                    <tr key={m}>
                      <td>{m === "streampulse" ? <b>StreamPulse forecast</b> : "Persistence (yesterday's value)"}</td>
                      <td className="r num">{x.visits}</td>
                      <td className="r num">{x.hits}</td>
                      <td className="r num">{x.wasted}</td>
                      <td className="r num">{pct(x.hit_rate)}</td>
                      <td className="r num">{pct(x.share_of_exceedances_visited)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="small faint">
            {b.paired_days} issue dates where every river had a forecast, persistence value and observation; {b.exceedance_station_days} river-days observed above the line.
            Not pre-registered: computed afterwards from the frozen 2025 forecasts, with no fitting or tuning. Days are correlated and the network has four rivers, so read this as descriptive.
            Source: <code>reports/exploratory/visit_budget.json</code>.
          </p>
        </>
      )}
    </div>
  );
}
