# StreamPulse FHIR workstream handoff

This package adds a Python 3.11 standard-library exporter, an experimental local FHIR R4 IG derived from the pinned OAH IG, standalone examples, official-validator checks and negative controls, CI, and three reproducible data audits. It does not modify Claude's ingestion/model/UI contract.

## Pasteable README section

StreamPulse exports a self-contained FHIR R4 collection Bundle: OAH Locations and input Observations, locally profiled forecast Observations, versioned model Devices, preparation-state alert Communications, demo acknowledgement Communications, and Provenance. Replay origin and actual publication time are separate. Dates retain source-calendar precision because Hub'eau's temperature timezone remains UNVERIFIED. No RiskAssessment, patient cohort, clinical risk, actual authority integration, or delivered alert is fabricated. The local definitions are experimental project artifacts; no HL7/OAH endorsement is implied.

The OAH source is pinned to `b907cf0869b59d82d9138b3d147fca66f333d911`; SUSHI is pinned to `3.20.1`; the official HL7 validator is pinned to `6.10.4` and its release SHA-256 is checked. Validation uses FHIR `4.0.1`, compiled OAH and local profiles, and the online terminology server. CI rejects errors, unresolved claimed profiles, unreviewed warnings, and negative controls that fail for the wrong reason. See `reports/fhir-validation/summary.json` and `WARNINGS.md` for measured results.

## Install and reproduce

Prerequisites: Python 3.11, Node 22/npm, Java 21, git, curl, and internet for dependency/terminology retrieval. Run from repository root. Java must be on PATH, or set `SP_JAVA` to its executable. Set `SP_PYTHON` if your Python 3.11 executable has a different name.

```bash
export SP_PYTHON=python3.11
bash scripts/build_fhir.sh
python3.11 scripts/make_fhir_examples.py
bash scripts/validate_fhir.sh --fixtures
python3.11 -m unittest discover -s tests/fhir -v
```

Export **Claude's actual files**, then validate them:

```bash
PYTHONPATH=src python3.11 -m streampulse.fhir_export
bash scripts/validate_fhir.sh
```

Defaults are the unchanged contract paths: `data/processed/daily_water.csv`, `reports/forecasts.jsonl`, `reports/alerts.jsonl`; output `reports/fhir/bundle.json`. `--station-metadata` defaults to the included verified station metadata. CLI flags can select different input/output locations. References are deterministic `urn:uuid` values with an in-Bundle closure; no FHIR server is required.

Reproduce the included **explicitly synthetic forecast demonstration** without actual modelling outputs:

```bash
PYTHONPATH=src python3.11 -m streampulse.fhir_export \
  --daily tests/fixtures/fhir/daily_water.csv \
  --forecasts tests/fixtures/fhir/forecasts.jsonl \
  --alerts tests/fixtures/fhir/alerts.jsonl \
  --demo-fixture
bash scripts/validate_fhir.sh
```

The checked-in demo Bundle contains real source-derived daily inputs but synthetic prediction values and a synthetic acknowledgement. The all-zero model version is deliberately a fixture marker, not an asserted real model commit. `make_fhir_examples.py` does not overwrite the actual `reports/fhir/bundle.json`; it writes a separate fixture Bundle. Inspect `reports/INTERFACE_NOTES.md` before integration, especially alert delivery, watch policy, timestamp precision, model identity and weather provenance.

Re-run network audits (about 76 weekly weather samples plus a pre-boundary probe, and 16 water years; raw evidence is included):

```bash
python3.11 scripts/audit_data.py --only both
python3.11 scripts/audit_timestamp.py
```

The recorded August 7 weather recheck is additional evidence from the delivered run; the main audit reproduces the full weekly sweep. Network data can change; retain the delivered request logs and hashes to compare snapshots.

## Integration and licences

Unzip into the repository root after reviewing overlapping paths. No root `pyproject.toml`, application code, or model-pipeline code is replaced. This is delivered as files; the remote repository was not accessible anonymously during this run and no commit/push was performed. GitHub Actions configuration was exercised through its local commands; execution on GitHub itself is UNVERIFIED.

Add `vendor/`, `tools/`, and `fhir/node_modules/` to the repository's existing ignore rules as appropriate. The build script fetches the exact OAH commit. Its cache package contains unchanged compiled upstream conformance definitions and carries the pinned source identity. It is a local dependency package, not an official OAH publication. Public hosting of the user's canonical URLs is not required for these local checks; canonical deployment is UNVERIFIED.

Our code/FSH is supplied under the MIT licence in `LICENSE_FHIR.txt`. OAH definitions, source documentation, Hub'eau and Open-Meteo data keep their original licences/attributions. The ZIP includes an OAH-derived package strictly as dependency evidence; do not relabel it MIT. Exact upstream redistribution/licence terms should be retained and checked before republishing third-party artifacts. See `THIRD_PARTY_FHIR.md`.
