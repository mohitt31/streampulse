"""Raw files -> data/processed (daily_water.csv, air_runs_daily.csv) + QC reports."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Paths, sha256_file
from .quality import build_daily, readings_from_records


def load_hubeau_raw(raw_dir: Path) -> pd.DataFrame:
    files = sorted(raw_dir.glob("chronique_*.json"))
    if not files:
        raise FileNotFoundError(f"no Hub'eau files in {raw_dir}; run scripts/fetch_hubeau.py")
    recs: list[dict] = []
    for f in files:
        recs.extend(json.loads(f.read_text())["data"])
    return readings_from_records(recs)


def load_single_runs(raw_dir: Path) -> pd.DataFrame:
    """Long table: run_date, offset_days, valid_date, air_mean_c, n_hours.

    Daily means use GMT calendar days and need all 24 hourly values.
    """
    rows = []
    for f in sorted(raw_dir.glob("*_00z.json")):
        js = json.loads(f.read_text())
        run_date = pd.Timestamp(f.stem.split("_")[-2])
        h = js.get("hourly", {})
        t = pd.to_datetime(pd.Series(h.get("time", [])))
        v = pd.to_numeric(pd.Series(h.get("temperature_2m", [])), errors="coerce")
        if len(t) == 0:
            continue
        df = pd.DataFrame({"day": t.dt.normalize(), "v": v})
        g = df.groupby("day")["v"].agg(["mean", "count"])
        for day, rec in g.iterrows():
            rows.append({
                "run_date": run_date, "offset_days": int((day - run_date).days), "valid_date": day,
                "air_mean_c": float(rec["mean"]) if rec["count"] == 24 else np.nan, "n_hours": int(rec["count"]),
            })
    out = pd.DataFrame(rows, columns=["run_date", "offset_days", "valid_date", "air_mean_c", "n_hours"])
    return out


def run_ingest(cfg: dict, paths: Paths) -> dict:
    paths.ensure()
    readings = load_hubeau_raw(paths.raw_hubeau)
    daily, log, summary = build_daily(readings, cfg["qc"])
    daily.to_csv(paths.daily_water, index=False, float_format="%.4f")
    log.to_csv(paths.processed / "qc_quarantine.csv", index=False)

    air = load_single_runs(paths.raw_runs)
    air_out = air.copy()
    for c in ("run_date", "valid_date"):
        air_out[c] = pd.to_datetime(air_out[c]).dt.strftime("%Y-%m-%d")
    air_out.to_csv(paths.air_runs, index=False, float_format="%.4f")

    summary["synthetic"] = paths.is_synthetic()
    summary["daily_water_sha256"] = sha256_file(paths.daily_water)
    summary["air_runs"] = {
        "runs": int(air["run_date"].nunique()) if len(air) else 0,
        "first_run": str(air["run_date"].min().date()) if len(air) else None,
        "last_run": str(air["run_date"].max().date()) if len(air) else None,
        "sha256": sha256_file(paths.air_runs),
    }
    (paths.reports / "qc_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


def load_air_wide(paths: Paths) -> pd.DataFrame:
    """Index run_date, columns offset 0..7 -> daily mean forecast air temperature."""
    if not paths.air_runs.exists():
        return pd.DataFrame()
    a = pd.read_csv(paths.air_runs)
    if a.empty:
        return pd.DataFrame()
    a["run_date"] = pd.to_datetime(a["run_date"])
    w = a.pivot_table(index="run_date", columns="offset_days", values="air_mean_c", aggfunc="first")
    return w.sort_index()
