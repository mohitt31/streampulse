# StreamPulse

Historical proof of concept on the Garonne at Portet-sur-Garonne, near Toulouse: leakage-safe 1–3 day forecasts of daily mean river water temperature, a thermal watch against a site-specific 90th percentile, and an OneAquaHealth-conformant FHIR record of observations, forecasts and follow-up alerts.

> Status: pipeline and evaluation contract frozen; real-data results pending. Full README with results, screenshots and video comes before submission.

## Reproduce
```bash
pip install -e ".[dev]"
python3 scripts/fetch_hubeau.py          # Hub'eau history, one file per year
python3 scripts/fetch_single_runs.py     # archived ECMWF IFS 00Z runs
streampulse ingest && streampulse validate && streampulse test && streampulse gate
pytest -q
```
The evaluation contract is `config/contract.toml`. `validate` never touches 2025; `test` opens 2025 once and records the frozen-selection hash in `reports/test_lock.json`.

Smoke test without network: `streampulse synth --root /tmp/sp && streampulse all --root /tmp/sp` (all outputs stamped SYNTHETIC).

Licence: MIT. Data sources: see DATA_SOURCES.md.
