"""Reading-level QC and daily aggregation for Hub'eau water temperature.

Rules (contract [qc]):
  * drop readings with excluded qualification codes, wrong units, non-numeric or
    implausible values;
  * collapse identical duplicates (same date, time, value);
  * quarantine conflicting duplicates (same date, time, different values) - all
    copies are dropped and logged;
  * a day is eligible iff it has >= min_hours unique hours and, if required,
    readings in all four 6-hour quarters of the source calendar day;
  * daily mean = mean of hourly means (hours with several readings are averaged
    first, so no hour is over-weighted);
  * gaps are never interpolated: ineligible or missing days stay missing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DAILY_COLUMNS = ["date", "mean_c", "n_hours", "n_quarters", "qual_codes", "eligible"]


def readings_from_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    for col in ("date_mesure_temp", "heure_mesure_temp", "resultat", "code_qualification", "symbole_unite"):
        if col not in df.columns:
            df[col] = None
    out = pd.DataFrame({
        "date": df["date_mesure_temp"].astype("string"),
        "time": df["heure_mesure_temp"].astype("string"),
        "value": pd.to_numeric(df["resultat"], errors="coerce"),
        "qual": df["code_qualification"].astype("string").fillna("NA"),
        "unit": df["symbole_unite"].astype("string").fillna("NA"),
    })
    return out


def _hour(times: pd.Series) -> pd.Series:
    h = pd.to_numeric(times.str.slice(0, 2), errors="coerce")
    return h.where((h >= 0) & (h <= 23))


def build_daily(readings: pd.DataFrame, qc: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (daily, quarantine_log, summary)."""
    r = readings.copy()
    r["reason"] = pd.Series(pd.NA, index=r.index, dtype="string")
    n_in = len(r)

    excl = set(str(c) for c in qc.get("exclude_qual_codes", []))
    allowed_units = set(qc.get("allowed_units", []))
    r["hour"] = _hour(r["time"])
    parsed_date = pd.to_datetime(r["date"], format="%Y-%m-%d", errors="coerce")

    r.loc[parsed_date.isna(), "reason"] = "bad_date"
    r.loc[r["reason"].isna() & r["hour"].isna(), "reason"] = "bad_time"
    r.loc[r["reason"].isna() & r["qual"].isin(excl), "reason"] = "excluded_qual_code"
    if allowed_units:
        r.loc[r["reason"].isna() & ~r["unit"].isin(allowed_units) & (r["unit"] != "NA"), "reason"] = "bad_unit"
    r.loc[r["reason"].isna() & r["value"].isna(), "reason"] = "non_numeric"
    lo, hi = qc.get("plausible_min_c", -1.0), qc.get("plausible_max_c", 40.0)
    r.loc[r["reason"].isna() & ((r["value"] < lo) | (r["value"] > hi)), "reason"] = "implausible"

    dropped = r[r["reason"].notna()]
    ok = r[r["reason"].isna()].copy()

    ident = ok.duplicated(["date", "time", "value"], keep="first")
    n_ident = int(ident.sum())
    ok = ok[~ident]
    conflict = ok.duplicated(["date", "time"], keep=False)
    quarantined = ok[conflict].copy()
    quarantined["reason"] = "conflicting_duplicate"
    ok = ok[~conflict]

    log = pd.concat([dropped, quarantined], ignore_index=True)[["date", "time", "value", "qual", "unit", "reason"]]

    if len(ok):
        ok["hour"] = ok["hour"].astype(int)
        hourly = ok.groupby(["date", "hour"], sort=True).agg(value=("value", "mean")).reset_index()
        quals = ok.groupby("date")["qual"].agg(lambda s: "|".join(sorted(set(map(str, s)))))
        daily = hourly.groupby("date").agg(
            mean_c=("value", "mean"),
            n_hours=("hour", "nunique"),
            n_quarters=("hour", lambda h: int((h // 6).nunique())),
        )
        daily["qual_codes"] = quals
        daily.index = pd.to_datetime(daily.index)
        full = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
        daily = daily.reindex(full)
    else:
        daily = pd.DataFrame(columns=["mean_c", "n_hours", "n_quarters", "qual_codes"],
                             index=pd.DatetimeIndex([], name="date"))

    daily["n_hours"] = daily["n_hours"].fillna(0).astype(int)
    daily["n_quarters"] = daily["n_quarters"].fillna(0).astype(int)
    daily["qual_codes"] = daily["qual_codes"].astype("string").fillna("")
    need_q = 4 if qc.get("require_all_quarters", True) else 0
    daily["eligible"] = (daily["n_hours"] >= int(qc["min_hours"])) & (daily["n_quarters"] >= need_q)
    daily.index.name = "date"
    daily = daily.reset_index()
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    daily = daily[DAILY_COLUMNS]

    years = pd.to_datetime(daily["date"]).dt.year if len(daily) else pd.Series(dtype=int)
    per_year = {}
    for y, g in daily.groupby(years):
        per_year[int(y)] = {
            "calendar_days": int(len(g)),
            "days_with_data": int((g["n_hours"] > 0).sum()),
            "eligible_days": int(g["eligible"].sum()),
        }
    summary = {
        "readings_in": n_in,
        "dropped": {k: int(v) for k, v in dropped["reason"].value_counts().items()},
        "identical_duplicates_collapsed": n_ident,
        "conflicting_duplicates_quarantined": int(len(quarantined)),
        "readings_used": int(len(ok)),
        "days": int(len(daily)),
        "eligible_days": int(daily["eligible"].sum()) if len(daily) else 0,
        "first_date": daily["date"].iloc[0] if len(daily) else None,
        "last_date": daily["date"].iloc[-1] if len(daily) else None,
        "per_year": per_year,
    }
    return daily, log, summary


def daily_series(daily: pd.DataFrame) -> pd.Series:
    """Eligible daily means as a float Series on a continuous daily index (NaN = missing)."""
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    elig = d["eligible"].astype(str).str.lower().isin(["true", "1"])
    y = pd.Series(np.where(elig, d["mean_c"].astype(float), np.nan), index=pd.DatetimeIndex(d["date"]))
    full = pd.date_range(y.index.min(), y.index.max(), freq="D")
    return y.reindex(full).rename("y")
