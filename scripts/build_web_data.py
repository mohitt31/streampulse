#!/usr/bin/env python3
"""Pack pipeline outputs into one compact JSON for the static replay dashboard.

Reads only files the pipeline already wrote (reports/*.json[l], data/processed/*.csv);
it computes nothing new about skill, so the web numbers are the report numbers.

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
                      "models": {m: {"mae": r3(v["mae"]), "rmse": r3(v["rmse"]), "bias": r3(v["bias"]),
                                     "skill": r3(v.get("skill_vs_persistence")),
                                     "coverage": r3(v["interval90"]["coverage"]),
                                     "width": r3(v["interval90"]["mean_width"]), "watch": v["watch"]}
                                 for m, v in e["models"].items()}}
    d1 = tm["runs"]["delay1"]["leads"].get(ph, {}).get("models", {})

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
                       "mae": {k: r3(v["mae"]) for k, v in ew.items() if isinstance(v, dict)},
                       "selected": p["weather"]["selected_variant"],
                       "coef": p["weather"]["coef"].get(ph, {}).get("full")},
        "delay1": {m: {"mae": r3(v["mae"]), "skill": r3(v.get("skill_vs_persistence"))} for m, v in d1.items()},
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
            out["fhir"] = json.load(f)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"wrote {a.out}: {os.path.getsize(a.out) / 1e6:.2f} MB, {len(origins)} origins, {len(alerts)} alerts")


if __name__ == "__main__":
    main()
