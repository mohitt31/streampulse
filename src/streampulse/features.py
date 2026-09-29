"""Leakage-safe feature rows.

Origin D (issuance D 12:00 UTC). With observation delay k, the last usable
observation is L = D - 1 - k. Lead h targets T = D + h.
Every feature uses only y on dates <= L (trailing windows). The label y_T is
kept in a separate column and never enters X.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["last", "m3_d", "m7_d", "change", "doy_sin", "doy_cos", "clim_d"]
ONE = pd.Timedelta(days=1)


def doy365(dates) -> np.ndarray:
    """Day of year on a 365-day calendar (Feb 29 shares Feb 28's slot)."""
    idx = pd.DatetimeIndex(dates)
    d = idx.dayofyear.to_numpy().copy()
    leap_after = np.asarray(idx.is_leap_year) & (idx.month.to_numpy() > 2)
    d[leap_after] -= 1
    feb29 = (idx.month.to_numpy() == 2) & (idx.day.to_numpy() == 29)
    d[feb29] = 59
    return d


def last_obs_date(origins, delay: int) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(origins) - (1 + int(delay)) * ONE


def build_rows(y: pd.Series, origins, lead: int, delay: int, clim_mean: np.ndarray,
               m3_min: int = 2, m7_min: int = 5) -> pd.DataFrame:
    origins = pd.DatetimeIndex(origins)
    L = last_obs_date(origins, delay)

    def at(k: int) -> np.ndarray:
        return y.reindex(L - k * ONE).to_numpy(dtype=float)

    w = np.column_stack([at(k) for k in range(7)])
    last = w[:, 0]
    fin = np.isfinite(w)
    n3, n7 = fin[:, :3].sum(1), fin.sum(1)
    s3 = np.where(fin[:, :3], w[:, :3], 0.0).sum(1)
    s7 = np.where(fin, w, 0.0).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m3 = np.where(n3 >= m3_min, s3 / n3, np.nan)
        m7 = np.where(n7 >= m7_min, s7 / n7, np.nan)
    lag3 = w[:, 3]
    T = origins + int(lead) * ONE
    doy = doy365(T)
    ang = 2 * np.pi * doy / 365.0
    clim_T = np.asarray(clim_mean, dtype=float)[doy - 1]

    df = pd.DataFrame({
        "origin": origins, "target": T, "last_date": L, "lead": int(lead), "delay": int(delay),
        "last": last, "m3_d": m3 - last, "m7_d": m7 - last, "change": last - lag3,
        "doy_sin": np.sin(ang), "doy_cos": np.cos(ang), "clim_d": clim_T - last,
        "clim_T": clim_T, "doy_T": doy,
    })
    df["features_ok"] = np.isfinite(df[FEATURES].to_numpy()).all(axis=1)
    df["y"] = y.reindex(T).to_numpy(dtype=float)
    return df


def input_obs_dates(y: pd.Series, last_date: pd.Timestamp) -> list[str]:
    """Dates actually used by the trailing 7-day window (for provenance/chronology checks)."""
    days = pd.date_range(last_date - 6 * ONE, last_date, freq="D")
    v = y.reindex(days)
    return [d.strftime("%Y-%m-%d") for d, x in v.items() if np.isfinite(x)]


def in_split(rows: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Row belongs to a split iff both origin and target lie inside it (boundary purge)."""
    return (rows["origin"] >= start) & (rows["origin"] <= end) & (rows["target"] >= start) & (rows["target"] <= end)


def attach_air(rows: pd.DataFrame, air_wide: pd.DataFrame, lead: int) -> pd.DataFrame:
    """air_x = mean forecast air (run D 00Z) over D+1..D+lead minus last water obs."""
    rows = rows.copy()
    if air_wide is None or air_wide.empty:
        rows["air_mean"] = np.nan
        rows["weather_run_init"] = pd.NaT
    else:
        cols = [c for c in range(1, int(lead) + 1)]
        a = air_wide.reindex(index=pd.DatetimeIndex(rows["origin"]), columns=cols)
        vals = a.to_numpy(dtype=float)
        ok = np.isfinite(vals).all(axis=1)
        sums = np.where(np.isfinite(vals), vals, 0.0).sum(axis=1)
        rows["air_mean"] = np.where(ok, sums / len(cols), np.nan)
        rows["weather_run_init"] = pd.DatetimeIndex(rows["origin"]).where(ok)
    rows["air_x"] = rows["air_mean"] - rows["last"]
    return rows
