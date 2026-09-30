#!/usr/bin/env python3
"""EXPLORATORY, POST-HOC: fixed field-visit budget comparison across the network.

Not pre-registered. Uses only forecasts already written by the frozen per-station runs
(reports/network_replay.json) and each station's committed daily means. Nothing is fitted,
tuned or re-run; the 2025 test is not reopened.

Question: a team can make K visits per day across the eligible stations. Each morning it
ranks stations by "forecast minus that station's seasonal 90th-percentile watch line" for a
given lead, and visits the top K whose forecast reaches the line. How many visits land on a
day that actually exceeded the line, compared with ranking the same way using persistence
(yesterday's observation)?

Only issue dates where every station has a forecast, a persistence value and an observed
target are scored, so both rankings face the same days and stations.

    python3 scripts/visit_budget.py   -> reports/exploratory/visit_budget.json
"""
import csv
import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGETS = (1, 2)
LEADS = (1, 2, 3)


def daily(code):
    for p in (os.path.join(ROOT, "data", "network", code, "data", "processed", "daily_water.csv"),
              os.path.join(ROOT, "data", "processed", "daily_water.csv")):
        if os.path.exists(p):
            out = {}
            with open(p) as f:
                for r in csv.DictReader(f):
                    if r["eligible"].strip().lower() in ("true", "1") and r["mean_c"]:
                        out[r["date"]] = float(r["mean_c"])
            return out
    raise FileNotFoundError(code)


def day_before(d):
    return (dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat()


def policy(rows, key, k):
    """rows: per-station dicts for one day. Visit top-k by margin among those with margin >= 0."""
    cand = sorted((r for r in rows if r[key] >= 0), key=lambda r: -r[key])[:k]
    return len(cand), sum(r["hit"] for r in cand)


def main():
    rep = json.load(open(os.path.join(ROOT, "reports", "network_replay.json")))
    summ = json.load(open(os.path.join(ROOT, "reports", "network_summary.json")))
    names = {s["code_station"]: s["name"] for s in summ["stations"]}
    codes = sorted(rep)
    obs = {c: daily(c) for c in codes}
    origins = sorted(set.intersection(*(set(rep[c]) for c in codes)))

    out = {"label": "EXPLORATORY, POST-HOC, NOT PRE-REGISTERED",
           "note": "Uses frozen per-station 2025 forecasts only; no fitting, tuning or test reopening. "
                   "Daily outcomes are serially correlated and the network has few stations: treat as descriptive.",
           "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stations": [{"code": c, "name": names.get(c)} for c in codes],
           "rule": "Each day, rank stations by (forecast - seasonal p90) and visit the top K with margin >= 0. "
                   "Persistence ranks by (yesterday's observation - p90 at the target date). A hit is a visit whose "
                   "target day was observed at or above p90.",
           "leads": {}}
    for h in LEADS:
        days = []
        for o in origins:
            rows = []
            for c in codes:
                cell = rep[c][o][h - 1] if rep[c].get(o) else None
                last = obs[c].get(day_before(o))
                if not cell or cell[1] is None or cell[3] is None or last is None:
                    rows = None
                    break
                pred, p90, _, y = cell
                rows.append({"code": c, "m_model": pred - p90, "m_pers": last - p90, "hit": int(y >= p90)})
            if rows:
                days.append((o, rows))
        n_exc = sum(r["hit"] for _, rows in days for r in rows)
        res = {"paired_days": len(days), "station_days": len(days) * len(codes),
               "exceedance_station_days": n_exc,
               "days_with_any_exceedance": sum(any(r["hit"] for r in rows) for _, rows in days),
               "budgets": {}}
        for k in BUDGETS:
            b = {}
            for name, key in (("streampulse", "m_model"), ("persistence", "m_pers")):
                v = hits = 0
                for _, rows in days:
                    a, t = policy(rows, key, k)
                    v += a
                    hits += t
                b[name] = {"visits": v, "hits": hits, "wasted": v - hits,
                           "hit_rate": round(hits / v, 3) if v else None,
                           "share_of_exceedances_visited": round(hits / n_exc, 3) if n_exc else None}
            res["budgets"][str(k)] = b
        out["leads"][str(h)] = res

    os.makedirs(os.path.join(ROOT, "reports", "exploratory"), exist_ok=True)
    p = os.path.join(ROOT, "reports", "exploratory", "visit_budget.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    for h, r in out["leads"].items():
        print(f"lead {h}: {r['paired_days']} days, {r['exceedance_station_days']} exceedance station-days")
        for k, b in r["budgets"].items():
            print(f"  K={k}", {m: (x["visits"], x["hits"], x["hit_rate"], x["share_of_exceedances_visited"])
                              for m, x in b.items()})
    print("wrote", p)


if __name__ == "__main__":
    main()
