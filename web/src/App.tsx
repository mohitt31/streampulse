import { useEffect, useMemo, useState } from "react";
import type { Replay } from "./types";
import { View, loadReplay } from "./lib/data";
import { ReplayView } from "./components/ReplayView";
import { EvaluationView } from "./components/EvaluationView";
import { MethodView } from "./components/MethodView";
import type { Acks } from "./components/AlertPanel";

type Tab = "replay" | "evaluation" | "method";
const TABS: [Tab, string][] = [["replay", "Replay"], ["evaluation", "Evaluation"], ["method", "Method & data"]];
const ACK_KEY = "streampulse.acks.v1";

function readAcks(): Acks {
  try { return JSON.parse(localStorage.getItem(ACK_KEY) || "{}"); } catch { return {}; }
}

export default function App() {
  const [data, setData] = useState<Replay | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(() => {
    const h = location.hash.slice(1) as Tab;
    return TABS.some(([k]) => k === h) ? h : "replay";
  });
  const [originIdx, setOriginIdx] = useState(0);
  const [acks, setAcks] = useState<Acks>(readAcks);
  const [theme, setTheme] = useState<"auto" | "light" | "dark">("auto");

  useEffect(() => {
    loadReplay()
      .then((d) => {
        setData(d);
        // open on the first day of the July 2025 heatwave alerts if present, else the first alert
        // deep link: ?d=YYYY-MM-DD opens that issue date; default = start of the June 2025 heatwave alerts
        const q = new URLSearchParams(location.search).get("d");
        const qi = q ? d.origins.indexOf(q) : -1;
        const jun = d.alerts.find((a) => a.origin_date >= "2025-06-19");
        const first = jun ?? d.alerts[0];
        setOriginIdx(qi >= 0 ? qi : first ? Math.max(0, d.origins.indexOf(first.origin_date)) : 0);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => { history.replaceState(null, "", `#${tab}`); }, [tab]);
  useEffect(() => {
    const onHash = () => {
      const h = location.hash.slice(1) as Tab;
      if (TABS.some(([k]) => k === h)) setTab(h);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const v = useMemo(() => (data ? new View(data) : null), [data]);

  const onAck = (id: string, a: Acks[string]) => {
    const next = { ...acks, [id]: a };
    setAcks(next);
    try { localStorage.setItem(ACK_KEY, JSON.stringify(next)); } catch { /* storage unavailable: keep in memory */ }
  };

  return (
    <>
      <header className="top">
        <div className="wrap">
          <div className="brand">
            <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
              <rect width="32" height="32" rx="7" fill="var(--accent)" />
              <path d="M4 19c4 0 4-6 8-6s4 8 8 8 4-9 8-9" stroke="var(--accent-ink)" strokeWidth="3" fill="none" strokeLinecap="round" />
            </svg>
            <div>
              <h1>StreamPulse</h1>
              <small>Garonne water-temperature watch · Portet-sur-Garonne</small>
            </div>
          </div>
          <nav className="tabs" role="tablist" aria-label="Sections">
            {TABS.map(([k, label]) => (
              <button key={k} className="tab" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{label}</button>
            ))}
          </nav>
          <button className="theme-btn" aria-label="Toggle colour theme"
            onClick={() => setTheme(theme === "auto" ? "dark" : theme === "dark" ? "light" : "auto")}>
            {theme === "auto" ? "◐" : theme === "dark" ? "☾" : "☀"}
          </button>
        </div>
      </header>
      <section aria-label="Scope notice">
      {data?.synthetic && (
        <div className="ribbon synthetic"><div className="wrap">SYNTHETIC DATA: pipeline smoke test, not results.</div></div>
      )}
      <div className="ribbon">
        <div className="wrap">
          Historical proof of concept on the Garonne at Portet-sur-Garonne, near Toulouse. Forecasts are replayed as they
          would have been issued in 2025; the station feed ends in August 2025.
        </div>
      </div>
      </section>
      <main>
        <div className="wrap">
          {err && <div className="card"><b>Could not load data.</b> <span className="muted">{err}</span></div>}
          {!v && !err && <div className="card muted">Loading replay…</div>}
          {v && tab === "replay" && <ReplayView v={v} originIdx={originIdx} setOriginIdx={setOriginIdx} acks={acks} onAck={onAck} />}
          {v && tab === "evaluation" && <EvaluationView v={v} />}
          {v && tab === "method" && <MethodView v={v} />}
        </div>
      </main>
      <footer>
        <div className="wrap">
          StreamPulse · OneAquaHealth IEEE Global Hackathon 2026 · MIT licence ·{" "}
          <a href="https://github.com/mohitt31/streampulse">github.com/mohitt31/streampulse</a> · data: Hub'eau (Etalab 2.0), Open-Meteo / ECMWF (CC BY 4.0)
          {data && <> · build {data.generated_at}</>}
        </div>
      </footer>
    </>
  );
}
