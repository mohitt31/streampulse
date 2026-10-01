# Hub'eau temperature timestamp convention audit

Generated 2026-09-29T16:53:40.830716+00:00.

## Ruling: timezone UNVERIFIED

The documentation and Swagger schema inspected do not state whether `date_mesure_temp` / `heure_mesure_temp` use UTC, local civil time, fixed standard time, or a producer-specific clock. The API returns separate date and time fields without UTC offset. This is a finding about the inspected sources, not proof that no producer documentation exists.

Exact requests, retrieval timestamps, HTTP status and SHA-256 hashes are in `audit-evidence/timestamp_requests.json`. Sources:

- https://hubeau.eaufrance.fr/page/api-temperature-continu — 2026-09-29T16:53:38.984993+00:00; HTTP 200; captured
- https://hubeau.eaufrance.fr/api/v1/temperature/api-docs — 2026-09-29T16:53:39.997725+00:00; HTTP 200; captured

## Schema fields

```json
{
  "date_mesure_temp": {
    "type": "string",
    "format": "date-time",
    "example": "2016-12-01",
    "description": "Date de la mesure"
  },
  "heure_mesure_temp": {
    "type": "string",
    "example": "16:12:36",
    "description": "Heure de la mesure"
  }
}
```

## Safest handling

- Preserve raw date and source-clock time. Do not append Z or infer Europe/Paris from coordinates.
- Keep the pipeline's daily source-calendar `date` unchanged. FHIR raw examples use date-only effectiveDateTime and retain the original hour in a note. Forecast effectivePeriod uses the same date for start and end at date precision: that source calendar day; no midnight UTC boundary is invented.
- Actual generation and acknowledgement timestamps must be explicitly timezone-aware. Simulated issuance remains the contract's UTC timestamp and is a separate extension.
- Weather alignment needs producer confirmation or an explicitly declared source-clock assumption plus sensitivity analysis. Do not call it fully verified while unresolved.
- DST-shaped duplicates or yearly counts are not proof of timezone. Do not borrow the separate hydrometry API's convention.
- Telemetry availability / publication delay is separate from timestamp convention and remains UNVERIFIED.

The ZIP includes the relevant schema excerpt in `audit-evidence/timestamp_schema_excerpt.json`; full upstream documentation pages are not redistributed. Full-response hashes remain in the request log for reproducibility.

## Update (2026-09-30): convention resolved from the data

The documentation is silent, but the records themselves settle it. On the spring daylight-saving Sunday of every year on record (2010–2013, 2015–2018, 2021, 2023–2025), hour `02` is absent and hour `03` appears twice with different values; autumn transitions show no gap. That is the signature of French civil time (Europe/Paris, CET/CEST). The 24 conflicting `03:00` readings are quarantined by QC. Consequence for leakage: a local calendar day ends at 22:00 or 23:00 UTC of that day, so day D−1 is complete before the 12:00 UTC issuance on day D. Reproduce with `reports/audit-evidence` and `data/processed/qc_quarantine.csv` (or `streampulse ingest`).

Raw per-request responses (`audit-evidence/water/`, `audit-evidence/weather/`, about 22 MB) are not committed; `scripts/audit_data.py` re-downloads them and `*_requests.json` keeps each URL, time and SHA-256.
