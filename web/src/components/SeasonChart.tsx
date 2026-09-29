import { View } from "../lib/data";
import { addDays, daysBetween, fmtDay } from "../lib/time";
import { linear, niceTicks, pathOf, useWidth } from "../lib/useWidth";

export function SeasonChart({ v, originIdx, onPick }: { v: View; originIdx: number; onPick: (i: number) => void }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const origins = v.d.origins;
  const start = addDays(origins[0], -7);
  const end = addDays(origins[origins.length - 1], 3);
  const n = daysBetween(start, end);
  const dates = Array.from({ length: n + 1 }, (_, i) => addDays(start, i));
  const H = 156;
  const m = { l: 34, r: 10, t: 10, b: 40 };
  const vals = dates.flatMap((d) => [v.obs(d), v.p90(d)]).filter((x): x is number => x != null);
  const lo = Math.floor(Math.min(...vals) - 1);
  const hi = Math.ceil(Math.max(...vals) + 1);
  const x = linear(0, n, m.l, width - m.r);
  const xd = (d: string) => x(daysBetween(start, d));
  const y = linear(lo, hi, H - m.b, m.t);
  const alerts = new Set(v.d.alerts.map((a) => a.origin_date));
  const sel = origins[originIdx];
  const months = dates.filter((d) => d.endsWith("-01"));

  const pick = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * width;
    const d = addDays(start, Math.round(((px - m.l) / (width - m.l - m.r)) * n));
    const i = origins.indexOf(d);
    if (i >= 0) onPick(i);
    else onPick(d < origins[0] ? 0 : origins.length - 1);
  };

  return (
    <div className="chart" ref={ref}>
      <svg viewBox={`0 0 ${width} ${H}`} onClick={pick} style={{ cursor: "pointer" }} role="img"
        aria-label="2025 season overview: observed water temperature against the seasonal watch line, with alert days marked. Click to jump to a date.">
        {niceTicks(lo, hi, 3).map((t) => (
          <g key={t}>
            <line className="gridline" x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} />
            <text x={m.l - 5} y={y(t) + 4} textAnchor="end">{t}</text>
          </g>
        ))}
        {months.map((d) => (
          <text key={d} x={xd(d)} y={H - 6} textAnchor="start">{fmtDay(d).split(" ")[1]}</text>
        ))}
        <path d={pathOf(dates.map((d) => [xd(d), v.p90(d) == null ? null : y(v.p90(d)!)]))} fill="none" stroke="var(--p90)" strokeDasharray="4 3" strokeWidth={1.2} />
        <path d={pathOf(dates.map((d) => [xd(d), v.obs(d) == null ? null : y(v.obs(d)!)]))} fill="none" stroke="var(--obs)" strokeWidth={1.4} />
        {origins.map((o) =>
          alerts.has(o) ? <rect key={o} x={xd(o) - 1.5} y={H - m.b + 3} width={3} height={9} fill="var(--watch)" rx={1} /> : null,
        )}
        <line x1={xd(sel)} x2={xd(sel)} y1={m.t} y2={H - m.b + 12} stroke="var(--accent)" strokeWidth={2} />
      </svg>
      <div className="legend">
        <span><i className="sw line" style={{ background: "var(--obs)" }} /> Observed 2025</span>
        <span><i className="sw line" style={{ background: "var(--p90)" }} /> Watch line</span>
        <span><i className="sw" style={{ background: "var(--watch)", width: 4 }} /> Alert issued</span>
        <span><i className="sw line" style={{ background: "var(--accent)" }} /> Selected issue date</span>
      </div>
    </div>
  );
}
