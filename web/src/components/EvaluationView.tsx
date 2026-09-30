import type { ModelId, Replay } from "../types";
import { View, MODEL_LABEL, MODEL_SHORT, fmtC, pct } from "../lib/data";
import { linear, niceTicks, pathOf, useWidth } from "../lib/useWidth";

const ORDER: ModelId[] = ["weather_corr_v1", "water_ridge_v1", "persistence", "climatology"];
const COLOR: Record<ModelId, string> = {
  weather_corr_v1: "var(--accent)",
  water_ridge_v1: "#7c8fd6",
  persistence: "var(--pers)",
  climatology: "var(--clim)",
};
const DASH: Record<ModelId, string | undefined> = { weather_corr_v1: undefined, water_ridge_v1: "6 3", persistence: "2 3", climatology: "8 3 2 3" };

export function EvaluationView({ v }: { v: View }) {
  const M = v.d.metrics;
  const ph = String(v.d.timing.primary_lead);
  const p = M[ph].models;
  const prod = v.d.product_model;
  const val = v.d.validation;
  const valSkill = val.mae.full != null && val.mae.persistence ? 1 - val.mae.full / val.mae.persistence : null;
  const w = p[prod]!.watch;
  const nPass = v.d.gate.criteria.filter((c) => c.passed).length;
  const mon = v.d.monthly ?? [];
  const worst = mon.reduce((a, b) => (b.skill < a.skill ? b : a), mon[0]);
  const best = mon.reduce((a, b) => (b.skill > a.skill ? b : a), mon[0]);
  const swing = mon.length
    ? `, and it swings by month: from ${pct(worst.skill)} in ${monthName(worst.month)} to ${pct(best.skill)} in ${monthName(best.month)}`
    : "";

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="kpis">
        <div className="card kpi">
          <div className="sub">Day-3 error, 2025 test (n={M[ph].n})</div>
          <div className="big num">{fmtC(p[prod]!.mae, 2)}</div>
          <div className="sub">vs persistence {fmtC(p.persistence!.mae, 2)} · climatology {fmtC(p.climatology!.mae, 2)}</div>
        </div>
        <div className="card kpi">
          <div className="sub">Day-3 skill vs persistence</div>
          <div className="big num">{pct(p[prod]!.skill)}</div>
          <div className="sub">2024 validation: {pct(valSkill, 1)} · future skill is unverified</div>
        </div>
        <div className="card kpi">
          <div className="sub">Go/no-go gate (frozen)</div>
          <div className={`big ${v.d.gate.passed ? "pass" : "fail"}`}>{v.d.gate.passed ? "GO" : "NO-GO"}</div>
          <div className="sub">{nPass}/{v.d.gate.criteria.length} criteria passed</div>
        </div>
        <div className="card kpi">
          <div className="sub">Day-3 thermal watch</div>
          <div className="big num">{pct(w.precision)} <span className="sub">precision</span></div>
          <div className="sub">recall {pct(w.recall)} · false-positive rate {pct(w.false_positive_rate)} · {M[ph].episodes} episodes</div>
        </div>
      </div>

      <div className="grid cols-main">
        <div className="card">
          <h2>Mean absolute error by lead time, 2025 test</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            All four methods scored on the same paired days within each lead. Lower is better. Days 4–7 are exploratory and were not used for any decision.
          </p>
          <SkillChart v={v} />
        </div>
        <div className="card">
          <h2>How to read this</h2>
          <ul className="notes small">
            <li><b>Persistence</b> says tomorrow equals yesterday. It is hard to beat for a large river with thermal inertia.</li>
            <li><b>Water-only</b> ridge learns from the last 7 days and the seasonal cycle (trained 2010–2023).</li>
            <li><b>StreamPulse</b> adds one physical signal: ECMWF's forecast air temperature for the target window, relative to today's water temperature.</li>
            <li>The recorded 2025 test opening follows <code>frozen_selection.json</code>. These local records are not independent preregistration.</li>
          </ul>
        </div>
      </div>

      <div className="card">
        <h2>Frozen go/no-go gate (lead {v.d.gate.primary_lead}, product <code>{v.d.gate.product_model}</code>)</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Criterion</th><th>Result</th><th>Pass</th></tr></thead>
            <tbody>
              {v.d.gate.criteria.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.name}</td>
                  <td className="num small">{fmtVal(c.value)}</td>
                  <td className={c.passed ? "pass" : "fail"} style={{ whiteSpace: "nowrap" }}>{c.passed ? "✓ yes" : "✗ no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(320px, 100%), 1fr))" }}>
        <div className="card">
          <h2>Point accuracy, 2025 test</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Lead</th>{ORDER.map((m) => <th key={m} className="r">{MODEL_SHORT[m]}</th>)}<th className="r">Skill</th></tr></thead>
              <tbody>
                {v.d.leads.map((h) => {
                  const r = M[String(h)];
                  return (
                    <tr key={h} style={h > 3 ? { color: "var(--muted)" } : undefined}>
                      <td>+{h}{h > 3 ? "*" : ""}</td>
                      {ORDER.map((m) => <td key={m} className="r num">{r.models[m]?.mae.toFixed(2) ?? "–"}</td>)}
                      <td className="r num"><b>{pct(r.models[prod]?.skill)}</b></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="small faint">MAE in °C. Skill = 1 − MAE / MAE(persistence). *exploratory. Day-3 bias {fmtC(p[prod]!.bias, 2)} (2025 ran warmer than the model expected).</p>
        </div>

        <div className="card">
          <h2>Thermal watch and 90% intervals</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Lead</th><th className="r">TP</th><th className="r">FP</th><th className="r">FN</th><th className="r">TN</th><th className="r">Precision</th><th className="r">Recall</th><th className="r">PI90 cover</th><th className="r">Width</th></tr></thead>
              <tbody>
                {v.d.timing.product_leads.map((h) => {
                  const r = M[String(h)].models[prod]!;
                  return (
                    <tr key={h}>
                      <td>+{h}</td>
                      <td className="r num">{r.watch.tp}</td><td className="r num">{r.watch.fp}</td>
                      <td className="r num">{r.watch.fn}</td><td className="r num">{r.watch.tn}</td>
                      <td className="r num">{pct(r.watch.precision)}</td><td className="r num">{pct(r.watch.recall)}</td>
                      <td className="r num">{pct(r.coverage)}</td><td className="r num">{r.width.toFixed(1)}°</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="small faint">
            Watch = forecast daily mean ≥ that calendar day's 90th percentile (2010–2023, ±15-day window). {M[ph].episodes} observed exceedance
            episodes in the test window, so these rates rest on few events. Intervals come from 2024 out-of-sample residuals and turned out wider than needed.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>Day-3 skill by month, 2025</h2>
        <p className="small muted" style={{ marginTop: 0 }}>
          Same paired days as above, split by target month. Bars left of zero mean StreamPulse did worse than persistence that month.
        </p>
        <MonthlyChart rows={mon} />
      </div>

      {v.d.context && <WarmDays ctx={v.d.context} />}

      <div className="card">
        <h2>Limits we report, not hide</h2>
        <ul className="notes small">
          <li>One station, one river. This is a historical proof of concept, not a validated operational service.</li>
          <li>Skill on 2025 ({pct(p[prod]!.skill)}) is higher than on 2024 validation ({pct(valSkill, 1)}){swing}. These periods do not bound future performance.</li>
          <li>Recall of the watch is modest ({pct(w.recall)} at day 3): it catches fewer than half of warm-anomaly days. Persistence recall is {pct(p.persistence!.watch.recall)} with precision {pct(p.persistence!.watch.precision)}; improved temperature MAE does not establish better field decisions.</li>
          <li>ECMWF inputs are archived runs from the Open-Meteo Single Runs API (early coverage may be reprocessed hindcasts), so this is a reforecast evaluation.</li>
          <li>Station record has a gap from Aug 2018 to Jan 2021 and ends on {v.d.qc.last_date}. Gaps are never interpolated.</li>
          <li>With a 24-hour data delay the day-3 skill stays at {pct(v.d.delay1[prod]?.skill)}.</li>
        </ul>
      </div>
      <p className="small faint">Selected on validation: <code>{val.selected}</code> weather correction (day-3 MAE {val.mae.full?.toFixed(3)} °C vs water-only {val.mae.water_only?.toFixed(3)}, intercept-only {val.mae.intercept_only?.toFixed(3)}, persistence {val.mae.persistence?.toFixed(3)}; {val.rows} rows, folds {val.folds[0]} → {val.folds[val.folds.length - 1]}). Models: {ORDER.map((m) => MODEL_LABEL[m]).join(" · ")}.</p>
    </div>
  );
}

function fmtVal(x: unknown): string {
  if (typeof x === "number") return Number.isInteger(x) ? String(x) : x.toFixed(3);
  if (x && typeof x === "object") {
    return Object.entries(x as Record<string, unknown>)
      .map(([k, val]) => {
        if (val && typeof val === "object" && "lo" in (val as object)) {
          const b = val as { lo: number; hi: number; block_days: number };
          return `${b.block_days}-day blocks [${b.lo.toFixed(3)}, ${b.hi.toFixed(3)}]`;
        }
        return `${k}=${typeof val === "number" ? (Number.isInteger(val) ? val : val.toFixed(3)) : String(val)}`;
      })
      .join(" · ");
  }
  return String(x);
}

function SkillChart({ v }: { v: View }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const H = 260;
  const m = { l: 40, r: 16, t: 14, b: 34 };
  const leads = v.d.leads;
  const vals = leads.flatMap((h) => ORDER.map((mm) => v.d.metrics[String(h)].models[mm]?.mae ?? NaN)).filter(Number.isFinite);
  const hi = Math.ceil(Math.max(...vals) * 4) / 4 + 0.1;
  const x = linear(1, leads.length, m.l + 16, width - m.r - 16);
  const y = linear(0, hi, H - m.b, m.t);
  return (
    <div className="chart" ref={ref}>
      <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label="Mean absolute error by lead time for four methods; StreamPulse lowest at every lead.">
        <rect x={(x(3) + x(4)) / 2} y={m.t} width={width - m.r - (x(3) + x(4)) / 2} height={H - m.t - m.b} fill="var(--surface-2)" />
        {niceTicks(0, hi, 5).map((t) => (
          <g key={t}>
            <line className="gridline" x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} />
            <text x={m.l - 6} y={y(t) + 4} textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={m.l - 6} y={m.t - 2} textAnchor="end">°C</text>
        {leads.map((h) => <text key={h} x={x(h)} y={H - 14} textAnchor="middle">{width < 560 ? `+${h}` : `day +${h}`}</text>)}
        {ORDER.map((mm) => (
          <g key={mm}>
            <path d={pathOf(leads.map((h) => [x(h), y(v.d.metrics[String(h)].models[mm]?.mae ?? NaN)]))} fill="none"
              stroke={COLOR[mm]} strokeWidth={mm === "weather_corr_v1" ? 3 : 2} strokeDasharray={DASH[mm]} />
            {leads.map((h) => {
              const val = v.d.metrics[String(h)].models[mm]?.mae;
              return val == null ? null : <circle key={h} cx={x(h)} cy={y(val)} r={3} fill={COLOR[mm]}><title>{`${MODEL_SHORT[mm]}, day +${h}: ${val.toFixed(2)} °C`}</title></circle>;
            })}
          </g>
        ))}
      </svg>
      <div className="legend">
        {ORDER.map((mm) => (
          <span key={mm}><i className="sw line" style={{ background: COLOR[mm] }} /> {MODEL_SHORT[mm]}</span>
        ))}
        <span><i className="sw" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }} /> exploratory leads</span>
      </div>
    </div>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
function monthName(ym: string) { return MONTHS_LONG[+ym.slice(5, 7) - 1]; }

function MonthlyChart({ rows }: { rows: Replay["monthly"] }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  if (!rows.length) return null;
  const rowH = 26;
  const narrow = width < 560;
  const m = { l: 44, r: narrow ? 48 : 190, t: 8, b: 22 };
  const H = m.t + rows.length * rowH + m.b;
  const lo = Math.min(-0.3, ...rows.map((r) => r.skill));
  const hi = Math.max(0.7, ...rows.map((r) => r.skill));
  const x = linear(lo, hi, m.l, width - m.r);
  const ticks = niceTicks(lo, hi, 5);
  return (
    <div className="chart" ref={ref}>
      <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label={`Day-3 skill versus persistence by month: ${rows.map((r) => `${MONTHS[+r.month.slice(5, 7) - 1]} ${pct(r.skill)}`).join(", ")}.`}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="gridline" x1={x(t)} x2={x(t)} y1={m.t} y2={H - m.b} />
            <text x={x(t)} y={H - 6} textAnchor="middle">{Math.round(t * 100)}%</text>
          </g>
        ))}
        <line x1={x(0)} x2={x(0)} y1={m.t} y2={H - m.b} stroke="var(--text)" strokeWidth={1} />
        {rows.map((r, i) => {
          const yy = m.t + i * rowH + 4;
          const x0 = x(Math.min(0, r.skill));
          const w = Math.abs(x(r.skill) - x(0));
          return (
            <g key={r.month}>
              <text x={m.l - 8} y={yy + 13} textAnchor="end">{MONTHS[+r.month.slice(5, 7) - 1]}</text>
              <rect x={x0} y={yy} width={Math.max(w, 1)} height={rowH - 10} rx={3} fill={r.skill >= 0 ? "var(--accent)" : "var(--watch)"}>
                <title>{`${monthName(r.month)}: skill ${pct(r.skill)}, MAE ${r.mae.toFixed(2)} vs persistence ${r.mae_persistence.toFixed(2)} °C, n=${r.n}`}</title>
              </rect>
              <text x={width - m.r + 8} y={yy + 13} className="num">{narrow ? pct(r.skill) : `${pct(r.skill)} · ${r.mae.toFixed(2)} vs ${r.mae_persistence.toFixed(2)} °C · n=${r.n}`}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function WarmDays({ ctx }: { ctx: NonNullable<View["d"]["context"]> }) {
  const leads = ["1", "2", "3"];
  const thr = ctx.salmon_threshold_c;
  return (
    <div className="card">
      <h2>Warm days, and a threshold we did not choose <span className="chip">exploratory · post-hoc</span></h2>
      <p className="small muted" style={{ marginTop: 0 }}>
        The watch line is statistical (unusual for the season). Two checks against outside evidence, computed afterwards from the frozen 2025 forecasts with no fitting or tuning.
      </p>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(320px, 100%), 1fr))" }}>
        <div>
          <h3>Error when the river is warm</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Lead</th><th className="r">Days &gt; 18 °C</th><th className="r">StreamPulse MAE</th><th className="r">Persistence MAE</th><th className="r">Skill</th></tr></thead>
              <tbody>
                {leads.map((h) => {
                  const s = ctx.leads[h]?.strata?.above_18;
                  const a = s?.weather_corr_v1?.mae, b = s?.persistence?.mae;
                  return (
                    <tr key={h}>
                      <td>+{h}</td><td className="r num">{s?.n ?? "–"}</td>
                      <td className="r num"><b>{a?.toFixed(2) ?? "–"}</b></td><td className="r num">{b?.toFixed(2) ?? "–"}</td>
                      <td className="r num">{a != null && b ? pct(1 - a / b) : "–"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="small faint">
            In a multi-site deep-learning study, persistence had better RMSE and bias than the models above 18 °C (Zwart et al. 2023, Frontiers in Water). Here the advantage holds on warm days (day-3 RMSE {ctx.leads["3"]?.strata?.above_18?.weather_corr_v1?.rmse?.toFixed(2)} vs {ctx.leads["3"]?.strata?.above_18?.persistence?.rmse?.toFixed(2)} °C).
            Different rivers and methods, so this is context, not a head-to-head. Strata split on the observed value.
          </p>
        </div>
        <div>
          <h3>Garonne salmon limit: {thr} °C</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Lead</th><th className="r">Days ≥ {thr} °C</th><th className="r">Forecast reached {thr}</th><th className="r">False calls</th><th className="r">Persistence reached</th><th className="r">False calls</th></tr></thead>
              <tbody>
                {leads.map((h) => {
                  const s = ctx.leads[h]?.salmon;
                  return (
                    <tr key={h}>
                      <td>+{h}</td><td className="r num">{s?.hot_days}</td>
                      <td className="r num"><b>{s?.weather_corr_v1.reached_on_hot_days}</b></td><td className="r num"><b>{s?.weather_corr_v1.reached_on_cooler_days}</b></td>
                      <td className="r num">{s?.persistence.reached_on_hot_days}</td><td className="r num">{s?.persistence.reached_on_cooler_days}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="small faint">
            Larnier et al. (2010, Knowl. Managt. Aquatic Ecosyst.) give {thr} °C as the upper limit for Atlantic salmon migration on the Garonne, where most recorded salmon mortalities occurred.
            StreamPulse almost never calls {thr} °C when the river stays below it; persistence catches a few more hot days with more false calls. Not a biological validation.
          </p>
        </div>
      </div>
    </div>
  );
}
