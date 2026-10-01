# Devpost submission text

**Project name:** StreamPulse

**Tagline:** Auditable river-temperature reforecasts that turn unusual warmth into a proposed field check, with OneAquaHealth-derived FHIR records.

**Tracks:** Track 6: Resilience Informatics (primary) · Track 7: Digital Health Standards (secondary)

- Prototype: https://mohitt31.github.io/streampulse/
- Code: https://github.com/mohitt31/streampulse
- Video: https://youtu.be/mbE1ybx11cg

## For judges: evidence by criterion

| Criterion | Where to look |
|---|---|
| **Impact & Alignment** | Toulouse is an OAH research city. Each watch becomes one field task (confirm temperature, measure dissolved oxygen) with the oxygen ceiling at the forecast temperature. Against the Garonne's published **24 °C** salmon limit, the day-3 forecast reached 24 °C on 13 of 24 such days with **0** false calls (persistence: 16, with 7 false calls). |
| **Innovation & Creativity** | Pre-registered, 2-stage regional replication (station rules committed to GitHub before any data download). Warm-day skill holds (39% at day 3 above 18 °C); for context, a published deep-learning study reported persistence had better RMSE and bias on warm days. Different rivers, not a head-to-head. A field-visit planner turns forecasts into "which river gets today's team". |
| **Architecture** | Frozen six-criterion gate, gap-aware block bootstrap, chronology assertions, 61 Python and 5 Node tests, and four CI workflows (tests, official HL7 FHIR validation, browser and axe accessibility, Pages). |
| **UX** | Replay with the outcome hidden until revealed, missing-weather and stale-feed states, regional map with date slider, planner, field-check form that downloads a FHIR Bundle, and axe WCAG 2 AA checks in CI. |
| **Scale** | 274 candidate stations were screened under a pre-registered rule; the same frozen method ran on the 4 that qualified, with one config change per site. FHIR R4 with OAH profiles for the site and measurements (forecasts use a local derived profile), with an official sandbox round-trip. Honest blocker: the public temperature archive lags by more than a year, so a pilot needs a producer feed. |

## Inspiration

A river monitoring team has limited time for field visits. Temperature can help prioritise a follow-up, but it cannot establish low dissolved oxygen, biological damage or health risk. StreamPulse asks when unusual warmth might justify a trained team's temperature and oxygen check. This proposed decision rule draws on the measurements supported by the [OAH Health Assessment Framework](https://www.oneaquahealth.eu/health-assessment-framework-for-urban-aquatic-ecosystems/); it is not a prescribed OAH alert threshold.

## What it does

StreamPulse replays **1–3 day** daily-mean water-temperature forecasts on the Garonne at Portet-sur-Garonne, near Toulouse. It shows nominal **90%** prediction intervals, compares a forecast to a seasonal **90th-percentile** watch line, and lets a reviewer reveal the observed outcome and compare baselines.

This is a large-river proof of concept near an OAH research city. Official OAH sampling-site membership is **UNVERIFIED**. A watch represents unusual warmth, not unsafe water.

The **2025** replay uses simulated **12:00 UTC** issuance and enforces date-based chronology. Historical input publication times remain **UNVERIFIED**. Archived weather runs may include reprocessed hindcasts, so we call this a reforecast evaluation. The static Live view withholds a current forecast because the bundled history ends on **2025-08-21**; it is not a continuously polling service.

The **Network** tab replays a regional watch map across four rivers and includes a field-visit planner that ranks rivers for a fixed daily number of visits. Acknowledgements are browser-local demonstrations. After acknowledgement, a field-check form accepts demonstration temperature, dissolved oxygen, optional saturation and a UTC measurement time. It downloads a FHIR collection Bundle linking the alert, acknowledgement, original forecasts, measurement Observations and provenance. Nothing is sent to field staff or a server; unsaved measurements leave memory when the view closes. A spot measurement versus daily-mean prediction is descriptive, not a new forecast-skill result. The browser-generated examples and missing-unit negative control are checked by the official HL7 validator in CI.

## How we built it

The water model is trained on **2010–2022**, tuned on **2023**, and refitted through **2023**. A fitted air-temperature correction is selected through expanding-window **2024** validation. The selected model is frozen before the recorded **2025** test opening. All methods are scored on paired eligible days within each lead. Quality control quarantines conflicting duplicates and does not interpolate gaps.

The source history has **4,527** eligible days and **523** archived ECMWF air-temperature runs. The dashboard uses React and TypeScript on GitHub Pages. It includes missing-weather fallback, stale inputs, baseline comparisons and explicit failure examples.

FHIR export uses OAH Location and indicator Observation profiles, a locally derived forecast profile, Communication, Device and Provenance. The recorded **HL7 validator 6.10.4** fixture suite has **0 errors and 0 warnings** on **10 documents**, with **three** negative controls rejected as intended. CI separately validates a real replay Bundle. [Official sandbox evidence](../reports/fhir-validation/sandbox_roundtrip.json) records transaction and read-back outcomes. Transport success does not mean OAH certification or field deployment.

## Results and their limits

**Primary site (Garonne at Portet-sur-Garonne):**
- **Day-3 MAE: 0.79 °C**, versus **1.20 °C** for persistence and **1.75 °C** for climatology: **34% skill** on **224** paired days. The frozen gate passed all **6** criteria.
- **Day-1 and day-2 skill:** **28%** and **31%**, on **226** and **225** paired days respectively.
- **Day-3 watch:** **80% precision, 43% recall**. Persistence gives **59% precision, 54% recall**: the model's higher precision comes with lower recall. Improved MAE does not establish improved field decisions.
- **Validation skill: 13.6%** on the expanding-window **2024** assessment. This and the test result do not bound future performance.
- Nominal **90%** intervals covered **95–98%**. Only **10** observed exceedance episodes underpin the watch rates.

**Network replication (pre-registered, 2-stage):**

The same frozen method — no re-design, no re-tuning — was applied to every Hub'eau river station within 300 km of Toulouse that met the pre-registered data-quality rule. Station selection was committed to the repository ([`config/network.toml`](../config/network.toml) for stage 1, [`config/network_stage2.toml`](../config/network_stage2.toml) for stage 2) **before any network data was downloaded**, with the commit timestamps on GitHub as evidence. Of **274** candidate stations (62 within 100 km, 212 within 100–300 km), **4** met the rule, including the primary site. At day 3, **all 4** beat persistence on the 2025 test: median skill **38%**, range **19–65%**. **3 of 4** passed the full six-criterion frozen gate; the fourth (Jaur à Olargues, 06185900) beats persistence overall but is reported as **NO-GO**: it failed gate criterion 5 (beat climatology overall and persistence in May–August). Four stations is a small network: this shows the frozen method transfers within this region, not that it transfers everywhere. The **Network** tab shows per-station results and a regional watch map replayed across every 2025 date. Source: [network_summary.json](../reports/network_summary.json).

**Field-visit planner (exploratory, post-hoc, not pre-registered):** with a fixed number of visits per day across the four rivers, ranking rivers by forecast margin above each river's watch line visits about as many real exceedances as ranking by persistence, with fewer wasted trips. At day 3 with two visits a day: **34** exceedance visits from **59** trips (**25** wasted) versus **35** from **81** (**46** wasted). At day 1 with one visit a day: **35** from **51** (**16** wasted) versus **33** from **55** (**22** wasted). Computed afterwards from the frozen 2025 forecasts, with no fitting or tuning; days are correlated and four rivers is small, so this is descriptive. Source: [visit_budget.json](../reports/exploratory/visit_budget.json).

**Warm days and an outside threshold (exploratory, post-hoc):** on days above **18 °C**, day-3 MAE is **0.78 °C** versus **1.27 °C** for persistence (**39%** skill, 68 days; RMSE **0.90** versus **1.70 °C**). A multi-site deep-learning study reported that persistence had better RMSE and bias than its models above 18 °C ([Zwart et al. 2023](https://doi.org/10.3389/frwa.2023.1184992)); different rivers and methods, so this is context, not a head-to-head. For the Garonne, [Larnier et al. 2010](https://doi.org/10.1051/kmae/2010031) give **24 °C** as the upper limit for Atlantic salmon migration. On the 24 target days that reached it, the day-3 forecast also reached 24 °C on **13** with **0** false calls on cooler days; persistence reached it on **16** with **7** false calls. Strata split on the observed value; not a biological validation. Source: [context.json](../reports/exploratory/context.json).

Sources: [test_metrics.json](../reports/test_metrics.json), [gate.json](../reports/gate.json), [frozen_selection.json](../reports/frozen_selection.json), [qc_summary.json](../reports/qc_summary.json), and the [FHIR summary](../reports/fhir-validation/summary.json). Exact keys are in [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md).

## Challenges and lessons

**Feed latency is the operational blocker.** When checked on 2026-09-30, the public Hub'eau temperature API still ended on **2025-08-21** for the primary station, and the network stations also stop in August 2025. A live early-warning service therefore needs a direct producer feed, not only the public archive.

Daylight-saving-shaped anomalies suggest a civil-time convention, but source timezone and publication delay remain **UNVERIFIED**. Date chronology is tested; historical availability at the exact simulated issuance is not proven. Local hashes and timestamps record the frozen selection and test opening; they are not independent preregistration.

Weather gaps expose an operational weakness: a labelled water-only fallback produces no product alert. The complete-case skill result does not measure the consequences of that outage. The demo also shows a missed cooling event; discharge is not an input, and its role in that particular miss is **UNVERIFIED**.

## Citizen science hook — proposed integration, not built

A coordinator could review a watch and route a site-specific check to a trained volunteer through an agreed adapter to the [OAH Citizen Science App](https://www.oneaquahealth.eu/citizen-science-project/). The volunteer would record observations and, where trained, equipped and authorised, confirm temperature and dissolved oxygen. An expert would review the evidence and decide whether biological sampling is warranted.

The adapter would link site, alert, assignment and returned evidence. App APIs, task routing, identity mapping, consent and write-back support are **UNVERIFIED**. No app connection, delivered notification or completed field sampling is claimed.

## What's next

Secure a direct fresh feed from the producer (the public archive lags by more than a year), establish a supervised fresh-feed pilot, and measure whether alerts improve visit decisions at a fixed sampling budget. Extend to low-cost loggers on small urban streams only after sensor QA, sufficient local history, site-specific calibration and new validation. Environmental or health benefits and cross-site skill remain **UNVERIFIED**.

## Built with

References: Zwart et al. 2023, *Frontiers in Water* 5:1184992 · Larnier et al. 2010, *Knowl. Managt. Aquatic Ecosyst.* 398:04 · Benson & Krause 1984, *Limnol. Oceanogr.* 29:620 (oxygen solubility).

Python · NumPy · pandas · React · TypeScript · Vite · SVG · Leaflet · HL7 FHIR · SUSHI · Hub'eau · Open-Meteo · ECMWF · GitHub Actions · GitHub Pages
