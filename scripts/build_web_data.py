#!/usr/bin/env python3
"""Pack pipeline outputs into one compact JSON for the static replay dashboard.

Reads only files the pipeline already wrote (reports/*, data/processed/*.csv). The only
thing computed here is a by-month breakdown of the primary-lead errors, on the same
paired rows (all four models present) that the pipeline scores.

    python3 scripts/build_web_data.py            -> web/public/data/replay.json
"""
import argparse
import csv
import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = ["weather_corr_v1", "water_ridge_v1", "persistence", "climatology"]


def rd(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)


def rjsonl(p):
    with open(os.path.join(ROOT, p)) as f:
        return [json.loads(x) for x in f if x.strip()]


def r3(x):
    return None if x is None else round(float(x), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "web", "public", "data", "replay.json"))
    a = ap.parse_args()

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    with open(os.path.join(ROOT, "config", "contract.toml"), "rb") as f:
        contract = tomllib.load(f)

    frozen = rd("reports/frozen_selection.json")
    tm = rd("reports/test_metrics.json")
    gate = rd("reports/gate.json")
    chron = rd("reports/chronology.json")
    qc = rd("reports/qc_summary.json")
    lock = rd("reports/test_lock.json")
    fc = rjsonl("reports/forecasts.jsonl")
    alerts = rjsonl("reports/alerts.jsonl")

    # observations: eligible daily means, full history
    obs_dates, obs_vals = [], []
    with open(os.path.join(ROOT, "data/processed/daily_water.csv")) as f:
        for row in csv.DictReader(f):
            obs_dates.append(row["date"])
            ok = row["eligible"].strip().lower() in ("true", "1")
            obs_vals.append(r3(row["mean_c"]) if ok and row["mean_c"] else None)
    obs_start = obs_dates[0]

    origins = sorted({x["origin_date"] for x in fc})
    oidx = {o: i for i, o in enumerate(origins)}
    leads = sorted({x["lead_days"] for x in fc})
    # forecasts[model][origin_i][lead-1] = [pred, lo, hi, watch] | null
    F = {m: [[None] * len(leads) for _ in origins] for m in MODELS}
    meta = [{"inputs": [], "run": None} for _ in origins]
    for x in fc:
        i = oidx[x["origin_date"]]
        F[x["model_id"]][i][x["lead_days"] - 1] = [r3(x["pred_mean_c"]), r3(x["pi90_low_c"]), r3(x["pi90_high_c"]),
                                                   1 if x["watch"] else 0]
        meta[i]["inputs"] = x["input_obs_dates"]
        if x["weather_run_init"]:
            meta[i]["run"] = x["weather_run_init"]
    model_version = fc[0]["model_version"] if fc else None

    ph = str(contract["timing"]["primary_lead"])
    p = frozen["primary"]
    ew = p["val_metrics"][ph].get("expanding_window_paired", {})
    runs = tm["runs"]["primary"]["leads"]
    metrics = {}
    for h, e in runs.items():
        metrics[h] = {"n": e["n_paired"], "n_may_aug": e["n_paired_may_aug"],
                      "episodes": e["observed_exceedance_episodes"],
                      "models": {m: {"mae": v["mae"], "rmse": v["rmse"], "bias": v["bias"],
                                     "skill": v.get("skill_vs_persistence"),
                                     "coverage": r3(v["interval90"]["coverage"]),
                                     "width": r3(v["interval90"]["mean_width"]), "watch": v["watch"]}
                                 for m, v in e["models"].items()}}
    d1 = tm["runs"]["delay1"]["leads"].get(ph, {}).get("models", {})

    # by-month day-3 breakdown on paired rows (every model present, observation present)
    rows = {}
    with open(os.path.join(ROOT, "reports", "test_predictions.csv")) as f:
        for r in csv.DictReader(f):
            if r["run"] != "primary" or r["lead"] != ph or not r["y"]:
                continue
            rows.setdefault(r["origin"], {"target": r["target"], "y": float(r["y"])})[r["model_id"]] = float(r["pred"])
    by_month = {}
    for o, r in rows.items():
        if not all(m in r for m in MODELS):
            continue
        mth = r["target"][:7]
        b = by_month.setdefault(mth, {"n": 0, "prod": 0.0, "pers": 0.0})
        b["n"] += 1
        b["prod"] += abs(r[p["product_model"]] - r["y"])
        b["pers"] += abs(r["persistence"] - r["y"])
    monthly = [{"month": k, "n": b["n"], "mae": r3(b["prod"] / b["n"]), "mae_persistence": r3(b["pers"] / b["n"]),
                "skill": r3(1 - b["prod"] / b["pers"])} for k, b in sorted(by_month.items())]

    out = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthetic": bool(tm.get("synthetic")),
        "site": {"id": contract["site"]["station_id"], "name": "Garonne upstream of the Ariège confluence",
                 "commune": "Portet-sur-Garonne (near Toulouse), France",
                 "lat": contract["site"]["lat"], "lon": contract["site"]["lon"],
                 "framing": contract["site"]["framing"]},
        "timing": {"issuance_hour_utc": contract["timing"]["issuance_hour_utc"],
                   "product_leads": contract["timing"]["product_leads"],
                   "exploratory_leads": contract["timing"]["exploratory_leads"],
                   "primary_lead": int(ph)},
        "followup": contract["followup"],
        "product_model": p["product_model"],
        "model_version": model_version,
        "hashes": {"contract": frozen["contract_sha256"], "frozen": lock["frozen_sha256"],
                   "daily_water": frozen["daily_water_sha256"]},
        "frozen_at": frozen["created_at"], "test_opened_at": lock["first_opened_at"],
        "obs": {"start": obs_start, "values": obs_vals},
        "clim": {"mean": p["climatology"]["mean"], "p90": p["climatology"]["p90"],
                 "period": [p["climatology"]["start"], p["climatology"]["end"]]},
        "origins": origins, "leads": leads, "forecasts": F, "meta": meta,
        "alerts": alerts,
        "metrics": metrics,
        "validation": {"lead": int(ph), "rows": p["weather"]["n_expanding_rows_primary"],
                       "folds": ew.get("folds", []),
                       "mae": {k: v["mae"] for k, v in ew.items() if isinstance(v, dict)},
                       "selected": p["weather"]["selected_variant"],
                       "coef": p["weather"]["coef"].get(ph, {}).get("full")},
        "monthly": monthly,
        "delay1": {m: {"mae": r3(v["mae"]), "skill": v.get("skill_vs_persistence")} for m, v in d1.items()},
        "gate": gate, "chronology": chron,
        "qc": {"per_year": qc["per_year"], "dropped": qc["dropped"],
               "conflicting_duplicates_quarantined": qc["conflicting_duplicates_quarantined"],
               "eligible_days": qc["eligible_days"], "days": qc["days"],
               "first_date": qc["first_date"], "last_date": qc["last_date"],
               "air_runs": qc["air_runs"]},
        "fhir": None,
    }
    fhir_summary = os.path.join(ROOT, "reports", "fhir-validation", "summary.json")
    if os.path.exists(fhir_summary):
        with open(fhir_summary) as f:
            fs = json.load(f)
        pos = fs.get("positive", {}).get("counts", {})
        negs = {k: v for k, v in fs.items() if isinstance(v, dict) and v.get("expected_failure")}
        out["fhir"] = {
            "validator": fs.get("validator"), "fhir": fs.get("fhir"),
            "errors": pos.get("error", 0) + pos.get("fatal", 0), "warnings": pos.get("warning", 0),
            "information": pos.get("information", 0), "positive_documents": fs.get("positive_documents"),
            "negative_controls": {k: v.get("counts", {}).get("error", 0) for k, v in negs.items()},
            "generated_at": fs.get("generated_at"),
        }
    ctx = os.path.join(ROOT, "reports", "exploratory", "context.json")
    out["context"] = None
    if os.path.exists(ctx):
        with open(ctx) as f:
            c = json.load(f)
        out["context"] = {k: c[k] for k in ("label", "note", "salmon_threshold_c", "references", "leads")}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    # network replication (optional): written as a separate file, loaded by the Network tab
    ns = os.path.join(ROOT, "reports", "network_summary.json")
    nr = os.path.join(ROOT, "reports", "network_replay.json")
    out["network"] = None
    if os.path.exists(ns) and os.path.exists(nr):
        with open(ns) as f:
            summ = json.load(f)
        with open(nr) as f:
            rep = json.load(f)
        slim = []
        for st in summ["stations"]:
            st = dict(st)
            st.pop("frozen_sha256", None)
            slim.append(st)
        net = {"headline": summ["headline"], "rule": summ["rule"], "stations": slim,
               "excluded": summ["excluded"], "origins": origins,
               "replay": {code: [series.get(o) for o in origins] for code, series in rep.items()},
               "budget": None}
        vb = os.path.join(ROOT, "reports", "exploratory", "visit_budget.json")
        if os.path.exists(vb):
            with open(vb) as f:
                b = json.load(f)
            net["budget"] = {k: b[k] for k in ("label", "note", "rule", "leads")}
        with open(os.path.join(os.path.dirname(a.out), "network.json"), "w") as f:
            json.dump(net, f, separators=(",", ":"))
        out["network"] = {"headline": summ["headline"], "file": "network.json"}

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"wrote {a.out}: {os.path.getsize(a.out) / 1e6:.2f} MB, {len(origins)} origins, {len(alerts)} alerts")


if __name__ == "__main__":
    main()
