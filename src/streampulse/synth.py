"""Synthetic raw data in the exact Hub'eau / Open-Meteo Single Runs file shapes.

Used only for CI and the end-to-end smoke test. Writes data/raw/SYNTHETIC so every
downstream report is stamped as synthetic. Includes the dirty cases QC must handle:
gaps, missing hours, half-day coverage, identical and conflicting duplicates,
excluded qualification codes, implausible values and missing weather runs.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import Paths


def generate(paths: Paths, cfg: dict, seed: int = 7, start: str = "2010-01-01") -> dict:
    rng = np.random.default_rng(seed)
    paths.ensure()
    end = pd.Timestamp(cfg["splits"]["test_end"])
    days = pd.date_range(start, end + pd.Timedelta(days=8), freq="D")
    n = len(days)
    doy = days.dayofyear.to_numpy()
    anom = np.zeros(n)
    for i in range(1, n):
        anom[i] = 0.8 * anom[i - 1] + rng.normal(0, 1.6)
    air = 13 + 9 * np.sin(2 * np.pi * (doy - 110) / 365) + anom
    water = np.empty(n)
    water[0] = 7.0
    for i in range(1, n):
        water[i] = water[i - 1] + 0.18 * (0.85 * air[i] + 1.8 - water[i - 1]) + rng.normal(0, 0.12)

    # hourly readings
    obs_days = days[days <= end]
    recs_by_year: dict[int, list] = {}
    gap_days = set()
    for _ in range(14):
        s = rng.integers(0, len(obs_days) - 60)
        for k in range(int(rng.integers(3, 45))):
            gap_days.add(s + k)
    half_days = set(rng.choice(len(obs_days), 60, replace=False).tolist())
    for i, d in enumerate(obs_days):
        if i in gap_days:
            continue
        hours = range(0, 12) if i in half_days else range(24)
        for hr in hours:
            if rng.random() < 0.03:
                continue
            v = water[i] + 0.45 * np.sin(2 * np.pi * (hr - 9) / 24) + rng.normal(0, 0.05)
            rec = {"code_station": cfg["site"]["station_id"], "date_mesure_temp": d.strftime("%Y-%m-%d"),
                   "heure_mesure_temp": f"{hr:02d}:00:00", "resultat": round(float(v), 2),
                   "code_qualification": "1", "code_unite": "27", "symbole_unite": "°C"}
            recs_by_year.setdefault(d.year, []).append(rec)
    # dirty cases
    y0 = min(recs_by_year)
    base = recs_by_year[y0]
    nb = len(base)
    for j in range(40):
        recs_by_year[y0].append(dict(base[(100 + j) % nb]))                   # identical duplicate
    for j in range(8):
        r = dict(base[(500 + j) % nb]); r["resultat"] = r["resultat"] + 1.3   # conflicting duplicate
        recs_by_year[y0].append(r)
    for j in range(5):
        r = dict(base[(900 + j) % nb]); r["code_qualification"] = "2"         # excluded code
        base[(900 + j) % nb] = r
    base[1200 % nb]["resultat"] = 99.0                                         # implausible

    for yr, recs in recs_by_year.items():
        (paths.raw_hubeau / f"chronique_{cfg['site']['station_id']}_{yr}.json").write_text(
            json.dumps({"station": cfg["site"]["station_id"], "year": yr, "urls": ["synthetic"],
                        "api_count": len(recs), "data": recs}))

    # single runs
    first = pd.Timestamp(cfg["weather"]["first_run"])
    runs = pd.date_range(first, end + pd.Timedelta(days=1), freq="D")
    idx = {d: i for i, d in enumerate(days)}
    n_runs = 0
    for r in runs:
        if rng.random() < 0.02:
            continue                                                            # missing run
        times, vals = [], []
        for off in range(8):
            day = r + pd.Timedelta(days=off)
            err = rng.normal(0, 0.4 + 0.35 * off)
            for hr in range(24):
                times.append((day + pd.Timedelta(hours=hr)).strftime("%Y-%m-%dT%H:%M"))
                vals.append(round(float(air[idx[day]] + err + 4 * np.sin(2 * np.pi * (hr - 9) / 24)
                                        + rng.normal(0, 0.3)), 1))
        js = {"latitude": cfg["site"]["lat"], "longitude": cfg["site"]["lon"], "timezone": "GMT",
              "hourly_units": {"time": "iso8601", "temperature_2m": "°C"},
              "hourly": {"time": times, "temperature_2m": vals}}
        (paths.raw_runs / f"ecmwf_ifs_{r:%Y-%m-%d}_00z.json").write_text(json.dumps(js))
        n_runs += 1
    paths.synthetic_marker.write_text("synthetic data - not real observations\n")
    return {"years": sorted(recs_by_year), "runs": n_runs}
