# Devpost submission text

**Project name:** StreamPulse

**Tagline:** Auditable river-temperature reforecasts that turn unusual warmth into a proposed field check, with OneAquaHealth-derived FHIR records.

**Tracks:** Track 6: Resilience Informatics (primary) · Track 7: Digital Health Standards (secondary)

- Prototype: https://mohitt31.github.io/streampulse/
- Code: https://github.com/mohitt31/streampulse
- Video: recording link pending

## Inspiration

A river monitoring team has limited time for field visits. Temperature can help prioritise a follow-up, but it cannot establish low dissolved oxygen, biological damage or health risk. StreamPulse asks when unusual warmth might justify a trained team's temperature and oxygen check. This proposed decision rule draws on the measurements supported by the [OAH Health Assessment Framework](https://www.oneaquahealth.eu/health-assessment-framework-for-urban-aquatic-ecosystems/); it is not a prescribed OAH alert threshold.

## What it does

StreamPulse replays **1–3 day** daily-mean water-temperature forecasts on the Garonne at Portet-sur-Garonne, near Toulouse. It shows nominal **90%** prediction intervals, compares a forecast to a seasonal **90th-percentile** watch line, and lets a reviewer reveal the observed outcome and compare baselines.

This is a large-river proof of concept near an OAH research city. Official OAH sampling-site membership is **UNVERIFIED**. A watch represents unusual warmth, not unsafe water.

The **2025** replay uses simulated **12:00 UTC** issuance and enforces date-based chronology. Historical input publication times remain **UNVERIFIED**. Archived weather runs may include reprocessed hindcasts, so we call this a reforecast evaluation. The static Live view withholds a current forecast because the bundled history ends on **2025-08-21**; it is not a continuously polling service.

Acknowledgements are browser-local demonstrations. The separate exporter can encode supplied acknowledgements as FHIR Communications; browser clicks are not automatically exported or sent to field staff.

## How we built it

The water model is trained on **2010–2022**, tuned on **2023**, and refitted through **2023**. A fitted air-temperature correction is selected through expanding-window **2024** validation. The selected model is frozen before the recorded **2025** test opening. All methods are scored on paired eligible days within each lead. Quality control quarantines conflicting duplicates and does not interpolate gaps.

The source history has **4,527** eligible days and **523** archived ECMWF air-temperature runs. The dashboard uses React and TypeScript on GitHub Pages. It includes missing-weather fallback, stale inputs, baseline comparisons and explicit failure examples.

FHIR export uses OAH Location and indicator Observation profiles, a locally derived forecast profile, Communication, Device and Provenance. The recorded **HL7 validator 6.10.4** fixture suite has **0 errors and 0 warnings** on **10 documents**, with **three** negative controls rejected as intended. CI separately validates a real replay Bundle. [Official sandbox evidence](../reports/fhir-validation/sandbox_roundtrip.json) records transaction and read-back outcomes. Transport success does not mean OAH certification or field deployment.

## Results and their limits

- **Day-3 MAE: 0.79 °C**, versus **1.20 °C** for persistence and **1.75 °C** for climatology: **34% skill** on **224** paired days. The frozen gate passed all **6** criteria.
- **Day-1 and day-2 skill:** **28%** and **31%**, on **226** and **225** paired days respectively.
- **Day-3 watch:** **80% precision, 43% recall**. Persistence gives **59% precision, 54% recall**: the model's higher precision comes with lower recall. Improved MAE does not establish improved field decisions.
- **Validation skill: 13.6%** on the expanding-window **2024** assessment. This and the test result do not bound future performance.
- Nominal **90%** intervals covered **95–98%**. Only **10** observed exceedance episodes underpin the watch rates.

Sources: [test_metrics.json](../reports/test_metrics.json), [gate.json](../reports/gate.json), [frozen_selection.json](../reports/frozen_selection.json), [qc_summary.json](../reports/qc_summary.json), and the [FHIR summary](../reports/fhir-validation/summary.json). Exact keys are in [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md).

## Challenges and lessons

Daylight-saving-shaped anomalies suggest a civil-time convention, but source timezone and publication delay remain **UNVERIFIED**. Date chronology is tested; historical availability at the exact simulated issuance is not proven. Local hashes and timestamps record the frozen selection and test opening; they are not independent preregistration.

Weather gaps expose an operational weakness: a labelled water-only fallback produces no product alert. The complete-case skill result does not measure the consequences of that outage. The demo also shows a missed cooling event; discharge is not an input, and its role in that particular miss is **UNVERIFIED**.

## Citizen science hook — proposed integration, not built

A coordinator could review a watch and route a site-specific check to a trained volunteer through an agreed adapter to the [OAH Citizen Science App](https://www.oneaquahealth.eu/citizen-science-project/). The volunteer would record observations and, where trained, equipped and authorised, confirm temperature and dissolved oxygen. An expert would review the evidence and decide whether biological sampling is warranted.

The adapter would link site, alert, assignment and returned evidence. App APIs, task routing, identity mapping, consent and write-back support are **UNVERIFIED**. No app connection, delivered notification or completed field sampling is claimed.

## What's next

Confirm source availability, establish a supervised fresh-feed pilot, and measure whether alerts improve visit decisions at a fixed sampling budget. Extend to low-cost loggers on small urban streams only after sensor QA, sufficient local history, site-specific calibration and new validation. Environmental or health benefits and cross-site skill remain **UNVERIFIED**.

## Built with

Python · NumPy · pandas · React · TypeScript · Vite · SVG · HL7 FHIR · SUSHI · Hub'eau · Open-Meteo · ECMWF · GitHub Actions · GitHub Pages
