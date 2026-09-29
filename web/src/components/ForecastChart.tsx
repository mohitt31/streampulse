import { useMemo, useState } from "react";
import type { ModelId } from "../types";
import { View, fmtC, MODEL_SHORT } from "../lib/data";
import { addDays, daysBetween, fmtDay, fmtDayLong } from "../lib/time";
import { linear, niceTicks, pathOf, useWidth } from "../lib/useWidth";

interface Props {
  v: View;
  originIdx: number;
  model: ModelId;
  showOutcome: boolean;
  showBaselines: boolean;
  stale?: boolean;
  history?: number;
}

export function ForecastChart({ v, originIdx, model, showOutcome, showBaselines, stale = false, history = 21 }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const origin = v.d.origins[originIdx];
  const lastObs = addDays(origin, -1);
  const start = addDays(origin, -history);
  const end = addDays(origin, 7);
  const nDays = daysBetween(start, end);
  const dates = useMemo(() => Array.from({ length: nDays + 1 }, (_, i) => addDays(start, i)), [start, nDays]);

  const H = width < 560 ? 270 : 330;
  const m = { l: 40, r: 14, t: 18, b: 30 };

  const fc = v.d.leads.map((h) => ({ h, date: addDays(origin, h), c: v.cell(model, originIdx, h) }));
  const pers = v.cell("persistence", originIdx, 1)?.[0] ?? null;
  const climC = v.d.leads.map((h) => v.cell("climatology", originIdx, h)?.[0] ?? null);

  const ys: number[] = [];
  dates.forEach((d) => {
    const o = v.obs(d);
    if (o != null && (d <= lastObs || showOutcome)) ys.push(o);
    const p = v.p90(d);
    if (p != null) ys.push(p);
  });
  fc.forEach(({ c }) => c && ys.push(c[0], c[1] ?? c[0], c[2] ?? c[0]));
  if (showBaselines) climC.forEach((c) => c != null && ys.push(c));
  const lo = Math.floor(Math.min(...ys) - 0.5);
  const hi = Math.ceil(Math.max(...ys) + 0.5);

  const x = linear(0, nDays, m.l, width - m.r);
  const xd = (d: string) => x(daysBetween(start, d));
  const y = linear(lo, hi, H - m.b, m.t);
  const X0 = xd(origin) + (x(1) - x(0)) * 0.5; // issuance at 12:00 UTC

  const obsPath = pathOf(dates.filter((d) => d <= lastObs).map((d) => [xd(d), v.obs(d) == null ? null : y(v.obs(d)!)]));
  const outcomeDates = dates.filter((d) => d >= origin);
  const p90Path = pathOf(dates.map((d) => [xd(d), v.p90(d) == null ? null : y(v.p90(d)!)]));
  const lastVal = v.obs(lastObs);
  const meanPts: [number, number | null][] = [
    ...(lastVal != null ? [[xd(lastObs), y(lastVal)] as [number, number]] : []),
    ...fc.map(({ date, c }) => [xd(date), c ? y(c[0]) : null] as [number, number | null]),
  ];
  const band = (from: number, to: number) => {
    const seg = fc.filter(({ h, c }) => h >= from && h <= to && c && c[1] != null && c[2] != null);
    if (seg.length < 2) return "";
    const top = seg.map(({ date, c }) => `${xd(date).toFixed(1)},${y(c![2]!).toFixed(1)}`);
    const bot = seg.slice().reverse().map(({ date, c }) => `${xd(date).toFixed(1)},${y(c![1]!).toFixed(1)}`);
    return `M${top.join("L")}L${bot.join("L")}Z`;
  };
  const xExplore = xd(addDays(origin, 3)) + (x(1) - x(0)) * 0.5;
  const yt = niceTicks(lo, hi, 5);
  const step = width < 560 ? 7 : width < 800 ? 4 : 3;
  const xt = dates.filter((_, i) => (nDays - i) % step === 0);

  const hoverDate = hover != null ? dates[hover] : null;
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * width;
    const i = Math.round(((px - m.l) / (width - m.l - m.r)) * nDays);
    setHover(i >= 0 && i <= nDays ? i : null);
  };

  const opacity = stale ? 0.35 : 1;
  const summary = fc
    .filter(({ h }) => h <= 3)
    .map(({ h, c }) => `day ${h}: ${c ? c[0].toFixed(1) : "n/a"} °C`)
    .join(", ");

  return (
    <div className="chart" ref={ref}>
      <svg
        viewBox={`0 0 ${width} ${H}`}
        role="img"
        aria-label={`Water temperature at the Garonne station, observed through ${fmtDay(lastObs, true)} and forecast issued ${fmtDay(origin, true)}: ${summary}.`}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
      >
        {yt.map((t) => (
          <g key={t}>
            <line className="gridline" x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} />
            <text x={m.l - 6} y={y(t) + 4} textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={m.l - 6} y={m.t - 6} textAnchor="end">°C</text>
        {xt.map((d) => (
          <text key={d} x={xd(d)} y={H - 10} textAnchor="middle">{fmtDay(d)}</text>
        ))}

        <rect x={xExplore} y={m.t} width={Math.max(0, width - m.r - xExplore)} height={H - m.t - m.b} fill="var(--surface-2)" opacity={0.7} />
        <text x={width - m.r - 4} y={H - m.b - 6} textAnchor="end" style={{ fontSize: 10 }}>{width < 560 ? "4–7 expl." : "days 4–7 exploratory"}</text>

        <path d={p90Path} fill="none" stroke="var(--p90)" strokeWidth={1.5} strokeDasharray="5 4" />

        <g opacity={opacity}>
          <path d={band(3, 7)} fill="var(--band-explore)" />
          <path d={band(1, 3)} fill="var(--band)" />
          {showBaselines && pers != null && (
            <line x1={xd(lastObs)} x2={xd(end)} y1={y(pers)} y2={y(pers)} stroke="var(--pers)" strokeWidth={1.5} strokeDasharray="2 3" />
          )}
          {showBaselines && (
            <path d={pathOf(fc.map(({ date }, i) => [xd(date), climC[i] == null ? null : y(climC[i]!)]))} fill="none" stroke="var(--clim)" strokeWidth={1.5} />
          )}
          <path d={pathOf(meanPts)} fill="none" stroke="var(--accent)" strokeWidth={2.5} />
          {fc.map(({ h, date, c }) =>
            c ? (
              <circle key={h} cx={xd(date)} cy={y(c[0])} r={h <= 3 ? 4 : 3} fill={c[3] ? "var(--watch)" : "var(--accent)"} stroke="var(--surface)" strokeWidth={1.5}>
                <title>{`Day +${h} (${fmtDay(date)}): ${c[0].toFixed(2)} °C${c[3] ? " — above seasonal 90th percentile" : ""}`}</title>
              </circle>
            ) : null,
          )}
        </g>

        <path d={obsPath} fill="none" stroke="var(--obs)" strokeWidth={1.8} />
        {dates.filter((d) => d <= lastObs).map((d) => {
          const o = v.obs(d);
          return o == null ? null : <circle key={d} cx={xd(d)} cy={y(o)} r={2.2} fill="var(--obs)" />;
        })}
        {showOutcome &&
          outcomeDates.map((d) => {
            const o = v.obs(d);
            return o == null ? null : (
              <circle key={d} cx={xd(d)} cy={y(o)} r={3.5} fill="none" stroke="var(--outcome)" strokeWidth={1.8} />
            );
          })}

        <line x1={X0} x2={X0} y1={m.t} y2={H - m.b} stroke="var(--text)" strokeWidth={1} strokeDasharray="1 3" />
        <text x={X0 - 4} y={m.t + 12} textAnchor="end" style={{ fontSize: 10 }}>{width < 560 ? "issued" : "issued 12:00 UTC"}</text>

        {hoverDate && <line x1={xd(hoverDate)} x2={xd(hoverDate)} y1={m.t} y2={H - m.b} stroke="var(--faint)" />}
      </svg>

      {hoverDate && (
        <Tip
          left={Math.min(xd(hoverDate) + 12, width - 190)}
          top={m.t}
          date={hoverDate}
          obs={hoverDate <= lastObs || showOutcome ? v.obs(hoverDate) : null}
          observedLabel={hoverDate <= lastObs ? "Observed" : "What happened"}
          cell={fc.find((f) => f.date === hoverDate)?.c ?? null}
          lead={daysBetween(origin, hoverDate)}
          p90={v.p90(hoverDate)}
          model={model}
        />
      )}

      <div className="legend" aria-hidden="true">
        <span><i className="sw line" style={{ background: "var(--obs)" }} /> Observed daily mean</span>
        <span><i className="sw line" style={{ background: "var(--accent)" }} /> {MODEL_SHORT[model]} forecast</span>
        <span><i className="sw" style={{ background: "var(--band)" }} /> 90% range</span>
        <span><i className="sw line" style={{ background: "var(--p90)" }} /> Seasonal 90th percentile (watch line)</span>
        {showOutcome && <span><i className="sw" style={{ border: "2px solid var(--outcome)", borderRadius: 6, width: 10 }} /> What actually happened</span>}
        {showBaselines && <span><i className="sw line" style={{ background: "var(--pers)" }} /> Persistence</span>}
        {showBaselines && <span><i className="sw line" style={{ background: "var(--clim)" }} /> Climatology</span>}
      </div>
    </div>
  );
}

function Tip(p: {
  left: number; top: number; date: string; obs: number | null; observedLabel: string;
  cell: [number, number | null, number | null, number] | null; lead: number; p90: number | null; model: ModelId;
}) {
  return (
    <div className="tooltip" style={{ left: p.left, top: p.top }}>
      <b>{fmtDayLong(p.date)}{p.lead > 0 ? ` · day +${p.lead}` : ""}</b>
      {p.obs != null && <div>{p.observedLabel}: <span className="num">{fmtC(p.obs, 2)}</span></div>}
      {p.cell && (
        <>
          <div>{MODEL_SHORT[p.model]}: <span className="num">{fmtC(p.cell[0], 2)}</span></div>
          {p.cell[1] != null && <div className="muted">90% range <span className="num">{p.cell[1].toFixed(1)}–{p.cell[2]!.toFixed(1)} °C</span></div>}
        </>
      )}
      {p.p90 != null && <div className="muted">Watch line: <span className="num">{fmtC(p.p90, 2)}</span></div>}
    </div>
  );
}
