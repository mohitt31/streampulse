# StreamPulse video script (4:30)

Record at 1280×800 or larger. Browser zoom 110%. Use the deployed Pages site. Deep links: `?d=YYYY-MM-DD#replay`.

Every number spoken below comes from `reports/gate.json`, `reports/test_metrics.json` or `reports/frozen_selection.json`. If a number changes, change the script.

Target: about 130 words per minute. Each block lists its word budget.

---

## 0:00–0:25 · Problem and user (Impact, 30%) · ~50 words

**Screen:** title card, then the Replay tab on `?d=2025-06-20`.

> Warm rivers hold less oxygen. In a heatwave, a monitoring team has to decide where to send people each morning. StreamPulse answers one question for them: will this river run unusually warm in the next three days, and should someone go out and measure oxygen?

## 0:25–0:55 · Scope and trust (Feasibility) · ~65 words

**Screen:** point at the yellow ribbon and the "REPLAY · simulated issuance" chip. Switch to **Live (today)** to show the stale banner, then back to replay.

> This is a historical proof of concept on the Garonne near Toulouse, using the public Hub'eau sensor. The feed stopped in August 2025. So in live mode StreamPulse refuses to forecast and says why. It does not invent a number. Everything you'll see is replayed exactly as it would have been issued on that day.

## 0:55–1:45 · Main interaction (UX + Innovation) · ~105 words

**Screen:** `?d=2025-06-20`. Hover the chart. Point at the three lead cards, the 90% range and the dashed watch line. Tick "What actually happened". Press ▶ for about 3 seconds.

> Twentieth of June 2025, noon. The model has water observations up to yesterday and this morning's ECMWF air-temperature forecast. It predicts 22.5, 22.7 and 22.6 degrees for the next three days. All three are above the watch line, the ninetieth percentile for this time of year. The shaded band is the 90% range. Now reveal what happened: 22.8, 23.3, 23.7. The watch was right on all three days. The innovation is small but physical: correct a water-history model with the air temperature the river is about to feel.

## 1:45–2:25 · Evaluation (Technical implementation) · ~85 words

**Screen:** Evaluation tab: the KPI row, the MAE-by-lead chart, the gate table. Then Replay at `?d=2025-05-31` for the failure case.

> Is it better than just saying tomorrow equals today? We fixed every rule before looking at 2025, then opened it once. At day three the error is 0.79 degrees against 1.20 for persistence: 34% better, all six pre-registered checks passed. On 2024 validation it was 13.5%, and in February it lost to persistence, so we report that range honestly. And here is a miss: on 31 May it forecast 18.4. The river dropped to 15.6. Flow isn't an input yet.

## 2:25–3:10 · Decision workflow (UX + Impact) · ~90 words

**Screen:** back to `?d=2025-06-20`. In the Thermal watch panel, read the follow-up, type "Field technician – Portet", add a note, click **Acknowledge alert**. Point at the issuance line (inputs through 19 Jun, ECMWF run 20 Jun 00 UTC) and at the alert list.

> A watch isn't just a red badge. It carries the OneAquaHealth field protocol step: confirm the temperature and measure dissolved oxygen. Whether to add biological sampling stays an expert decision. The technician acknowledges it, and the acknowledgement is linked to the alert. Every forecast shows exactly which days of data it used and which weather run. That makes it auditable.

## 3:10–3:50 · Interoperability (Track 7) · ~80 words

**Screen:** repository `fhir/`. Show the example Bundle (Location, Observation, forecast Observation, Communication, Provenance, Device). Terminal: validator output with 0 errors. One negative control failing as expected.

> Everything is exported as FHIR R4 using the OneAquaHealth implementation guide. The site is an OAH Location, and measurements are OAH indicator observations in UCUM degrees Celsius. Forecasts use a profile derived from them, carrying the interval and the forecast origin. The alert is a Communication, with provenance to the exact model version. The official HL7 validator reports zero errors. Broken examples are rejected, as they should be.

*(Fill in the exact validator line and the name of the negative control once the FHIR workstream is merged.)*

## 3:50–4:30 · Next steps (Feasibility + Scalability) · ~80 words

**Screen:** Method & data tab: the pipeline, the leakage-safe timeline, the data-quality table and the DST finding. End on the repository README.

> Going live needs one thing: a fresh sensor feed. The pipeline already runs daily. A new station needs a code, coordinates and its own climatology. Next come river flow as an input, and watch lines tuned with local ecologists. It's all open source under MIT, and every download and result is hashed. StreamPulse: forecasts you can check, alerts you can act on.

---

## Shot checklist

- [ ] Pages site deployed; `?d=` links work
- [ ] Light theme for recording (◐ button → ☀)
- [ ] Clear the demo acknowledgement before recording (DevTools → Application → Local Storage → `streampulse.acks.v1`)
- [ ] FHIR validator output ready in a terminal
- [ ] Final numbers checked against `reports/gate.json`
