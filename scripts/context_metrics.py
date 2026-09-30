#!/usr/bin/env python3
"""EXPLORATORY, POST-HOC: warm-day error and an external ecological threshold, primary site.

Not pre-registered. Reads only the frozen primary-site 2025 test predictions
(reports/test_predictions.csv); nothing is fitted, tuned or re-run.

1. Error on warm days. Studies of short-term stream-temperature forecasts report that
   models can lose to persistence on the warmest days (Zwart et al. 2023, Frontiers in Water,
   doi:10.3389/frwa.2023.1184992: persistence better above 18 °C in the Delaware River Basin).
   We split the same paired rows by observed temperature above 18 °C and 20 °C.
   Splitting on the observed value is a descriptive stratification, not a forecast-conditioned test.

2. An externally defined threshold. For the Garonne, Larnier et al. (2010, Knowl. Managt.
   Aquatic Ecosyst. 398:04, doi:10.1051/kmae/2010031) cite 24 °C as the upper limit for
   Atlantic salmon migration, above which most recorded Garonne salmon mortalities occurred.
   We count 2025 target days observed at or above 24 °C and how often each method's point
   forecast reached 24 °C on those days and on days that stayed below.

    python3 scripts/context_metrics.py  -> reports/exploratory/context.json
"""
import csv
import datetime as dt
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD, PERS = "weather_corr_v1", "persistence"
SALMON_C = 24.0


def main():
    rows = {}
    with open(os.path.join(ROOT, "reports", "test_predictions.csv")) as f:
        for r in csv.DictReader(f):
            if r["run"] != "primary" or not r["y"] or int(r["lead"]) > 3:
                continue
            k = (int(r["lead"]), r["origin"])
            rows.setdefault(k, {"y": float(r["y"]), "target": r["target"]})[r["model_id"]] = float(r["pred"])
    paired = [v | {"lead": k[0]} for k, v in rows.items() if PROD in v and PERS in v]

    def err(sub, m):
        n = len(sub)
        return {"mae": round(sum(abs(r[m] - r["y"]) for r in sub) / n, 3),
                "rmse": round(math.sqrt(sum((r[m] - r["y"]) ** 2 for r in sub) / n), 3)} if n else None

    out = {"label": "EXPLORATORY, POST-HOC, NOT PRE-REGISTERED",
           "note": "Frozen primary-site 2025 test predictions only; no fitting or tuning. Warm-day strata split on the observed value.",
           "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "salmon_threshold_c": SALMON_C,
           "references": {
               "zwart2023": "Zwart et al. 2023, Frontiers in Water, doi:10.3389/frwa.2023.1184992",
               "larnier2010": "Larnier et al. 2010, Knowl. Managt. Aquatic Ecosyst. 398:04, doi:10.1051/kmae/2010031"},
           "leads": {}}
    for h in (1, 2, 3):
        L = [r for r in paired if r["lead"] == h]
        strata = {}
        for name, cond in (("all", lambda r: True), ("above_18", lambda r: r["y"] > 18), ("above_20", lambda r: r["y"] > 20)):
            s = [r for r in L if cond(r)]
            strata[name] = {"n": len(s), PROD: err(s, PROD), PERS: err(s, PERS)}
        hot = [r for r in L if r["y"] >= SALMON_C]
        cool = [r for r in L if r["y"] < SALMON_C]
        det = {m: {"reached_on_hot_days": sum(r[m] >= SALMON_C for r in hot),
                   "reached_on_cooler_days": sum(r[m] >= SALMON_C for r in cool)} for m in (PROD, PERS)}
        out["leads"][str(h)] = {"strata": strata, "salmon": {"hot_days": len(hot), "cooler_days": len(cool), **det}}

    p = os.path.join(ROOT, "reports", "exploratory", "context.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    for h, r in out["leads"].items():
        s = r["strata"]
        print(f"lead {h}: >18 n={s['above_18']['n']} MAE {s['above_18'][PROD]['mae']} vs {s['above_18'][PERS]['mae']}; "
              f">=24 days {r['salmon']['hot_days']}: sp {r['salmon'][PROD]} pers {r['salmon'][PERS]}")
    print("wrote", p)


if __name__ == "__main__":
    main()
