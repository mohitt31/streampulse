"""Network replication plumbing on synthetic data: eligibility rule, per-station frozen runs, summary."""
import importlib
import json

import pytest


@pytest.fixture(scope="module")
def net(tmp_path_factory, monkeypatch_module=None):
    import os
    root = tmp_path_factory.mktemp("net")
    os.environ["STREAMPULSE_NET"] = str(root / "network")
    os.environ["STREAMPULSE_NET_OUT"] = str(root / "out")
    import streampulse.network as N
    N = importlib.reload(N)
    from streampulse.config import Paths, load_contract
    from streampulse.synth import generate
    stations = [
        {"code_station": "99000001", "libelle_station": "Synthetic A", "latitude": 43.60, "longitude": 1.40},
        {"code_station": "99000002", "libelle_station": "Synthetic B (too short)", "latitude": 43.70, "longitude": 1.50},
    ]
    (N.NET).mkdir(parents=True)
    (N.NET / "stations.json").write_text(json.dumps({"stations": stations}))
    deg = N.net_cfg()["weather"]["share_cell_deg"]
    for i, s in enumerate(stations):
        cfg = load_contract(site=N._site(s))
        p = N.station_paths(s, deg)
        p.raw_runs.mkdir(parents=True, exist_ok=True)
        generate(Paths(p.root, p.raw_runs).ensure(), cfg, seed=11 + i, start="2010-01-01" if i == 0 else "2023-06-01")
    el = N.eligibility()
    N.run()
    summ = N.summary()
    yield N, el, summ
    os.environ.pop("STREAMPULSE_NET"); os.environ.pop("STREAMPULSE_NET_OUT")


def test_eligibility_rule_applied(net):
    _, el, _ = net
    assert [s["code_station"] for s in el["eligible"]] == ["99000001"]
    ex = {x["code_station"]: x["reason"] for x in el["excluded"]}
    assert "training years" in ex["99000002"]


def test_station_gets_own_contract_and_lock(net):
    N, _, summ = net
    st = summ["stations"][0]
    assert st["status"] == "ok", st
    fz = json.loads((N.NET / "99000001" / "reports" / "frozen_selection.json").read_text())
    from streampulse.config import load_contract
    assert fz["contract_sha256"] != load_contract()["_sha256"]          # site folded into the hash
    assert (N.NET / "99000001" / "reports" / "test_lock.json").exists()
    assert summ["headline"]["analysed"] == 1 and "3" in st["leads"]
