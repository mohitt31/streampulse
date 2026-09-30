"""Network replication of the frozen single-station method (config/network.toml).

    python -m streampulse.network eligibility   # QC every downloaded candidate, apply the pre-registered rule
    python -m streampulse.network run           # ingest -> validate -> test -> gate for each eligible station
    python -m streampulse.network summary       # reports/network_summary.json (+ web bundle)

Nothing here changes the method: each station reuses config/contract.toml with only [site] replaced.
"""
from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from .config import REPO_ROOT, Paths, load_contract, split, tomllib
from .ingest import load_hubeau_raw
from .quality import build_daily

NET = Path(os.environ.get("STREAMPULSE_NET", REPO_ROOT / "data" / "network"))
OUT = Path(os.environ.get("STREAMPULSE_NET_OUT", REPO_ROOT / "reports"))


def net_cfg() -> dict:
    return tomllib.loads((REPO_ROOT / "config" / "network.toml").read_text(encoding="utf-8"))


def cell_key(lat: float, lon: float, deg: float) -> str:
    return "%.2f_%.2f" % (round(lat / deg) * deg, round(lon / deg) * deg)


def _stations() -> list[dict]:
    return json.loads((NET / "stations.json").read_text())["stations"]


def eligibility() -> dict:
    nc = net_cfg()
    e = nc["eligibility"]
    base = load_contract()
    t0, t1 = split(base, "test")
    out = {"rule": e, "eligible": [], "excluded": []}
    for s in _stations():
        code = s["code_station"]
        root = NET / code
        try:
            readings = load_hubeau_raw(root / "data" / "raw" / "hubeau")
        except FileNotFoundError:
            out["excluded"].append({"code_station": code, "reason": "not downloaded"})
            continue
        if readings.empty:
            out["excluded"].append({"code_station": code, "reason": "no readings 2010-2025"})
            continue
        daily, _, summ = build_daily(readings, base["qc"])
        paths = Paths(root).ensure()
        daily.to_csv(paths.daily_water, index=False, float_format="%.4f")
        d = pd.to_datetime(daily["date"])
        el = daily["eligible"].astype(bool)
        per_year = el.groupby(d.dt.year).sum()
        train_years = int(sum(1 for y, n in per_year.items() if 2010 <= y <= 2022 and n >= e["min_training_year_days"]))
        n23 = int(per_year.get(2023, 0))
        n24 = int(per_year.get(2024, 0))
        n25 = int(el[(d >= t0) & (d <= t1)].sum())
        counts = {"training_years": train_years, "days_2023": n23, "days_2024": n24, "days_2025_test": n25,
                  "eligible_days_total": int(el.sum()), "first_date": summ["first_date"], "last_date": summ["last_date"]}
        reasons = []
        if train_years < e["min_training_years"]:
            reasons.append(f"training years {train_years} < {e['min_training_years']}")
        if n23 < e["min_tune_days_2023"]:
            reasons.append(f"2023 days {n23} < {e['min_tune_days_2023']}")
        if n24 < e["min_validation_days_2024"]:
            reasons.append(f"2024 days {n24} < {e['min_validation_days_2024']}")
        if n25 < e["min_test_days_2025"]:
            reasons.append(f"2025 test days {n25} < {e['min_test_days_2025']}")
        rec = {**s, "counts": counts}
        if reasons:
            out["excluded"].append({"code_station": code, "reason": "; ".join(reasons), "counts": counts})
        else:
            out["eligible"].append(rec)
    (NET / "eligible.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"eligible {len(out['eligible'])} / {len(out['eligible']) + len(out['excluded'])}")
    for x in out["eligible"]:
        print("  +", x["code_station"], x.get("libelle_station"), x["counts"])
    return out


def _site(s: dict) -> dict:
    return {"station_id": s["code_station"], "name": s.get("libelle_station") or s["code_station"],
            "lat": float(s["latitude"]), "lon": float(s["longitude"])}


def station_paths(s: dict, deg: float) -> Paths:
    key = cell_key(float(s["latitude"]), float(s["longitude"]), deg)
    return Paths(NET / s["code_station"], NET / "_weather" / key / "data" / "raw" / "single_runs")


def run(only: list[str] | None = None) -> None:
    from .backtest import run_test, run_validation
    from .gate import run_gate
    from .ingest import run_ingest

    nc = net_cfg()
    el = json.loads((NET / "eligible.json").read_text())["eligible"]
    primary = nc["reporting"]["primary_station"]
    for s in el:
        code = s["code_station"]
        if code == primary or (only and code not in only):
            continue
        cfg = load_contract(site=_site(s))
        paths = station_paths(s, nc["weather"]["share_cell_deg"])
        status = NET / code / "reports" / "run_status.json"
        try:
            if not any(paths.raw_runs.glob("*_00z.json")):
                raise RuntimeError(f"no ECMWF runs in {paths.raw_runs}")
            paths.ensure()
            run_ingest(cfg, paths)
            if not paths.test_lock.exists():
                run_validation(cfg, paths)
            run_test(cfg, paths)
            g = run_gate(cfg, paths)
            status.write_text(json.dumps({"ok": True, "decision": g["decision"]}))
            print(f"{code}: {g['decision']}", flush=True)
        except Exception as exc:  # noqa: BLE001 - record and continue with the next station
            status.parent.mkdir(parents=True, exist_ok=True)
            status.write_text(json.dumps({"ok": False, "error": repr(exc), "trace": traceback.format_exc()[-2000:]}))
            print(f"{code}: FAILED {exc!r}", flush=True)


def _station_result(code: str, root: Path, meta: dict) -> dict:
    rep = root / "reports"
    st = rep / "run_status.json"
    if st.exists() and not json.loads(st.read_text()).get("ok"):
        return {**meta, "status": "failed", "error": json.loads(st.read_text()).get("error")}
    try:
        gate = json.loads((rep / "gate.json").read_text())
        tm = json.loads((rep / "test_metrics.json").read_text())
        fz = json.loads((rep / "frozen_selection.json").read_text())
    except FileNotFoundError:
        return {**meta, "status": "not run"}
    prod = fz["primary"]["product_model"]
    leads = {}
    for h, e in tm["runs"]["primary"]["leads"].items():
        if int(h) > 3:
            continue
        m = e["models"]
        leads[h] = {"n": e["n_paired"], "episodes": e["observed_exceedance_episodes"],
                    "mae": {k: round(v["mae"], 3) for k, v in m.items()},
                    "skill": round(m[prod]["skill_vs_persistence"], 3) if prod in m else None,
                    "watch": m[prod]["watch"] if prod in m else None}
    return {**meta, "status": "ok", "product_model": prod, "weather_selected": fz["primary"]["weather"]["selected_variant"],
            "gate_passed": gate["passed"], "gate": [{"id": c["id"], "passed": c["passed"]} for c in gate["criteria"]],
            "leads": leads, "frozen_sha256": json.loads((rep / "test_lock.json").read_text())["frozen_sha256"]}


def _replay_series(root: Path, prod: str) -> dict:
    """Compact product-model day+1..3 forecasts per issue date, for the network map."""
    p = root / "reports" / "test_predictions.csv"
    if not p.exists():
        return {}
    d = pd.read_csv(p)
    d = d[(d["run"] == "primary") & (d["model_id"] == prod) & (d["lead"] <= 3)]
    out = {}
    for r in d.itertuples(index=False):
        o = out.setdefault(r.origin, [None, None, None])
        o[int(r.lead) - 1] = [round(float(r.pred), 2), round(float(r.p90), 2) if np.isfinite(r.p90) else None,
                              1 if bool(r.watch) else 0, None if not np.isfinite(r.y) else round(float(r.y), 2)]
    return out


def summary() -> dict:
    nc = net_cfg()
    el = json.loads((NET / "eligible.json").read_text())
    primary = nc["reporting"]["primary_station"]
    rows, replay = [], {}
    for s in el["eligible"]:
        code = s["code_station"]
        meta = {"code_station": code, "name": s.get("libelle_station"), "commune": s.get("libelle_commune"),
                "river": s.get("libelle_cours_eau"), "lat": float(s["latitude"]), "lon": float(s["longitude"]),
                "primary": code == primary, "counts": s.get("counts")}
        root = REPO_ROOT if code == primary else NET / code
        r = _station_result(code, root, meta)
        rows.append(r)
        if r["status"] == "ok":
            replay[code] = _replay_series(root, r["product_model"])
    ok = [r for r in rows if r["status"] == "ok"]
    sk = [r["leads"]["3"]["skill"] for r in ok if r["leads"].get("3", {}).get("skill") is not None]
    head = {"candidates": len(el["eligible"]) + len(el["excluded"]), "eligible": len(el["eligible"]),
            "analysed": len(ok), "gate_passed": sum(1 for r in ok if r["gate_passed"]),
            "beats_persistence_day3": sum(1 for x in sk if x > 0),
            "median_skill_day3": round(float(np.median(sk)), 3) if sk else None,
            "skill_day3_range": [round(min(sk), 3), round(max(sk), 3)] if sk else None}
    out = {"preregistration": "config/network.toml", "headline": head, "stations": rows,
           "excluded": el["excluded"], "rule": el["rule"]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "network_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (OUT / "network_replay.json").write_text(json.dumps(replay, separators=(",", ":")))
    print(json.dumps(head, indent=1))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="streampulse.network")
    ap.add_argument("step", choices=["eligibility", "run", "summary"])
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    {"eligibility": eligibility, "summary": summary}.get(a.step, lambda: run(a.only))()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
