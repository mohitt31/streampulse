import numpy as np
import pandas as pd

from streampulse.config import load_contract
from streampulse.quality import build_daily, daily_series, readings_from_records

QC = load_contract()["qc"]


def rec(date, hour, v, q="1", unit="°C", minute=0):
    return {"date_mesure_temp": date, "heure_mesure_temp": f"{hour:02d}:{minute:02d}:00", "resultat": v,
            "code_qualification": q, "symbole_unite": unit}


def day(date, hours, v=10.0):
    return [rec(date, h, v + h * 0.01) for h in hours]


def run(recs):
    return build_daily(readings_from_records(recs), QC)


def test_eligibility_needs_18_hours_and_all_quarters():
    recs = day("2020-01-01", range(24)) + day("2020-01-02", range(17)) + \
        day("2020-01-03", list(range(0, 18))) + day("2020-01-04", [h for h in range(24) if not 6 <= h < 12]) + \
        day("2020-01-05", [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20])
    d, _, _ = run(recs)
    e = dict(zip(d["date"], d["eligible"]))
    assert e["2020-01-01"]
    assert not e["2020-01-02"]           # 17 hours
    assert not e["2020-01-03"]           # 18 hours but quarter 18-23 missing
    assert not e["2020-01-04"]           # 18 hours, quarter 06-11 missing
    assert d.set_index("date").loc["2020-01-04", "n_quarters"] == 3
    assert e["2020-01-05"]               # exactly 18 hours spread over all 4 quarters


def test_identical_duplicate_collapsed_conflict_quarantined():
    base = day("2020-01-01", range(24))
    recs = base + [dict(base[0])] + [dict(base[5], resultat=base[5]["resultat"] + 2.0)]
    d, log, s = run(recs)
    assert s["identical_duplicates_collapsed"] == 1
    assert s["conflicting_duplicates_quarantined"] == 2
    assert (log["reason"] == "conflicting_duplicate").sum() == 2
    row = d.set_index("date").loc["2020-01-01"]
    assert row["n_hours"] == 23 and bool(row["eligible"])


def test_excluded_code_unit_and_range():
    recs = day("2020-01-01", range(24))
    recs[0]["code_qualification"] = "2"
    recs[1]["symbole_unite"] = "K"
    recs[2]["resultat"] = 55.0
    recs[3]["resultat"] = "n/a"
    _, log, s = run(recs)
    assert s["dropped"] == {"excluded_qual_code": 1, "bad_unit": 1, "implausible": 1, "non_numeric": 1}


def test_hourly_means_not_overweighted():
    recs = [rec("2020-01-01", h, 10.0) for h in range(24)] + [rec("2020-01-01", 0, 30.0, minute=m) for m in (15, 30, 45)]
    d, _, _ = run(recs)
    # hour 0 = mean(10,30,30,30)=25; daily = (25 + 23*10)/24
    assert abs(d["mean_c"].iloc[0] - (25 + 230) / 24) < 1e-9


def test_gaps_not_interpolated_and_partial_year_kept():
    recs = day("2020-01-01", range(24)) + day("2020-01-05", range(24))
    d, _, _ = run(recs)
    assert list(d["date"]) == ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05"]
    y = daily_series(d)
    assert np.isnan(y.loc["2020-01-03"]) and np.isfinite(y.loc["2020-01-05"])
