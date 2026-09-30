# StreamPulse

**River-temperature reforecasts that turn an unusual-warmth watch into a proposed field check, with auditable OneAquaHealth-derived FHIR records.**

Historical proof of concept on the Garonne at Portet-sur-Garonne, near Toulouse (Hub'eau station `05174000`). This is a large-river pilot near an OAH research city; membership of this station in the official OAH sampling network is **UNVERIFIED**.

**[Live replay dashboard](https://mohitt31.github.io/streampulse/)** · [Video recording script](docs/VIDEO_SCRIPT.md) (recording link pending) · **Track 6: Resilience Informatics** · **Track 7: Digital Health Standards**

![Historical replay with an unusual-warmth watch](docs/img/replay.png)

## Why

Monitoring teams cannot sample every site every day. StreamPulse asks: **will this river run unusually warm, and should a trained monitoring team confirm temperature and measure dissolved oxygen?** Temperature motivates a follow-up measurement; it does not establish low oxygen, biological harm, pathogen presence or human health risk.

The [OAH Health Assessment Framework](https://www.oneaquahealth.eu/health-assessment-framework-for-urban-aquatic-ecosystems/) provides harmonised indicators and sampling guidance. StreamPulse's watch-to-visit rule is a project proposal, not an OAH-prescribed thermal trigger. The intended benefit is better timing of field checks. Saved effort, earlier detection and ecological outcomes are **UNVERIFIED**.

## What is built

- A historical **1–3 day** daily-mean water-temperature reforecast, with nominal **90%** prediction intervals.
- A watch when the forecast reaches the seasonal **90th percentile**, using **2010–2023** and a **±15-day** window. This measures unusual warmth relative to the site's history, not a biological safety limit.
- A replay dashboard with baseline comparisons, observed outcomes, missing-weather fallback and a stale-input state.
- Browser-local demonstration acknowledgements. They are not dispatched to a technician or synchronised with a server. The separate Python FHIR exporter represents supplied acknowledgements as linked Communications.
- A real replay Bundle validated in CI, plus an official OAH sandbox round-trip described below.

The replay uses a simulated **12:00 UTC** issuance. It enforces observation-date and model-fitting chronology. Historical source publication times and exact source timezone remain **UNVERIFIED**; the archive does not prove that every input was obtainable at that simulated instant. The weather archive may include reprocessed hindcasts, so this is a **reforecast evaluation**, not a record of live-issued forecasts.

The static **Live (today)** view checks the age of the bundled snapshot, whose source history ends on **2025-08-21**. It withholds a current forecast and labels the historical forecast shown for reference. It does not poll Hub'eau or run a daily service.

![Stale-input state](docs/img/stale.png)

## Frozen results

Numerical results below come from [test_metrics.json](reports/test_metrics.json), [gate.json](reports/gate.json), [frozen_selection.json](reports/frozen_selection.json) and [qc_summary.json](reports/qc_summary.json). [The evidence map](docs/CLAIM_EVIDENCE.md) gives exact keys and the limits of each claim.

All methods are paired on the same eligible days **within each lead**, not across all leads. Test window: **1 Jan–21 Aug 2025**.

| Lead | Paired days | StreamPulse MAE | Water-only ridge | Persistence | Climatology | Skill vs persistence |
|---|---:|---:|---:|---:|---:|---:|
| +1 | 226 | **0.53** | 0.69 | 0.74 | 1.77 | 28% |
| +2 | 225 | **0.68** | 0.94 | 0.97 | 1.76 | 31% |
| +3 | 224 | **0.79** | 1.13 | 1.20 | 1.75 | **34%** |

MAE is in °C. Skill = 1 − MAE / MAE(persistence). Longer leads are exploratory.

**The frozen day-3 gate passed all 6 criteria.** Its MAE gain was **0.41 °C**. The gap-aware moving-block bootstrap gain intervals were **[0.19, 0.64] °C** with **14-day** blocks and **[0.15, 0.69] °C** with **28-day** blocks. The delayed-observation sensitivity retained positive skill. These estimates describe the evaluated period, not future performance.

| Lead | Watch precision | Watch recall | Nominal 90% interval coverage |
|---|---:|---:|---:|
| +1 | 86% | 72% | 95% |
| +2 | 85% | 61% | 95% |
| +3 | 80% | 43% | 98% |

At day **3**, the watch misses more than half of observed exceedances. Persistence has **59%** precision and **54%** recall at that lead: StreamPulse improves precision but loses recall. MAE improvement alone does not prove better field decisions. Only **10** observed exceedance episodes support these indicative watch rates; daily samples are correlated.

![Evaluation view](docs/img/evaluation.png)

## Limits that matter

- **One site and a partial-year test.** Transfer to small urban streams is **UNVERIFIED**.
- **Validation is not a future performance range.** Expanding-window **2024** validation skill was **13.6%**, versus **34%** on the **2025** test. Neither bounds next year's skill.
- **Intervals over-cover.** Nominal **90%** intervals covered **95–98%**; day-3 bias was **−0.40 °C**.
- **Missing weather is operationally important.** Missing or empty runs use a visibly labelled water-only fallback and produce no product alert. Complete-case skill does not measure end-to-end alert availability during outages.
- **The failure case stays visible.** The dashboard includes a forecast that missed abrupt cooling. River discharge is not an input; the cause of that particular miss is **UNVERIFIED**.
- **Chronology checks have limits.** The selection hash and first test-open time are recorded. They are local audit evidence, not independent preregistration or proof that nobody previously inspected the test data.

![Failure case](docs/img/failure-case.png)

## How it works

```text
Hub'eau hourly sensor → QC → source-calendar daily mean → trailing water features → ridge
ECMWF archived run   → forecast air minus last water temperature → fitted correction
                            ↓
              residual interval + seasonal watch → proposed field check → FHIR export
```

The water model is trained on **2010–2022**, tuned on **2023**, then refitted through **2023**. The weather correction is selected using expanding-window **2024** validation, fitting each fold only on earlier observed targets. The final selected model is frozen before the recorded **2025** test opening. The climatology and watch reference use only the refit period. Gaps are not interpolated; conflicting duplicates are quarantined.

The processed history contains **4,527** eligible days out of **5,712** calendar days and **523** archived air-temperature runs. Coverage and input hashes are in [qc_summary.json](reports/qc_summary.json). Download manifests retain URLs, retrieval times and hashes; see [DATA_SOURCES.md](DATA_SOURCES.md).

**Source-clock caveat:** daylight-saving-shaped anomalies suggest a civil-time convention, but do not establish the producer's timestamp transformation or publication latency. Dates remain source-calendar dates. The earlier assertion in the frozen timestamp audit that this was conclusively resolved is superseded by this qualification; its historical report is preserved unchanged.

## Interoperability

The exporter produces a FHIR R4 `collection` Bundle. OAH profiles apply to the site and measurements; forecasts use a local derived profile. Communications, Devices and Provenance use their applicable core/local definitions. This is not OAH certification of the whole application.

| Object | FHIR representation |
|---|---|
| Station | OAH Location with Hub'eau identifier |
| Daily water mean | OAH indicator Observation, UCUM `Cel` |
| Forecast | Locally derived Observation, interval, seasonal reference, watch, simulated origin and replay marker |
| Model and lineage | Versioned Device and Provenance to input Observations |
| Prepared alert | Communication about the Location and forecasts |
| Demo acknowledgement | Completed Communication with `inResponseTo`; no field visit is asserted |

The recorded **HL7 validator 6.10.4** fixture suite reports **0 errors and 0 warnings** on **10 documents**: a **15-resource** fixture Bundle and **9** standalone examples. Its **183** informational messages concern preferred bindings. **Three** negative controls are rejected for their intended defects. Source: [validation summary](reports/fhir-validation/summary.json). This fixture result is distinct from the real replay Bundle validation in [FHIR conformance CI](https://github.com/mohitt31/streampulse/actions/workflows/fhir.yml).

The real demo is [reports/fhir/bundle.json](reports/fhir/bundle.json), generated by `scripts/fhir_real_demo.py`; it contains real replay predictions and a clearly labelled demonstration acknowledgement. [Sandbox evidence](reports/fhir-validation/sandbox_roundtrip.json) records the official endpoint, source hash, transaction status, created resource IDs and read-back checks. Server storage is evidence of transport interoperability; local profile validation remains a separate check.

`RiskAssessment` is not used: this is an environmental observation workflow, not a patient risk assessment. Local definitions are experimental, with no implied HL7/OAH endorsement. See [README_FHIR.md](README_FHIR.md) and [THIRD_PARTY_FHIR.md](THIRD_PARTY_FHIR.md).

## Citizen science hook — proposed integration, not built

A monitoring coordinator could review a watch, then route a site-specific follow-up to a trained volunteer through an agreed integration with the [OAH Citizen Science App](https://www.oneaquahealth.eu/citizen-science-project/). The volunteer would record an observation and, where trained, equipped and authorised, confirm temperature and dissolved oxygen. An expert would review the returned evidence and decide whether biological sampling is appropriate.

The proposed adapter would link the watch, assignment and returned observation by site and alert identifier. App API access, task routing, identity mapping, consent and write-back support are **UNVERIFIED**. No app connection, notification delivery or volunteer deployment is built or claimed.

## Reproduce without reopening the test

```bash
pip install -e ".[dev]" scikit-learn
pytest -q
cd web
npm ci
npm run build
npm run dev
```

Tests use temporary synthetic workspaces; the dashboard uses the committed snapshot. Do not run `streampulse all`, `validate`, `test`, fetchers or report generators in this frozen checkout. For a separate synthetic smoke run:

```bash
streampulse synth --root /tmp/streampulse-smoke
streampulse all --root /tmp/streampulse-smoke
```

For real-data reconstruction, use a separate worktree and output root, preserve the existing evidence, and treat changed inputs or model selection as a new evaluation. FHIR-only instructions are in [README_FHIR.md](README_FHIR.md).

## Next steps

- Confirm source-clock and publication latency with the data producer; then test a scheduled fresh-feed pilot with failure monitoring and a responsible field team.
- Evaluate alert usefulness against persistence at a matched field-visit budget on new data.
- Trial low-cost loggers on small urban streams. Each site needs sensor QA, adequate history, local calibration, independent validation and agreed access; the pipeline can be reused, the Garonne skill cannot.
- Investigate discharge and locally appropriate watch thresholds in a separately specified future evaluation.

## Licence

MIT for project code. Hub'eau data retain the Etalab Open Licence; Open-Meteo data retain CC BY attribution requirements. Third-party FHIR definitions retain their upstream terms.
