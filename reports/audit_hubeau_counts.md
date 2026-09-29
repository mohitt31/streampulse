# Hub'eau station 05174000: 2010–2025 audit

Audit generated 2026-09-29T16:46:41.713177+00:00. Exact URLs, retrieval timestamps, HTTP status and SHA-256: `audit-evidence/water_requests.json`. Raw responses: `audit-evidence/water/`.

Counts describe returned records, not independently verified sensor accuracy. Times below remain source clock values; timezone UNVERIFIED.

| Year | API count | Downloaded | Unique timestamps | Duplicate rows | First | Last | Complete download |
|---|---:|---:|---:|---:|---|---|---|
| 2010 | 8760 | 8760 | 8759 | 1 | 2010-01-01T00:00:00 | 2010-12-31T23:00:00 | True |
| 2011 | 8760 | 8760 | 8759 | 1 | 2011-01-01T00:00:00 | 2011-12-31T23:00:00 | True |
| 2012 | 8784 | 8784 | 8783 | 1 | 2012-01-01T00:00:00 | 2012-12-31T23:00:00 | True |
| 2013 | 8320 | 8320 | 8319 | 1 | 2013-01-01T00:00:00 | 2013-12-13T15:00:00 | True |
| 2014 | 2169 | 2169 | 2169 | 0 | 2014-10-02T15:00:00 | 2014-12-31T23:00:00 | True |
| 2015 | 8760 | 8760 | 8759 | 1 | 2015-01-01T00:00:00 | 2015-12-31T23:00:00 | True |
| 2016 | 8783 | 8783 | 8782 | 1 | 2016-01-01T00:00:00 | 2016-12-31T23:00:00 | True |
| 2017 | 8760 | 8760 | 8759 | 1 | 2017-01-01T00:00:00 | 2017-12-31T23:00:00 | True |
| 2018 | 5097 | 5097 | 5096 | 1 | 2018-01-01T00:00:00 | 2018-08-01T08:00:00 | True |
| 2019 | 0 | 0 | 0 | 0 | None | None | True |
| 2020 | 0 | 0 | 0 | 0 | None | None | True |
| 2021 | 8624 | 8624 | 8623 | 1 | 2021-01-06T16:00:00 | 2021-12-31T23:00:00 | True |
| 2022 | 8759 | 8759 | 8759 | 0 | 2022-01-01T00:00:00 | 2022-12-31T23:00:00 | True |
| 2023 | 8760 | 8760 | 8759 | 1 | 2023-01-01T00:00:00 | 2023-12-31T23:00:00 | True |
| 2024 | 8780 | 8780 | 8779 | 1 | 2024-01-01T00:00:00 | 2024-12-31T23:00:00 | True |
| 2025 | 5584 | 5584 | 5583 | 1 | 2025-01-01T00:00:00 | 2025-08-21T15:00:00 | True |

## Largest internal gaps

Expected hourly slots are a descriptive assumption, not proof the instrument was scheduled hourly throughout. Boundary censoring before the first/after the last record is not counted as an internal gap.

| Last record before gap | First record after gap | Missing expected interval | Missing hourly slots |
|---|---|---|---:|
| 2018-08-01T08:00:00 | 2021-01-06T16:00:00 | 2018-08-01T09:00:00 → 2021-01-06T15:00:00 | 21343 |
| 2013-12-13T15:00:00 | 2014-10-02T15:00:00 | 2013-12-13T16:00:00 → 2014-10-02T14:00:00 | 7031 |
| 2024-06-07T11:00:00 | 2024-06-07T16:00:00 | 2024-06-07T12:00:00 → 2024-06-07T15:00:00 | 4 |
| 2010-03-28T01:00:00 | 2010-03-28T03:00:00 | 2010-03-28T02:00:00 → 2010-03-28T02:00:00 | 1 |
| 2011-03-27T01:00:00 | 2011-03-27T03:00:00 | 2011-03-27T02:00:00 → 2011-03-27T02:00:00 | 1 |
| 2012-03-25T01:00:00 | 2012-03-25T03:00:00 | 2012-03-25T02:00:00 → 2012-03-25T02:00:00 | 1 |
| 2013-03-31T01:00:00 | 2013-03-31T03:00:00 | 2013-03-31T02:00:00 → 2013-03-31T02:00:00 | 1 |
| 2015-03-29T01:00:00 | 2015-03-29T03:00:00 | 2015-03-29T02:00:00 → 2015-03-29T02:00:00 | 1 |
| 2016-03-27T01:00:00 | 2016-03-27T03:00:00 | 2016-03-27T02:00:00 → 2016-03-27T02:00:00 | 1 |
| 2016-05-06T10:00:00 | 2016-05-06T12:00:00 | 2016-05-06T11:00:00 → 2016-05-06T11:00:00 | 1 |
| 2017-03-26T01:00:00 | 2017-03-26T03:00:00 | 2017-03-26T02:00:00 → 2017-03-26T02:00:00 | 1 |
| 2018-03-25T01:00:00 | 2018-03-25T03:00:00 | 2018-03-25T02:00:00 → 2018-03-25T02:00:00 | 1 |
| 2021-03-28T01:00:00 | 2021-03-28T03:00:00 | 2021-03-28T02:00:00 → 2021-03-28T02:00:00 | 1 |
| 2022-03-27T01:00:00 | 2022-03-27T03:00:00 | 2022-03-27T02:00:00 → 2022-03-27T02:00:00 | 1 |
| 2023-03-26T01:00:00 | 2023-03-26T03:00:00 | 2023-03-26T02:00:00 → 2023-03-26T02:00:00 | 1 |

See machine-readable summary for qualification and duplicate-conflict counts. Do not discard a whole partial year: retain eligible uninterrupted windows. API qualification `4` is non-qualified, not independently validated.

Station metadata was rechecked separately: `audit-evidence/station_metadata_request.json` records the successful request, retrieval time and response hash; this follows the initial metadata-request timeout recorded in the sweep log.
