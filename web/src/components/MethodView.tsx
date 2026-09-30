import { View, pct } from "../lib/data";
import { fmtDay } from "../lib/time";

const STEPS = [
  ["Hub'eau hourly sensor", "Station 05174000, 2010 → Aug 2025, source clock unverified"],
  ["Quality control", "≥18 hours, all four 6-h quarters, conflicting duplicates quarantined, no gap filling"],
  ["Daily mean", "Mean of hourly means on the source calendar day"],
  ["Trailing features", "Last value, 3- and 7-day means, 3-day change, season, climatology gap"],
  ["Ridge per lead", "Direct model for each day +1…+7, α chosen on 2023"],
  ["ECMWF air correction", "a + b × (forecast air mean − water), from run D 00 UTC"],
  ["Interval + watch", "Empirical 5/95% residuals; watch if ≥ seasonal 90th percentile"],
  ["Alert → FHIR", "OAH Location, Observations, forecast profile, Communication, Provenance"],
];

export function MethodView({ v }: { v: View }) {
  const years = Object.entries(v.d.qc.per_year);
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card">
        <h2>What StreamPulse does</h2>
        <p style={{ marginTop: 0 }}>
          At a simulated 12:00 UTC issuance, this replay forecasts the daily mean water temperature of the Garonne for the next three days,
          flags days likely to run warmer than 90% of past years at that time of year, and turns each flag into a concrete
          field task: <b>confirm the temperature and measure dissolved oxygen</b>, a proposed follow-up using measurements supported by the OAH framework; not an OAH-prescribed thermal trigger.
          The separate exporter produces FHIR resources using OAH and local profiles. Browser acknowledgements are local demonstrations.
        </p>
        <div className="pipeline">
          {STEPS.map(([t, d], i) => (
            <div className="step" key={t}><b>{i + 1}. {t}</b>{d}</div>
          ))}
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(320px, 100%), 1fr))" }}>
        <div className="card">
          <h2>Leakage-safe timeline</h2>
          <div className="splits" aria-label="Data splits">
            <div style={{ flex: 8.6, background: "#0b6e79" }}>train 2010–18</div>
            <div style={{ flex: 2.4, background: "repeating-linear-gradient(45deg,#9aa7ab,#9aa7ab 4px,#b8c3c6 4px,#b8c3c6 8px)", color: "#233" }}>gap</div>
            <div style={{ flex: 2, background: "#0b6e79" }}>2021–22</div>
            <div style={{ flex: 1, background: "#3b6fb6" }}>2023</div>
            <div style={{ flex: 1, background: "#6b46b0" }}>2024</div>
            <div style={{ flex: 0.65, background: "#c2410c" }}>2025</div>
          </div>
          <div className="legend" style={{ marginTop: 6 }}>
            <span><i className="sw" style={{ background: "#0b6e79" }} /> train</span>
            <span><i className="sw" style={{ background: "#3b6fb6" }} /> tune α (2023)</span>
            <span><i className="sw" style={{ background: "#6b46b0" }} /> validate weather (2024)</span>
            <span><i className="sw" style={{ background: "#c2410c" }} /> test, opened once (2025)</span>
          </div>
          <ul className="notes small" style={{ marginTop: 10 }}>
            <li>A training row counts only if both its issue date and its target date sit inside the split, so no target leaks across a boundary.</li>
            <li>Features use observations up to the day before issuance, never after.</li>
            <li>Climatology and the watch line use 2010–2023 only.</li>
            <li>Weather correction chosen on 2024 with an expanding window: each month is forecast with coefficients fitted only on earlier, already-observed targets.</li>
            <li>2025 opened once: frozen {fmtDay(v.d.frozen_at.slice(0, 10), true)} {v.d.frozen_at.slice(11, 16)} UTC, test opened {v.d.test_opened_at.slice(11, 16)} UTC. The CLI blocks re-tuning by default; local timestamps are not independent preregistration.</li>
          </ul>
        </div>
        <div className="card">
          <h2>Chronology assertions {v.d.chronology.passed ? <span className="pass">all pass</span> : <span className="fail">FAILED</span>}</h2>
          <ul className="notes small">
            {v.d.chronology.checks.map((c) => (
              <li key={c.check}><span className={c.passed ? "pass" : "fail"}>{c.passed ? "✓" : "✗"}</span> {c.check}</li>
            ))}
          </ul>
          <p className="small faint">Sensitivity: with observations delayed by one extra day, day-3 skill is {pct(v.d.delay1[v.d.product_model]?.skill)}.</p>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(320px, 100%), 1fr))" }}>
        <div className="card">
          <h2>Data quality by year</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Year</th><th className="r">Days with data</th><th className="r">Usable days</th><th className="r">Share</th></tr></thead>
              <tbody>
                {years.map(([y, r]) => (
                  <tr key={y} style={r.eligible_days === 0 ? { color: "var(--watch)" } : undefined}>
                    <td>{y}</td>
                    <td className="r num">{r.days_with_data}</td>
                    <td className="r num">{r.eligible_days}</td>
                    <td className="r num">{pct(r.eligible_days / r.calendar_days)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small faint">
            {v.d.qc.eligible_days} usable days of {v.d.qc.days}. {v.d.qc.conflicting_duplicates_quarantined} conflicting readings quarantined.
            Daylight-saving-shaped anomalies suggest a civil-time convention. Producer timezone and historical publication latency remain UNVERIFIED; chronology checks do not establish actual input availability.
          </p>
        </div>
        <div className="card">
          <h2>Data sources</h2>
          <ul className="notes small">
            <li><a href="https://hubeau.eaufrance.fr/page/api-temperature-continu" target="_blank" rel="noreferrer">Hub'eau water temperature API</a> (Etalab Open Licence 2.0): station {v.d.site.id}, {v.d.site.name}, {v.d.site.commune}.</li>
            <li><a href="https://open-meteo.com/en/docs/single-runs-api" target="_blank" rel="noreferrer">Open-Meteo Single Runs API</a> (CC BY 4.0): ECMWF IFS 00 UTC runs, hourly 2 m air temperature, {v.d.qc.air_runs.runs} runs {v.d.qc.air_runs.first_run} → {v.d.qc.air_runs.last_run}.</li>
            <li><a href={`https://www.openstreetmap.org/?mlat=${v.d.site.lat}&mlon=${v.d.site.lon}#map=13/${v.d.site.lat}/${v.d.site.lon}`} target="_blank" rel="noreferrer">Site on OpenStreetMap</a> ({v.d.site.lat.toFixed(4)}, {v.d.site.lon.toFixed(4)}).</li>
            <li>OneAquaHealth FHIR IG (pinned commit), HL7 FHIR R4 4.0.1.</li>
          </ul>
          <h3 style={{ marginTop: 14 }}>FHIR conformance</h3>
          {v.d.fhir ? (
            <>
              <p className="small" style={{ marginTop: 0 }}>
                Official HL7 validator {v.d.fhir.validator}, FHIR {v.d.fhir.fhir}, on the recorded fixture suite against pinned OAH and local profiles:{" "}
                <b className={v.d.fhir.errors === 0 ? "pass" : "fail"}>{v.d.fhir.errors} errors, {v.d.fhir.warnings} warnings</b>
                {v.d.fhir.positive_documents ? ` on ${v.d.fhir.positive_documents} documents` : ""}.
              </p>
              <p className="small" style={{ marginTop: 0 }}>
                Negative controls correctly rejected: {Object.keys(v.d.fhir.negative_controls).map((k) => k.replace(/-/g, " ")).join(", ")}.
              </p>
              <ul className="notes small">
                <li><b>Site</b>: OAH <code>Location</code> (Hub'eau station identifier)</li>
                <li><b>Daily means</b>: OAH <code>ObservationIndicatorsOah</code>, UCUM <code>Cel</code></li>
                <li><b>Forecasts</b>: local profile derived from the OAH indicator, with 90% interval, forecast origin and run mode</li>
                <li><b>Alert</b>: <code>Communication</code> about the site and forecasts; acknowledgement via <code>inResponseTo</code></li>
                <li><b>Lineage</b>: <code>Provenance</code> to input observations and the model <code>Device</code> (git version)</li>
              </ul>
              <p className="small faint">CI rebuilds the OAH IG from its pinned commit and re-validates a Bundle exported from these real forecasts on every push.</p>
            </>
          ) : (
            <p className="small muted">FHIR export and validation report are published in the repository under <code>fhir/</code>.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h2>Reproducibility</h2>
        <div className="table-wrap">
          <table>
            <tbody>
              <tr><th>Model version (git)</th><td className="mono">{v.d.model_version}</td></tr>
              <tr><th>Evaluation contract sha256</th><td className="mono hash">{v.d.hashes.contract}</td></tr>
              <tr><th>Frozen selection sha256</th><td className="mono hash">{v.d.hashes.frozen}</td></tr>
              <tr><th>Daily water data sha256</th><td className="mono hash">{v.d.hashes.daily_water}</td></tr>
              <tr><th>Rebuild</th><td className="mono">See README: preserve the frozen checkout; reconstruct in an isolated workspace.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
