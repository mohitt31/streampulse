"""Leakage tests: perturbing anything the forecaster could not have seen at issuance
must not change features, fitted models or predictions."""
import numpy as np
import pandas as pd
import pytest

from streampulse.baselines import fit_climatology
from streampulse.features import FEATURES, attach_air, build_rows, in_split, input_obs_dates
from streampulse.metrics import _blocks, block_bootstrap_ci


@pytest.fixture
def y():
    idx = pd.date_range("2015-01-01", "2018-12-31", freq="D")
    rng = np.random.default_rng(0)
    v = 12 + 8 * np.sin(2 * np.pi * idx.dayofyear / 365) + rng.normal(0, 0.5, len(idx))
    s = pd.Series(v, index=idx)
    s.iloc[100:110] = np.nan
    return s


CLIM = np.full(365, 12.0)


@pytest.mark.parametrize("delay", [0, 1])
@pytest.mark.parametrize("lead", [1, 3, 7])
def test_features_ignore_future(y, lead, delay):
    origins = pd.date_range("2017-03-01", "2017-10-01", freq="D")
    base = build_rows(y, origins, lead, delay, CLIM)
    for D in origins[::17]:
        L = D - pd.Timedelta(days=1 + delay)
        y2 = y.copy()
        y2[y2.index > L] += 100.0              # corrupt everything not yet observed
        r1 = base[base["origin"] == D][FEATURES].to_numpy()
        r2 = build_rows(y2, pd.DatetimeIndex([D]), lead, delay, CLIM)[FEATURES].to_numpy()
        np.testing.assert_array_equal(r1, r2)


def test_last_date_and_target_alignment(y):
    r = build_rows(y, pd.DatetimeIndex(["2017-06-10"]), 3, 1, CLIM).iloc[0]
    assert r["last_date"] == pd.Timestamp("2017-06-08")
    assert r["target"] == pd.Timestamp("2017-06-13")
    assert r["last"] == y.loc["2017-06-08"]
    assert r["y"] == y.loc["2017-06-13"]
    assert max(input_obs_dates(y, r["last_date"])) == "2017-06-08"


def test_split_purges_boundary_crossing_rows(y):
    origins = pd.date_range("2016-12-20", "2017-01-10", freq="D")
    r = build_rows(y, origins, 5, 0, CLIM)
    m = in_split(r, pd.Timestamp("2016-01-01"), pd.Timestamp("2016-12-31"))
    assert (r.loc[m, "target"] <= pd.Timestamp("2016-12-31")).all()
    assert r.loc[m, "origin"].max() == pd.Timestamp("2016-12-26")


def test_climatology_uses_training_years_only(y):
    c1 = fit_climatology(y, "2015-01-01", "2016-12-31")
    y2 = y.copy()
    y2[y2.index >= "2017-01-01"] = 99.0
    c2 = fit_climatology(y2, "2015-01-01", "2016-12-31")
    np.testing.assert_array_equal(c1.mean, c2.mean)
    np.testing.assert_array_equal(c1.p90, c2.p90)


def test_air_uses_run_of_origin_day_only():
    rows = pd.DataFrame({"origin": pd.to_datetime(["2024-07-01"]), "last": [20.0]})
    air = pd.DataFrame({k: [30.0 + k, 99.0] for k in range(8)},
                       index=pd.to_datetime(["2024-07-01", "2024-07-02"]))   # later run must be ignored
    out = attach_air(rows, air, 3).iloc[0]
    assert out["air_mean"] == pytest.approx((31 + 32 + 33) / 3)
    assert out["weather_run_init"] == pd.Timestamp("2024-07-01")


def test_air_missing_day_gives_nan():
    rows = pd.DataFrame({"origin": pd.to_datetime(["2024-07-01"]), "last": [20.0]})
    air = pd.DataFrame({k: [30.0] for k in range(8)}, index=pd.to_datetime(["2024-07-01"]))
    air.loc["2024-07-01", 2] = np.nan
    assert np.isnan(attach_air(rows, air, 3).iloc[0]["air_x"])


def test_bootstrap_blocks_do_not_cross_gaps():
    dates = pd.DatetimeIndex(list(pd.date_range("2025-01-01", periods=20)) +
                             list(pd.date_range("2025-03-01", periods=5)))
    for s, ln in _blocks(dates, 14):
        span = dates[s:s + ln]
        assert (np.diff(span.values).astype("timedelta64[D]").astype(int) == 1).all()
    ci = block_bootstrap_ci(dates, np.ones(len(dates)), 14, 200, 1)
    assert ci["lo"] == ci["hi"] == 1.0
