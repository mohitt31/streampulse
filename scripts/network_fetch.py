#!/usr/bin/env python3
"""Network replication downloads (stdlib only, Python 3.8+; run on a machine that can reach
Hub'eau and Open-Meteo). The selection rule is fixed in config/network.toml.

    python3 scripts/network_fetch.py stations          # candidate list  -> data/network/stations.json
    python3 scripts/network_fetch.py water             # Hub'eau history for every candidate
    python3 scripts/network_fetch.py weather           # ECMWF runs for stations in data/network/eligible.json

Resumable: re-running skips files already downloaded (the per-station fetchers keep manifests).
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.path.join(ROOT, "data", "network")
UA = "streampulse/0.1 (hackathon research; github.com/mohitt31/streampulse)"
# kept in sync with config/network.toml (read with a tiny parser: no tomllib on older Pythons)
CFG_PATH = os.path.join(ROOT, "config", "network.toml")


def cfg():
    out, sec = {}, None
    for line in open(CFG_PATH, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            sec = line.strip("[]")
            out[sec] = {}
            continue
        k, v = [x.strip() for x in line.split("=", 1)]
        v = v.strip('"')
        try:
            v = float(v) if "." in v else int(v)
        except ValueError:
            pass
        out[sec][k] = v
    return out


def get_json(url):
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** i)
    raise RuntimeError("failed: %s (%s)" % (url, last))


def stations(c):
    s = c["selection"]
    q = {"latitude": s["center_lat"], "longitude": s["center_lon"], "distance": s["radius_km"],
         "size": 500, "format": "json"}
    url = "https://hubeau.eaufrance.fr/api/v1/temperature/station?" + urllib.parse.urlencode(q)
    js = get_json(url)
    data = js.get("data", [])
    keep = [{k: d.get(k) for k in ("code_station", "libelle_station", "libelle_commune", "code_departement",
                                    "libelle_cours_eau", "latitude", "longitude", "date_maj_infos")} for d in data]
    os.makedirs(NET, exist_ok=True)
    with open(os.path.join(NET, "stations.json"), "w") as f:
        json.dump({"url": url, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "api_count": js.get("count"), "stations": keep}, f, indent=1, ensure_ascii=False)
    print("candidates: %d (api count %s)" % (len(keep), js.get("count")))


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]


def water(workers):
    st = json.load(open(os.path.join(NET, "stations.json")))["stations"]

    def one(s):
        code = s["code_station"]
        rc, tail = run([sys.executable, os.path.join(ROOT, "scripts", "fetch_hubeau.py"), "--station", code,
                        "--root", os.path.join(NET, code)])
        return code, rc, tail[0]

    with cf.ThreadPoolExecutor(workers) as ex:
        for i, (code, rc, tail) in enumerate(ex.map(one, st), 1):
            print("[%d/%d] %s rc=%d %s" % (i, len(st), code, rc, tail), flush=True)


def weather(workers, c):
    el = json.load(open(os.path.join(NET, "eligible.json")))
    cell = float(c["weather"]["share_cell_deg"])
    cells = {}
    for s in el["eligible"]:
        key = "%.2f_%.2f" % (round(s["latitude"] / cell) * cell, round(s["longitude"] / cell) * cell)
        cells.setdefault(key, s)
    print("eligible stations: %d, weather cells: %d" % (len(el["eligible"]), len(cells)), flush=True)

    def one(item):
        key, s = item
        rc, tail = run([sys.executable, os.path.join(ROOT, "scripts", "fetch_single_runs.py"),
                        "--lat", "%.6f" % s["latitude"], "--lon", "%.6f" % s["longitude"],
                        "--root", os.path.join(NET, "_weather", key), "--sleep", "0.4"])
        return key, rc, tail[0]

    with cf.ThreadPoolExecutor(workers) as ex:
        for i, (key, rc, tail) in enumerate(ex.map(one, sorted(cells.items())), 1):
            print("[%d/%d] cell %s rc=%d %s" % (i, len(cells), key, rc, tail), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("steps", nargs="+", choices=["stations", "water", "weather"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    c = cfg()
    for s in a.steps:
        if s == "stations":
            stations(c)
        elif s == "water":
            water(a.workers)
        else:
            weather(a.workers, c)


if __name__ == "__main__":
    main()
