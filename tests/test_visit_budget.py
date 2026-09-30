import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    "visit_budget", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "visit_budget.py")
vb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vb)


def test_policy_visits_top_k_above_line_only():
    rows = [{"m": 2.0, "hit": 1}, {"m": 0.5, "hit": 0}, {"m": -1.0, "hit": 1}, {"m": 1.0, "hit": 1}]
    assert vb.policy(rows, "m", 1) == (1, 1)
    assert vb.policy(rows, "m", 2) == (2, 2)
    # a river below its line is never visited, even when budget remains
    assert vb.policy(rows, "m", 4) == (3, 2)


def test_policy_no_visit_when_nothing_reaches_line():
    assert vb.policy([{"m": -0.1, "hit": 1}], "m", 2) == (0, 0)


def test_day_before():
    assert vb.day_before("2025-03-01") == "2025-02-28"
