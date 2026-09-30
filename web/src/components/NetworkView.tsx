import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Network, NetworkStation, NetCell } from "../types";
import { View, loadNetwork, fmtC, pct } from "../lib/data";
import { addDays, fmtDay, fmtDayLong } from "../lib/time";

interface Props {
  v: View;
  originIdx: number;
  setOriginIdx: (i: number) => void;
  openPrimary: () => void;
}

type ColorBy = "watch" | "skill";

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";

function skillColor(s: number | null | undefined): string {
  if (s == null) return css("--faint");
  if (s < 0) return css("--watch");
  if (s < 0.1) return "#8fa3a8";
  if (s < 0.25) return "#3f8f99";
  return css("--accent");
}

function watchState(cells: NetCell[] | null | undefined): "watch" | "normal" | "none" {
  if (!cells || !cells.some(Boolean)) return "none";
  return cells.some((c) => c && c[2]) ? "watch" : "normal";
}

export function NetworkView({ v, originIdx, setOriginIdx, openPrimary }: Props) {
  const [net, setNet] = useState<Network | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [colorBy, setColorBy] = useState<ColorBy>("watch");
  const [sel, setSel] = useState<string | null>(null);
  const mapEl = useRef<HTMLDivElement | null>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);

  useEffect(() => { loadNetwork().then(setNet).catch((e) => setErr(String(e))); }, []);

  const origin = v.d.origins[originIdx];
  const oi = net ? net.origins.indexOf(origin) : -1;
  const ok = useMemo(() => (net ? net.stations.filter((s) => s.status === "ok") : []), [net]);

  // map init
  useEffect(() => {
    if (!net || !mapEl.current || map.current) return;
    const m = L.map(mapEl.current, { scrollWheelZoom: false, attributionControl: true });
    const dark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    L.tileLayer(`https://{s}.basemaps.cartocdn.com/${dark ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`, {
      maxZoom: 13, subdomains: "abcd",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(m);
    const pts = net.stations.map((s) => [s.lat, s.lon] as [number, number]);
    if (pts.length) m.fitBounds(L.latLngBounds(pts).pad(0.15));
    layer.current = L.layerGroup().addTo(m);
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, [net]);

  // markers
  useEffect(() => {
    if (!net || !layer.current) return;
    layer.current.clearLayers();
    for (const s of net.stations) {
      const cells = oi >= 0 ? net.replay[s.code_station]?.[oi] : null;
      const state = watchState(cells);
      const skill = s.leads?.["3"]?.skill;
      const fill = s.status !== "ok" ? css("--faint")
        : colorBy === "watch" ? (state === "watch" ? css("--watch") : state === "normal" ? css("--accent") : css("--faint"))
        : skillColor(skill);
      const mk = L.circleMarker([s.lat, s.lon], {
        radius: s.primary ? 10 : 8, color: s.code_station === sel ? css("--text") : "#ffffff",
        weight: s.code_station === sel ? 3 : 1.5, fillColor: fill, fillOpacity: s.status === "ok" ? 0.95 : 0.4,
      });
      const label = `${s.name ?? s.code_station}${s.status !== "ok" ? " (not analysed)" : colorBy === "watch"
        ? state === "watch" ? " · WATCH" : state === "normal" ? " · normal" : " · no forecast" : ` · day-3 skill ${pct(skill)}`}`;
      mk.bindTooltip(label);
      mk.on("click", () => setSel(s.code_station));
      mk.addTo(layer.current);
    }
  }, [net, oi, colorBy, sel]);

  if (err) return <div className="card"><b>Network data unavailable.</b> <span className="muted">{err}</span></div>;
  if (!net) return <div className="card muted">Loading network…</div>;

  const h = net.headline;
  const nWatch = ok.filter((s) => watchState(oi >= 0 ? net.replay[s.code_station]?.[oi] : null) === "watch").length;
  const selSt = net.stations.find((s) => s.code_station === sel) ?? null;
  const sorted = [...ok].sort((a, b) => (b.leads?.["3"]?.skill ?? -9) - (a.leads?.["3"]?.skill ?? -9));
  const other = net.stations.filter((s) => s.status !== "ok");

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="kpis">
        <div className="card kpi">
          <div className="sub">Rivers analysed (pre-registered rule)</div>
          <div className="big num">{h.analysed}</div>
          <div className="sub">{h.candidates} candidate stations within {net.rule ? "100 km" : ""} of Toulouse; {h.eligible} met the data rule</div>
        </div>
        <div className="card kpi">
          <div className="sub">Beat persistence at day 3</div>
          <div className="big num">{h.beats_persistence_day3}/{h.analysed}</div>
          <div className="sub">median skill {pct(h.median_skill_day3)}{h.skill_day3_range ? ` · range ${pct(h.skill_day3_range[0])} to ${pct(h.skill_day3_range[1])}` : ""}</div>
        </div>
        <div className="card kpi">
          <div className="sub">Passed the full 6-criterion gate</div>
          <div className="big num">{h.gate_passed}/{h.analysed}</div>
          <div className="sub">same frozen method and thresholds as the primary site</div>
        </div>
        <div className="card kpi">
          <div className="sub">On watch · {fmtDay(origin, true)}</div>
          <div className="big num">{nWatch}</div>
          <div className="sub">rivers forecast above their seasonal 90th percentile (day +1…+3)</div>
        </div>
      </div>

      <div className="grid cols-main">
        <div className="card">
          <div className="row" style={{ marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>Regional early-warning map</h2>
            <span className="spacer" />
            <div className="seg" role="group" aria-label="Colour stations by">
              <button aria-pressed={colorBy === "watch"} onClick={() => setColorBy("watch")}>Watch on this date</button>
              <button aria-pressed={colorBy === "skill"} onClick={() => setColorBy("skill")}>Day-3 skill</button>
            </div>
          </div>
          <div className="row" style={{ marginBottom: 8 }}>
            <button className="btn iconbtn" aria-label="Previous day" onClick={() => setOriginIdx(Math.max(0, originIdx - 1))}>‹</button>
            <input type="range" min={0} max={v.d.origins.length - 1} value={originIdx} style={{ flex: 1, width: "auto" }}
              onChange={(e) => setOriginIdx(+e.target.value)} aria-label="Forecast issue date" aria-valuetext={fmtDayLong(origin)} />
            <button className="btn iconbtn" aria-label="Next day" onClick={() => setOriginIdx(Math.min(v.d.origins.length - 1, originIdx + 1))}>›</button>
            <span className="num small" style={{ minWidth: 118 }}>{fmtDayLong(origin)}</span>
          </div>
          <div ref={mapEl} className="netmap" role="img" aria-label={`Map of ${net.stations.length} river stations around Toulouse; ${nWatch} on watch for ${fmtDay(origin, true)}. The same information is in the table below.`} />
          <div className="legend">
            {colorBy === "watch" ? (
              <>
                <span><i className="sw" style={{ background: "var(--watch)", borderRadius: 6 }} /> Watch (day +1…+3 above watch line)</span>
                <span><i className="sw" style={{ background: "var(--accent)", borderRadius: 6 }} /> Normal</span>
                <span><i className="sw" style={{ background: "var(--faint)", borderRadius: 6 }} /> No forecast (data gap / missing run) or not analysed</span>
              </>
            ) : (
              <>
                <span><i className="sw" style={{ background: "var(--accent)", borderRadius: 6 }} /> ≥ 25%</span>
                <span><i className="sw" style={{ background: "#3f8f99", borderRadius: 6 }} /> 10–25%</span>
                <span><i className="sw" style={{ background: "#8fa3a8", borderRadius: 6 }} /> 0–10%</span>
                <span><i className="sw" style={{ background: "var(--watch)", borderRadius: 6 }} /> worse than persistence</span>
              </>
            )}
            <span>larger dot = primary site</span>
          </div>
        </div>

        <StationCard s={selSt} net={net} oi={oi} origin={origin} openPrimary={openPrimary} />
      </div>

      <div className="card">
        <h2>Every analysed river, 2025 test (day 3)</h2>
        <p className="small muted" style={{ marginTop: 0 }}>
          Each station was fitted and frozen on 2010–2024 with the primary site's exact method (<code>config/contract.toml</code>),
          then its 2025 test was opened once. Station selection was fixed in <code>config/network.toml</code> before any of this data was downloaded.
        </p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Station</th><th>River · commune</th><th className="r">Days</th><th className="r">StreamPulse</th><th className="r">Persistence</th><th className="r">Skill</th><th className="r">Gate</th><th className="r">Watch prec./recall</th></tr></thead>
            <tbody>
              {sorted.map((s) => {
                const l = s.leads?.["3"];
                const prod = s.product_model ?? "weather_corr_v1";
                return (
                  <tr key={s.code_station} aria-selected={s.code_station === sel} onClick={() => setSel(s.code_station)} style={{ cursor: "pointer", background: s.code_station === sel ? "var(--accent-soft)" : undefined }}>
                    <td className="mono">{s.code_station}{s.primary ? " ★" : ""}</td>
                    <td>{s.name}<div className="small muted">{[s.river, s.commune].filter(Boolean).join(" · ")}</div></td>
                    <td className="r num">{l?.n ?? "–"}</td>
                    <td className="r num">{l?.mae?.[prod]?.toFixed(2) ?? "–"}</td>
                    <td className="r num">{l?.mae?.persistence?.toFixed(2) ?? "–"}</td>
                    <td className={`r num ${l?.skill != null && l.skill < 0 ? "fail" : ""}`}><b>{pct(l?.skill)}</b></td>
                    <td className={`r ${s.gate_passed ? "pass" : "fail"}`}>{s.gate_passed ? "✓ GO" : `✗ ${(s.gate ?? []).filter((g) => g.passed).length}/6`}</td>
                    <td className="r num">{l?.watch ? `${pct(l.watch.precision)} / ${pct(l.watch.recall)}` : "–"}</td>
                  </tr>
                );
              })}
              {other.map((s) => (
                <tr key={s.code_station} className="muted">
                  <td className="mono">{s.code_station}</td>
                  <td>{s.name}</td>
                  <td colSpan={6} className="small">{s.status === "failed" ? `run failed: ${s.error ?? ""}` : "not run"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small faint">★ primary site. Skill = 1 − MAE / MAE(persistence), same paired days per station. Gate = the six pre-registered criteria; "✗ k/6" shows how many passed.</p>
        <details>
          <summary className="small">{net.excluded.length} candidate stations excluded by the pre-registered data rule</summary>
          <ul className="notes small" style={{ marginTop: 8 }}>
            {net.excluded.map((x) => <li key={x.code_station}><span className="mono">{x.code_station}</span>: {x.reason}</li>)}
          </ul>
        </details>
      </div>
    </div>
  );
}

function StationCard({ s, net, oi, origin, openPrimary }: { s: NetworkStation | null; net: Network; oi: number; origin: string; openPrimary: () => void }) {
  if (!s) {
    return (
      <div className="card">
        <h2>Pick a river</h2>
        <p className="small muted" style={{ marginTop: 0 }}>Click a dot on the map or a row in the table to see that station's forecast for the selected day and its 2025 test record.</p>
        <p className="small muted">Moving the date slider replays the whole region: the map shows which rivers StreamPulse would have flagged that day.</p>
      </div>
    );
  }
  const cells = oi >= 0 ? net.replay[s.code_station]?.[oi] ?? null : null;
  const l = s.leads?.["3"];
  return (
    <div className="card">
      <h2 style={{ marginBottom: 2 }}>{s.name}</h2>
      <div className="small muted">{[s.river, s.commune, `station ${s.code_station}`].filter(Boolean).join(" · ")}</div>
      {s.status !== "ok" ? (
        <p className="small">Not analysed: {s.error ?? s.status}</p>
      ) : (
        <>
          <h3 style={{ marginTop: 12 }}>Issued {fmtDay(origin, true)}</h3>
          {cells && cells.some(Boolean) ? (
            <div className="grid" style={{ gap: 6 }}>
              {cells.map((c, i) => (
                <div key={i} className="row small num" style={{ gap: 8 }}>
                  <span style={{ minWidth: 88 }}>Day +{i + 1} · {fmtDay(addDays(origin, i + 1))}</span>
                  {c ? (
                    <>
                      <b>{fmtC(c[0])}</b>
                      <span className="muted">line {fmtC(c[1])}</span>
                      <span className={`chip ${c[2] ? "watch" : "ok"}`}>{c[2] ? "▲ watch" : "● normal"}</span>
                      {c[3] != null && <span className="outcome">actual {c[3].toFixed(1)}</span>}
                    </>
                  ) : <span className="muted">no forecast</span>}
                </div>
              ))}
            </div>
          ) : (
            <p className="small muted">No forecast for this date (observation gap or missing ECMWF run).</p>
          )}
          <h3 style={{ marginTop: 14 }}>2025 test, day 3</h3>
          <div className="small num">
            MAE {l?.mae?.[s.product_model ?? "weather_corr_v1"]?.toFixed(2)} °C vs persistence {l?.mae?.persistence?.toFixed(2)} °C
            → skill <b>{pct(l?.skill)}</b> ({l?.n} days)
          </div>
          <div className="small">Gate: <b className={s.gate_passed ? "pass" : "fail"}>{s.gate_passed ? "GO (6/6)" : `${(s.gate ?? []).filter((g) => g.passed).length}/6 criteria`}</b>
            {" "}· weather correction selected on 2024: <code>{s.weather_selected}</code></div>
          {s.primary && <button className="btn primary" style={{ marginTop: 12 }} onClick={openPrimary}>Open full replay for this site</button>}
        </>
      )}
    </div>
  );
}
