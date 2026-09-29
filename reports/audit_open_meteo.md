# Open-Meteo Single Runs weekly coverage audit

Generated 2026-09-29T16:46:46.586026+00:00. Model `ecmwf_ifs`; coordinates 43.512148, 1.387766; `temperature_2m`; 00 UTC; `forecast_days=8`; `timezone=GMT`.

76 sampled dates from 2024-03-14 to 2025-08-21; weekly cadence anchored at 2024-03-14, plus endpoint if necessary. One earlier boundary probe. Requests were serial with at least 2 seconds between completion and the next request (maximum 0.5 requests/second; actual rate lower). No automatic retries.

First sampled full run: 2024-03-14. Full runs: 75/76. Exact earliest available date across unsampled history: UNVERIFIED. Every intervening daily run: UNVERIFIED.

HTTP 429 responses: 0. Other request failures/incomplete runs: 1. Check request evidence for HTTP status and headers.

A full run means exactly 192 consecutive hourly timestamps from run-date 00:00 through day 8 23:00, 192 finite temperature values, Celsius and zero UTC offset. These are eight calendar days including initialization day; they are not eight full future days after a noon issuance.

Docs: https://open-meteo.com/en/docs/single-runs-api (accessed during this audit). Documentation identifies early ECMWF coverage as IFS Cycle 49R1 hindcasts. Retrieval proves data availability now, not historical operational publication.

## Every sampled request

| Run date | HTTP | Finite values | Exact axis | Eight full days | Error |
|---|---:|---:|---|---|---|
| 2024-03-13 | 400 | None | None | False | HTTP Error 400: Bad Request |
| 2024-03-14 | 200 | 192 | True | True |  |
| 2024-03-21 | 200 | 192 | True | True |  |
| 2024-03-28 | 200 | 192 | True | True |  |
| 2024-04-04 | 200 | 192 | True | True |  |
| 2024-04-11 | 200 | 192 | True | True |  |
| 2024-04-18 | 200 | 192 | True | True |  |
| 2024-04-25 | 200 | 192 | True | True |  |
| 2024-05-02 | 200 | 192 | True | True |  |
| 2024-05-09 | 200 | 192 | True | True |  |
| 2024-05-16 | 200 | 192 | True | True |  |
| 2024-05-23 | 200 | 192 | True | True |  |
| 2024-05-30 | 200 | 192 | True | True |  |
| 2024-06-06 | 200 | 192 | True | True |  |
| 2024-06-13 | 200 | 192 | True | True |  |
| 2024-06-20 | 200 | 192 | True | True |  |
| 2024-06-27 | 200 | 192 | True | True |  |
| 2024-07-04 | 200 | 192 | True | True |  |
| 2024-07-11 | 200 | 192 | True | True |  |
| 2024-07-18 | 200 | 192 | True | True |  |
| 2024-07-25 | 200 | 192 | True | True |  |
| 2024-08-01 | 200 | 192 | True | True |  |
| 2024-08-08 | 200 | 192 | True | True |  |
| 2024-08-15 | 200 | 192 | True | True |  |
| 2024-08-22 | 200 | 192 | True | True |  |
| 2024-08-29 | 200 | 192 | True | True |  |
| 2024-09-05 | 200 | 192 | True | True |  |
| 2024-09-12 | 200 | 192 | True | True |  |
| 2024-09-19 | 200 | 192 | True | True |  |
| 2024-09-26 | 200 | 192 | True | True |  |
| 2024-10-03 | 200 | 192 | True | True |  |
| 2024-10-10 | 200 | 192 | True | True |  |
| 2024-10-17 | 200 | 192 | True | True |  |
| 2024-10-24 | 200 | 192 | True | True |  |
| 2024-10-31 | 200 | 192 | True | True |  |
| 2024-11-07 | 200 | 192 | True | True |  |
| 2024-11-14 | 200 | 192 | True | True |  |
| 2024-11-21 | 200 | 192 | True | True |  |
| 2024-11-28 | 200 | 192 | True | True |  |
| 2024-12-05 | 200 | 192 | True | True |  |
| 2024-12-12 | 200 | 192 | True | True |  |
| 2024-12-19 | 200 | 192 | True | True |  |
| 2024-12-26 | 200 | 192 | True | True |  |
| 2025-01-02 | 200 | 192 | True | True |  |
| 2025-01-09 | 200 | 192 | True | True |  |
| 2025-01-16 | 200 | 192 | True | True |  |
| 2025-01-23 | 200 | 192 | True | True |  |
| 2025-01-30 | 200 | 192 | True | True |  |
| 2025-02-06 | 200 | 192 | True | True |  |
| 2025-02-13 | 200 | 192 | True | True |  |
| 2025-02-20 | 200 | 192 | True | True |  |
| 2025-02-27 | 200 | 192 | True | True |  |
| 2025-03-06 | 200 | 192 | True | True |  |
| 2025-03-13 | 200 | 192 | True | True |  |
| 2025-03-20 | 200 | 192 | True | True |  |
| 2025-03-27 | 200 | 192 | True | True |  |
| 2025-04-03 | 200 | 192 | True | True |  |
| 2025-04-10 | 200 | 192 | True | True |  |
| 2025-04-17 | 200 | 192 | True | True |  |
| 2025-04-24 | 200 | 192 | True | True |  |
| 2025-05-01 | 200 | 192 | True | True |  |
| 2025-05-08 | 200 | 192 | True | True |  |
| 2025-05-15 | 200 | 192 | True | True |  |
| 2025-05-22 | 200 | 192 | True | True |  |
| 2025-05-29 | 200 | 192 | True | True |  |
| 2025-06-05 | 200 | 192 | True | True |  |
| 2025-06-12 | 200 | 192 | True | True |  |
| 2025-06-19 | 200 | 192 | True | True |  |
| 2025-06-26 | 200 | 192 | True | True |  |
| 2025-07-03 | 200 | 192 | True | True |  |
| 2025-07-10 | 200 | 192 | True | True |  |
| 2025-07-17 | 200 | 192 | True | True |  |
| 2025-07-24 | 200 | 192 | True | True |  |
| 2025-07-31 | 200 | 192 | True | True |  |
| 2025-08-07 | 200 | 0 | True | False |  |
| 2025-08-14 | 200 | 192 | True | True |  |
| 2025-08-21 | 200 | 192 | True | True |  |

Exact URLs, retrieval times and SHA-256 hashes: `audit-evidence/weather_requests.json`. Raw responses: `audit-evidence/weather/`.

## Incomplete-run recheck

A separate repeat request for 2025-08-07T00:00 at 2026-09-29T16:53:40.922792+00:00 returned HTTP 200 and 0 non-null temperature values. Evidence: `audit-evidence/weather_recheck.json`. This recheck is additional to the initial serial weekly sweep.
