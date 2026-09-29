# Data sources

| Source | What | Access | Licence |
|---|---|---|---|
| Hub'eau "Température des cours d'eau" API | Hourly water temperature, station 05174000 (Garonne upstream of Ariège, Portet-sur-Garonne), 2010 → 2025-08-21 | `scripts/fetch_hubeau.py` → `data/raw/hubeau/`, manifest `data/manifests/hubeau.json` (URL, retrieved_at, sha256, rows) | Licence Ouverte / Etalab 2.0 |
| Open-Meteo Single Runs API | Archived ECMWF IFS 00 UTC runs, hourly `temperature_2m`, 8 forecast days, GMT, from run 2024-03-14 | `scripts/fetch_single_runs.py` → `data/raw/single_runs/`, manifest `data/manifests/single_runs.json` | CC BY 4.0 (Open-Meteo), ECMWF open data terms |

## Known caveats (audits in progress)
- **Hub'eau timezone is unverified.** Daily means use the source calendar day and source hours as published.
- The station series ends **2025-08-21**; the app is a clearly labelled **historical replay** and shows a stale-input state after that date.
- Weather inputs are a **reforecast evaluation**: archived operational runs, used only from run D 00 UTC at issuance D 12 UTC.
