# StreamPulse recording script

Editorial plan: aim for a narrated demo within the hackathon's required duration. These are recording instructions, not measured results. The numeric result claims below come from the JSON keys listed in [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md). Do not recompute or reopen the test for the video.

## Problem and scope

**Screen:** Replay, then the stale-input view. Use the deployed version only after this PR is merged and Pages is green.

> A river monitoring team cannot visit every site every morning. StreamPulse asks when unusual warmth could justify a temperature and dissolved-oxygen check. This is a historical proof of concept on the Garonne near Toulouse, not a live warning service. The bundled feed is stale, so this view withholds a current forecast. We use archived weather runs and simulated issuance: historical input availability remains unverified. This is a reforecast evaluation.

## Replay

**Screen:** Open the June warm-anomaly example from the alert list. Switch off “What actually happened”, explain the forecast, then reveal the outcome. Show baselines.

> The model forecasts daily mean water temperature for the next three days. The watch line is the seasonal ninetieth percentile from the training history. Crossing it means unusually warm for this site and season, not unsafe water. The shaded band is a nominal ninety-percent prediction interval. Here the observed temperatures crossed the watch line too. The model combines water history with a fitted correction from archived air-temperature forecasts. The useful contribution is the auditable path from prediction to a proposed field check.

## Results and a failure

**Screen:** Evaluation tab, frozen gate, then the cooling failure shown in the README screenshot.

> At day three, mean absolute error is point seven nine degrees, versus one point two zero for persistence: thirty-four percent skill, on two hundred twenty-four paired days. All six frozen gate criteria passed. Validation skill was thirteen point six percent; future performance is not bounded by those results. The watch has eighty-percent precision but forty-three-percent recall. Persistence catches more exceedances, with lower precision. Better temperature accuracy does not prove better field decisions. This cooling event shows a clear forecast miss. Discharge is not an input; we have not established the cause of that miss.

## Network and visit planning

**Screen:** Network tab. Drag the slider to 30 June 2025: every river turns to watch. Scroll to the field-visit planner, show 1 team, then the season table.

> The same frozen method, with no re-tuning, was applied to every station that met a data rule we committed before downloading. Two hundred seventy-four screened, four qualified, all four beat persistence at day three, three of four pass the full gate. The one that fails is shown. In the late-June heatwave all four rivers are on watch, but a team can only go to one or two. The planner ranks them by how far each forecast is above that river's own line. Over the season, this visits about as many real exceedances as persistence, with fewer wasted trips. That comparison was done afterwards, so we label it exploratory.

## Field workflow and its boundary

**Screen:** Acknowledge an alert using a fictional demo role. Point to the local-only explanation.

> The proposed follow-up is to confirm temperature and measure dissolved oxygen with a trained team. OAH supports these measurements; our watch is not an OAH-prescribed trigger. Biological sampling stays an expert decision. This acknowledgement is stored only in this browser. The browser can now download the acknowledgement and demonstration measurements as linked FHIR resources. No notification or field visit is claimed. A proposed future adapter could route a coordinator-approved check through the OAH Citizen Science App, but that integration is not built.

## Interoperability evidence

**Screen:** Real Bundle, FHIR CI, then `reports/fhir-validation/sandbox_roundtrip.json`. Describe only its recorded outcome; do not call a failed or incomplete read-back a success.

> The site and measurements use OAH profiles. Forecasts use a local derived Observation profile, with the interval and simulated origin separated from actual generation time. A Device identifies the model; Provenance links the inputs. The recorded validator fixture suite has zero errors and zero warnings, and deliberately broken examples fail. CI separately validates a real replay Bundle. This sandbox evidence records the transaction and resource read-back checks. Server storage and profile validation are separate tests, neither an OAH endorsement nor proof of deployment.

## Close

**Screen:** Method and data, then repository.

> The public temperature archive we used still stops in August 2025, so a live service needs a direct producer feed. The next step is a supervised pilot: connect that feed, and test whether the watch improves field visits at a fixed budget. Small urban streams need local sensor checks, calibration and new validation. The pipeline is reusable; the Garonne skill does not automatically transfer. StreamPulse makes a narrow claim that can be checked, and makes its missing evidence visible.

## Before recording

- Replace the pending video link after upload; do not leave a placeholder link in the submission.
- Confirm that the deployed site includes the reviewed wording and the report-derived validation skill.
- Show a local-only acknowledgement and an actual negative-control failure.
- Use the committed sandbox evidence; if the server is unavailable during recording, say this is a recorded round-trip.
- Keep the source-clock, reforecast and missing-weather limitations in the narration.

**Field-check beat — approximately 15 seconds:** Open “Log field check”, enter demonstration readings and a UTC time, then download the Bundle.

> Now I log demonstration temperature and oxygen readings. The browser links them to this alert and forecast in a validator-tested FHIR file. Nothing is sent. A spot reading is not a daily-mean forecast-error test.
