# Senior judge and red-team review

Reviewed repository base: `32351b6ff53d3c00377359a585b3af88f4c89443`. Review date: 2026-09-30 local time. This review preserves the frozen evaluation. Scores, effort estimates and placing probabilities below are subjective judgements, not report-derived model results or calibrated probabilities.

## Ruling

Keep Track 6 primary and Track 7 secondary. StreamPulse is a credible retrospective forecasting prototype, with unusually explicit baseline comparisons and reproducibility evidence. It is not yet a proven early-warning service. The remaining competitive weakness is measured usefulness to a monitoring team, followed by limited algorithmic novelty and large-river-to-urban-stream transfer.

There is no demonstrated fatal flaw in the inspected date-based split, fitting or frozen gate implementation. That is not a proof of historical real-time availability or a full independent reproduction of the original evaluation. The frozen test was not rerun. The missing final video link is the immediate submission blocker; the recording/submission itself is UNVERIFIED.

## Rubric assessment after this PR

| Criterion | My score | Reason |
|---|---:|---|
| Impact / OAH alignment | 21/30 | A specific temperature/oxygen follow-up and OAH-derived data representation make the link credible. No field partner, sampled outcome, volunteer integration or measured benefit is established. The Garonne is not the intended small urban-stream setting. |
| Innovation | 13/20 | Auditable reforecast-to-action integration is useful; ridge plus an air correction, thresholds and a dashboard are established methods. A claim of novel modelling would be weak. |
| Technical | 18/20 | Paired baselines, frozen gate, gap-aware bootstrap, chronology checks, negative FHIR controls and an actual sandbox transaction are strengths. Historical publication latency and archive vintage remain unresolved. |
| Usability | 12/15 | Live replay, outcome reveal, visual baseline comparison, missing-weather labels and stale refusal are clear. Acknowledgement is local-only; no responsible assignee, delivery or completed follow-up evidence exists. |
| Feasibility | 10/15 | Static deployment and a small interpretable model are feasible. Operational ingestion, latency, ownership of follow-ups and transfer to new sites require a supervised pilot. |
| **Total** | **74/100** | Plausible finalist quality; not an obvious winner on present evidence. Treat this as roughly ±5 points, not a prediction of judge scores. |

## Ranked changes

Estimated score gains are weighted total-score points, overlap, and must not be added mechanically. Effort excludes waiting for third parties.

| Rank | Change | Expected gain | Hours | Risk / status |
|---|---|---:|---:|---|
| 1 | Record and link a concise finished video showing replay → revealed outcome → failure → local acknowledgement → validator → sandbox evidence | +3–6 | 2–4 | Low; proposed. Missing submission asset is the immediate blocker. |
| 2 | Correct historical-availability, operational, OAH-trigger, future-skill-range and numerical claims | +2–4 | 1–2 | Low; implemented. Preserves credibility under expert questioning. |
| 3 | Official sandbox transaction and complete resource read-back with content comparison | +2–4 | 1–2 | Low; implemented. Demonstrates transport, not app deployment or clinical benefit. |
| 4 | Obtain a monitoring practitioner's review of the watch-to-visit decision and document the pilot owner, sampling capacity and acceptance criteria | +2–5 | 3–6 | Depends on an external reviewer; proposed. Do not invent endorsement or outcomes. |
| 5 | Add an actual browser-acknowledgement export or persisted assignment/return workflow, with a demo-only boundary | +1–3 | 3–5 | Medium; proposed. Current wording now discloses the local-only boundary. |
| 6 | Citizen Science App hook with explicit proposed/not-built boundary and unverified API assumptions | +0.5–1.5 | 0.25–0.5 | Low; implemented. A paragraph alone is not an integration or a large Impact gain. |
| 7 | Future matched-budget alert evaluation and prospective small-stream validation | +3–6 if actually evidenced | Multiple days/weeks | High before deadline; propose only. Requires new data and a new protocol, never retuning this test. |

## Competitor comparison

The following are public-repository/source/evidence reviews, not independently rerun competitor test suites. Their deployed uptime, user outcomes, validation execution and final submissions are **UNVERIFIED** in this review. Do not equate README claims with independently observed success.

| Competitor and inspected revision | What they show | StreamPulse advantage | StreamPulse disadvantage |
|---|---|---|---|
| [StreamLink](https://github.com/N-H-L/streamlink-oneaquahealth/tree/66e19e5f4faac40987e799d121523929d811a6a9) | Volunteer → expert → lab referral → feedback workflow; committed validator and sandbox lifecycle evidence. | Stronger explicit within-site forecasting/baseline result for a narrow target. | StreamLink has the more complete OAH operational workflow and broader standards story. It is the strongest direct Track 7 threat here. |
| [Rill](https://github.com/shi1720/OneAquaHealth/tree/8c0cd6541d8a61d9d960b1f42f51abf5f79dd093) | Capacity-constrained visit planning, assignment and meaningful recheck in a persistent workspace; openly described heuristic and synthetic demo. | Real environmental reforecast evaluation and more specific OAH profile/validator evidence. | Rill makes the responsible user's decision and follow-through clearer. It can beat StreamPulse on Impact and feasibility even without a predictive model. |
| [StreamProof](https://github.com/Hexraei/StreamProof/tree/35ba347c2f172087b9e4a50a39b2f0232095381a) | Narrow measurement QA → human approval → draft-aligned FHIR export; explicit refusal of unsupported photo claims. | Stronger conformance and real numerical evaluation evidence. | Its workflow is easier to explain quickly. In the inspected FHIR builder, `urn:uuid:loc-...` and `urn:uuid:obs-...` are not UUIDs; it explicitly does not claim conformance. Do not treat its export as equivalent to validator evidence. |
| [StreamVitals](https://github.com/kathir-iTech/streamvitals/tree/7d2d10c70337a6ab8deb2add75d68f3fba6b9d1c) | Guided official indicator collection, lab-only boundaries, local persistence, bounded factsheet assistance. | Clearer measured forecasting result and FHIR lineage. | More direct use of official OAH biological indicators and citizen field collection. StreamPulse's citizen connection is only proposed. |

Likely pattern: StreamLink and Rill are serious threats; StreamPulse has a more defensible quantitative core than the simpler collection/QA entries, but judges need not weight that above a complete One Health workflow. None of these repositories establishes the strength or size of the full entrant field.

## Findings and dispositions

### Fixed without changing the evaluation

- Corrected the assertion that every lead used 224 days: lead-specific counts are 226, 225 and 224.
- Corrected validation skill to 13.6% from the frozen value. The UI previously recomputed skill from MAEs rounded to three decimals, yielding 13.5%. The web packer now carries full report precision for headline MAE/skill, and display formatting rounds at the end. This also fixes the day-1 climatology display rounding.
- Removed the supposed validation-to-test range for future annual skill. Neither period bounds future performance.
- Added the omitted alert trade-off: day-3 persistence recall exceeds product recall, despite worse precision. A matched-cost or matched-budget field comparison is still needed before claiming operational benefit.
- Replaced “OAH protocol thermal trigger” with a proposed follow-up informed by the framework. The framework does not verify this percentile-to-visit rule.
- Qualified source-clock inference and archive availability. The frozen timestamp audit's later confident paragraph is retained as historical evidence, with a current qualification in the submission and evidence map.
- Replaced “already runs operationally/daily” and “only a fresh feed needed”. This is a static snapshot replay, with browser-local acknowledgement and separate Python export.
- Distinguished validator fixtures from real replay validation. The old FHIR handoff README incorrectly implied the committed real Bundle still used synthetic prediction values.
- Removed unsupported numeric prose derived only from CSV/JSONL or uncommitted accessibility results. Added a JSON claim-source map.
- Added a proposed citizen-app handoff without claiming an API, notification, app partnership or completed integration.
- Added a Pages build on relevant pull requests, while deployment remains restricted to main. No branch deployment or main push is required to verify the build.

### Sandbox evidence

The official [webinar presentation](https://www.oneaquahealth.eu/app/uploads/2026/09/OneAquaHealth_hackathon_session_4_Aug27-2026.pdf) identifies the server. It returned an R4 CapabilityStatement advertising transactions. A single transaction POST created 72 tagged resources from the unchanged real demo Bundle, each with a 201 response. Every resource was read back with HTTP 200 and compared for equal content after excluding only server IDs/version metadata and equivalent reference rewriting. The first GET timed out; read-only resume completed the check without another POST. The retained evidence includes this failure.

No credentials were used, no existing shared resources were overwritten, and no field sampling is asserted. `reports/fhir-validation/sandbox_roundtrip.json` is the only added report. Its transport success does not prove that the server enforced every local profile; official validator evidence is separate.

### Proposed only

- Do not change the frozen weather correction, thresholds, features, quality rules, lead selection or test gate. No model change is necessary to preserve the narrow reforecast claim.
- River discharge, alternative thermal thresholds, different lead policies and interval recalibration belong in a newly specified study with new holdout evidence.
- Evaluate expected field value at a common visit budget, including missing-run days. The existing complete-case test cannot establish that deployment policy's benefit.
- Confirm measurement timezone transformation and acquisition/publication delay with the producer. A DST pattern alone is insufficient to prove both.
- App integration, shared acknowledgement storage, responsible assignees and returned field measurements require actual engineering and operational agreements.
- Pilot low-cost loggers on small streams only with local QA/calibration and fresh evaluation. Do not transfer the Garonne skill claim.

## Verification scope

The deployed StreamPulse replay loaded; the Live view withheld current forecasts; the Evaluation view exposed metrics, gate and limitations. Visual hierarchy was inspected. Source review covered the model/splits, feature chronology, gate, FHIR exporter/validation workflow and browser acknowledgement path. This is not a full penetration test or accessibility certification. Competitor runtimes were not executed.

Existing tests were run locally on temporary synthetic data; the web production build was run. New offline sandbox tests check reference closure, non-mutating POST conversion and read-back rejection of changed values/references. Existing protected files and all pre-existing reports were compared with pre-review SHA-256 hashes and stayed unchanged. CI and PR status are linked in the pull request rather than represented as frozen evaluation results.

## Independent placing estimate

**Top 3: 18%. First place: 4%.** These are subjective estimates conditional on a complete eligible submission, a clear video and a field of roughly 20–40 serious entries. Field size, entrant quality, judge preferences and the final video are UNVERIFIED. Plausible uncertainty is broad: roughly 10–30% top-three and 1–8% first.

Why not higher: Impact is the largest weight; no measured monitoring benefit or complete field workflow is established, and the model is conventional. Why not lower: real held-out temperature evaluation, visible failure cases, precise limitations, conformance tests and now a successful official sandbox round-trip distinguish this from a cosmetic dashboard. A rushed model change is less valuable than a finished video and a credible practitioner-reviewed pilot plan.
