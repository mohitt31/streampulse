# Submission claim evidence

All performance numbers in README, Devpost and narration are rounded from the frozen JSON below. No evaluation was rerun for this review. Track labels, protocol names, FHIR versions, station identifiers, formula constants, dates and editorial recording instructions are not performance measurements; their provenance is distinguished here.

| Claim | Source and key |
|---|---|
| Test window | `reports/test_metrics.json.test_window` |
| Paired count by lead | `reports/test_metrics.json.runs.primary.leads.<lead>.n_paired` |
| MAE, bias, skill | Same lead's `models.<model>.{mae,bias,skill_vs_persistence}` |
| Watch precision, recall, confusion counts | Same model's `watch` |
| Interval coverage | Same model's `interval90.coverage` |
| Exceedance episodes | Same lead's `observed_exceedance_episodes` |
| Gate pass and bootstrap intervals | `reports/gate.json.{passed,criteria}`; gain is criterion 3; intervals are criterion 4 `value.b14/b28` |
| Validation skill | `reports/frozen_selection.json.primary.val_metrics.3.expanding_window_paired.full.skill_vs_persistence` = 0.13580618697387903, rounded to 13.6%, not the previous 13.5% calculated from pre-rounded MAEs |
| Training/tuning/refit/validation dates | `reports/frozen_selection.json.splits` |
| Reference period, percentile and window | `reports/frozen_selection.json.primary.climatology.{start,end,quantile,window}` |
| Available history and weather runs | `reports/qc_summary.json.{eligible_days,days,last_date,air_runs.runs}` |
| Recorded chronology and local freeze ordering | `reports/chronology.json.checks`; `reports/test_lock.json`; these do not prove independent preregistration |
| Fixture validator version, FHIR version, counts and negatives | `reports/fhir-validation/summary.json`; omitted error/warning severities in positive counts mean none recorded, not an unexecuted validator |
| Real sandbox result | `reports/fhir-validation/sandbox_roundtrip.json`; created resource count is the length of `resources`; read success requires both HTTP success and `content_matches` |
| Station identifier | `reports/audit-evidence/water_summary.json`; real FHIR demo Location in `reports/fhir/bundle.json` |
| Simulated issuance and forecast lead/interval fields | Forecast Observations and extensions in `reports/fhir/bundle.json`; generated from the real JSONL replay |

The original monthly table and narrated individual temperatures relied on CSV/JSONL or dashboard derivations rather than a frozen JSON summary. They were removed from submission prose rather than creating new evaluation numbers. The dashboard may still show its existing descriptive monthly breakdown, clearly limited to the recorded test.

The prior accessibility zero-violation claim had no committed JSON report, so it was removed from submission prose. Accessibility test code remains available; a complete accessibility certification is not claimed.

OAH framework and citizen-app claims are sourced to the official pages linked in README. Those pages support measurements and citizen observation collection; app task APIs and a thermal-watch trigger are UNVERIFIED.

Earlier prose in `reports/audit_timestamp.md` claims the timezone was resolved from DST-shaped anomalies. That frozen report is retained unchanged. Current submission wording qualifies the inference: source timezone transformation, historical publication latency, and contemporaneous availability of archive inputs remain UNVERIFIED.
