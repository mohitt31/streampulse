#!/usr/bin/env python3
"""Fetch archived ECMWF IFS 00Z runs (Open-Meteo Single Runs API) for the site.

One request per run date D (run = D 00:00 UTC). Each file holds the run's hourly
temperature_2m for D..D+7 in GMT. These are archived operational forecasts, so
using run D at issuance D 12:00 UTC does not leak future information.

Stdlib only. Resumable; missing runs are recorded in the manifest as status=missing.

Usage:
    python3 scripts/fetch_single_runs.py                        # 2024-03-14 .. 2025-08-22
    python3 scripts/fetch_single_runs.py --start 2025-07-01 --end 2025-07-05
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://single-runs-api.open-meteo.com/v1/forecast"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "streampulse/0.1 (hackathon research; github.com/mohitt31/streampulse)"


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (400, 404):
                return e.code, {"error": True, "reason": body}
            last = "HTTP %s %s" % (e.code, body)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = str(e)
        time.sleep(2 ** i + 1)
    return None, {"error": True, "reason": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=43.512148)
    ap.add_argument("--lon", type=float, default=1.387766)
    ap.add_argument("--model", default="ecmwf_ifs")
    ap.add_argument("--start", default="2024-03-14")
    ap.add_argument("--end", default="2025-08-22")
    ap.add_argument("--forecast-days", type=int, default=8)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    raw_dir = os.path.join(a.root, "data", "raw", "single_runs")
    man_path = os.path.join(a.root, "data", "manifests", "single_runs.json")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(os.path.dirname(man_path), exist_ok=True)
    man = {"source": "open-meteo single runs", "model": a.model, "entries": {}}
    if os.path.exists(man_path):
        with open(man_path) as f:
            man = json.load(f)

    d = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end)
    n_ok = n_miss = 0
    while d <= end:
        key = d.isoformat()
        path = os.path.join(raw_dir, "%s_%s_00z.json" % (a.model, key))
        ent = man["entries"].get(key)
        if not a.refresh and ent and ent.get("status") == "ok" and os.path.exists(path) \
                and sha256_file(path) == ent.get("sha256"):
            d += dt.timedelta(days=1)
            n_ok += 1
            continue
        q = {
            "latitude": "%.6f" % a.lat, "longitude": "%.6f" % a.lon,
            "hourly": "temperature_2m", "models": a.model,
            "run": key + "T00:00", "forecast_days": str(a.forecast_days), "timezone": "GMT",
        }
        url = ENDPOINT + "?" + urllib.parse.urlencode(q)
        status, js = fetch(url)
        ok = status == 200 and "hourly" in js and len(js["hourly"].get("time", [])) > 0
        if ok:
            with open(path, "w") as f:
                json.dump(js, f)
            vals = js["hourly"].get("temperature_2m", [])
            man["entries"][key] = {
                "url": url, "retrieved_at": now(), "status": "ok", "sha256": sha256_file(path),
                "rows": len(vals), "non_null": sum(v is not None for v in vals),
                "path": os.path.relpath(path, a.root),
            }
            n_ok += 1
        else:
            man["entries"][key] = {"url": url, "retrieved_at": now(), "status": "missing",
                                   "http": status, "reason": str(js.get("reason"))[:300]}
            n_miss += 1
            print("missing run %s: http=%s %s" % (key, status, str(js.get("reason"))[:120]))
        with open(man_path + ".tmp", "w") as f:
            json.dump(man, f, indent=1, sort_keys=True)
        os.replace(man_path + ".tmp", man_path)
        time.sleep(a.sleep)
        d += dt.timedelta(days=1)
    print("runs ok=%d missing=%d" % (n_ok, n_miss))


if __name__ == "__main__":
    main()
