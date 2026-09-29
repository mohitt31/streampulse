# Data sources

| Source | What | Access | Licence |
|---|---|---|---|
| Hub'eau "Température des cours d'eau" API | Hourly water temperature, station 05174000 (Garonne upstream of Ariège, Portet-sur-Garonne), 2010 → 2025-08-21 | `scripts/fetch_hubeau.py` → `data/raw/hubeau/`, manifest `data/manifests/hubeau.json` (URL, retrieved_at, sha256, rows) | Licence Ouverte / Etalab 2.0 |
| Open-Meteo Single Runs API | Archived ECMWF IFS 00 UTC runs, hourly `temperature_2m`, 8 forecast days, GMT, from run 2024-03-14 | `scripts/fetch_single_runs.py` → `data/raw/single_runs/`, manifest `data/manifests/single_runs.json` | CC BY 4.0 (Open-Meteo), ECMWF open data terms |

## Known caveats (audits in progress)
- **Hub'eau does not document the timezone.** The data shows it is French civil time (Europe/Paris): on every spring daylight-saving Sunday (12 years on record) 02:00 is missing and 03:00 is doubled. Those 24 conflicting readings are quarantined. Daily means use the source (local) calendar day, which is complete before the 12:00 UTC issuance.
- Station gap: no data Aug 2018 to Jan 2021; 2014 mostly missing. Never interpolated.
- ECMWF runs missing for 2025-08-05, -06, -08, -09; run 2025-08-07 returned all nulls. Those days are excluded from scoring.
- The station series ends **2025-08-21**; the app is a clearly labelled **historical replay** and shows a stale-input state after that date.
- Weather inputs are a **reforecast evaluation**: archived operational runs, used only from run D 00 UTC at issuance D 12 UTC.
