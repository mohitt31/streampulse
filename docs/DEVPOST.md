# Devpost submission text (paste into the form)

**Project name:** StreamPulse

**Tagline (≤200 chars):** Leakage-safe 1–3 day river-temperature forecasts that turn into OneAquaHealth field alerts ("measure dissolved oxygen") and are recorded as validated FHIR.

**Tracks:** Track 6: Resilience Informatics (primary) · Track 7: Digital Health Standards (secondary)

**Links:**
- Prototype: https://mohitt31.github.io/streampulse/
- Code: https://github.com/mohitt31/streampulse
- Video: *(YouTube link)*

---

## Inspiration

Warm water holds less oxygen. During a heatwave, fish kills and poor water quality in urban rivers can follow within days, and monitoring teams cannot sample everywhere every morning. OneAquaHealth's field protocol already says what to do when a river runs hot: confirm the temperature and measure dissolved oxygen. What is missing is a trustworthy early signal of *when*, a few days ahead, in a format other systems can read.

## What it does

StreamPulse runs every day at 12:00 UTC for a river monitoring site, using only data available at that moment:

- **Forecast:** daily mean water temperature for the next 1–3 days, with a 90% range.
- **Thermal watch:** raised when a forecast reaches that calendar day's 90th percentile (2010–2023).
- **Field task:** each watch becomes an alert with the OAH follow-up, "confirm temperature and measure dissolved oxygen". A technician can acknowledge it.
- **FHIR record:** everything (site, observations, forecasts, alert, acknowledgement and provenance) is exported as FHIR R4 resources following the OneAquaHealth implementation guide.

The prototype is a historical replay on the Garonne at Portet-sur-Garonne, near Toulouse. You pick any day of 2025 and see exactly what StreamPulse would have said at noon that day, then what actually happened. In live mode it refuses to forecast, because the public station feed ended in August 2025. It shows a stale-input warning instead of an invented number.

## How we built it

- **Data:**
  - Hourly water temperature from the French Hub'eau API, 2010–2025.
  - 523 archived ECMWF IFS forecast runs from the Open-Meteo Single Runs API.
  - Every download is logged with URL, time and SHA-256.
- **Quality control:** a day needs ≥18 hourly readings covering all four quarters of the day. Conflicting duplicates are quarantined, and gaps are never filled.
- **Model:**
  - A direct ridge regression per lead time on the last seven days and the season.
  - A physical correction on top: ECMWF's forecast air temperature for the target window, relative to today's water.
  - Intervals come from out-of-sample residuals.
- **Evaluation designed before looking:**
  - Contract file: `config/contract.toml`.
  - Splits: train 2010–2022, tune 2023, validate 2024 (expanding window), test 2025.
  - The 2025 test was opened once. The CLI refuses to re-tune after that.
  - A six-criterion go/no-go gate was fixed in advance, including a gap-aware block bootstrap and a 24-hour data-delay sensitivity test.
- **Dashboard:** React + TypeScript with hand-built SVG charts. It is accessible, mobile-friendly, has a dark mode, and is deployed on GitHub Pages.
- **FHIR:**
  - `LocationOah` and `ObservationIndicatorsOah` for the site and measurements.
  - A derived forecast Observation profile for forecasts.
  - `Communication` for alerts, and `Provenance` plus `Device` for the model.
  - Validated with the official HL7 validator 6.10.4 against the pinned OAH IG: 0 errors and 0 warnings on 10 documents.
  - Three broken negative controls are each rejected for the intended reason.
  - CI rebuilds everything and validates a Bundle exported from the real replay on every push.

## Results (2025, opened once)

- **Day-3 error:** 0.79 °C, against 1.20 °C for persistence and 1.75 °C for climatology. That is **34% skill**; all 6 pre-registered gate criteria passed.
- **Day 1 and day 2:** 28% and 31% skill.
- **Thermal watch at day 3:** 80% precision, 43% recall. At day 1: 86% precision, 72% recall.
- **Honest range:** 2024 validation skill was 13.5%. By month in 2025, skill goes from −21.5% (February) to 60% (May).

## Challenges we ran into

- **Undocumented timestamps.** Hub'eau does not say which timezone its timestamps use. We worked it out from the data: every spring daylight-saving night, 02:00 is missing and 03:00 appears twice, so it is French local time. That also proves no information leaks into a noon forecast.
- **Data gaps.** The station has no data from August 2018 to January 2021, and five ECMWF runs were missing right at the start of the August 2025 heatwave. We report both instead of patching them.
- **Beating persistence.** Saying "tomorrow equals today" is hard to beat for a big river. We made that the bar, not climatology.

## Accomplishments that we're proud of

- A forecast that is scored on the same days as its baselines, with a pre-registered gate it could have failed.
- A failure case (31 May 2025, forecast 18.4 °C vs 15.6 °C observed) shown in the demo on purpose.
- An alert that means a specific field action, not just a red badge.

## What we learned

The hardest part of early warning is not the model. It is proving the warning was issued only from information available at that time, and saying clearly where it fails.

## What's next

- Plug in a live sensor feed. The pipeline already runs daily.
- Add river discharge to catch flow-driven cooling.
- Tune watch thresholds with local ecologists.
- Onboard more OneAquaHealth sites. Each needs only a station code and its own climatology.

## Built with

python · numpy · pandas · react · typescript · vite · svg · hl7-fhir · sushi · hub'eau-api · open-meteo · ecmwf · github-actions · github-pages
