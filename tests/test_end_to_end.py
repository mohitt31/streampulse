"""Synthetic end-to-end run: raw files -> gate. Checks contracts, not skill."""
import json

import pytest

from streampulse.backtest import ReopenError, run_test, run_validation
from streampulse.config import Paths, load_contract
from streampulse.gate import run_gate
from streampulse.ingest import run_ingest
from streampulse.synth import generate

FORECAST_KEYS = {"station_id", "mode", "model_id", "model_version", "origin_date", "issued_simulated",
                 "generated_at", "lead_days", "target_date", "pred_mean_c", "pi90_low_c", "pi90_high_c",
                 "p90_reference_c", "watch", "weather_run_init", "input_obs_dates"}
ALERT_KEYS = {"alert_id", "station_id", "origin_date", "target_dates", "forecast_refs", "action", "status", "ack"}
DAILY_COLS = "date,mean_c,n_hours,n_quarters,qual_codes,eligible"


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    root = tmp_path_factory.mktemp("sp")
    cfg = load_contract()
    paths = Paths(root).ensure()
    generate(paths, cfg)
    run_ingest(cfg, paths)
    run_validation(cfg, paths)
    run_test(cfg, paths)
    gate = run_gate(cfg, paths)
    return cfg, paths, gate


def test_daily_contract(pipeline):
    _, paths, _ = pipeline
    assert paths.daily_water.read_text().splitlines()[0] == DAILY_COLS


def test_forecasts_contract(pipeline):
    cfg, paths, _ = pipeline
    lines = [json.loads(x) for x in paths.reports.joinpath("forecasts.jsonl").read_text().splitlines()]
    assert lines
    models = set()
    for ln in lines:
        assert set(ln) == FORECAST_KEYS
        assert ln["mode"] == "replay"
        assert ln["issued_simulated"].endswith("T12:00:00Z")
        models.add(ln["model_id"])
        o = ln["origin_date"]
        assert all(d < o for d in ln["input_obs_dates"])
        if ln["model_id"] == "weather_corr_v1":
            assert ln["weather_run_init"].startswith(o)
        else:
            assert ln["weather_run_init"] is None
    assert models == {"water_ridge_v1", "weather_corr_v1", "persistence", "climatology"}


def test_alerts_reference_watch_forecasts(pipeline):
    cfg, paths, _ = pipeline
    fc = paths.reports.joinpath("forecasts.jsonl").read_text().splitlines()
    for raw in paths.reports.joinpath("alerts.jsonl").read_text().splitlines():
        a = json.loads(raw)
        assert set(a) == ALERT_KEYS and a["status"] == "open" and a["ack"] is None
        for i in a["forecast_refs"]:
            f = json.loads(fc[i])
            assert f["watch"] and f["origin_date"] == a["origin_date"] and f["lead_days"] <= 3


def test_chronology_and_gate_shape(pipeline):
    _, paths, gate = pipeline
    chron = json.loads(paths.reports.joinpath("chronology.json").read_text())
    assert chron["passed"], chron
    assert [c["id"] for c in gate["criteria"]] == [1, 2, 3, 4, 5, 6]
    assert gate["synthetic"] is True
    assert "SYNTHETIC" in paths.reports.joinpath("gate.md").read_text()


def test_cannot_revalidate_after_test_opened(pipeline):
    cfg, paths, _ = pipeline
    with pytest.raises(ReopenError):
        run_validation(cfg, paths)


def test_changed_frozen_file_refuses_test(pipeline):
    cfg, paths, _ = pipeline
    fz = json.loads(paths.frozen.read_text())
    fz["created_at"] = "tampered"
    paths.frozen.write_text(json.dumps(fz))
    with pytest.raises(ReopenError):
        run_test(cfg, paths)
