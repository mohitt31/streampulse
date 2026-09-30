#!/usr/bin/env python3
"""Network replication downloads (stdlib only, Python 3.8+; run on a machine that can reach
Hub'eau and Open-Meteo). The selection rule is fixed in config/network.toml.

    python3 scripts/network_fetch.py stations          # candidate list  -> data/network/stations.json
    python3 scripts/network_fetch.py prescreen         # 2025 test-window reading count per candidate (1 request each)
    python3 scripts/network_fetch.py water             # Hub'eau history for candidates that can still meet the rule
    python3 scripts/network_fetch.py weather           # ECMWF runs for stations to analyse (stage 1 + stage 2)
    python3 scripts/network_fetch.py --stage 2 stations prescreen water   # stage 2 (config/network_stage2.toml)

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
SUFFIX = ""   # "" for stage 1, "_s2" for stage 2 (set in main)


def f(name):
    base, ext = os.path.splitext(name)
    return os.path.join(NET, base + SUFFIX + ext)


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


def check_network():
    import socket
    for host in ("hubeau.eaufrance.fr", "single-runs-api.open-meteo.com"):
        try:
            socket.getaddrinfo(host, 443)
        except OSError as e:
            sys.exit("Cannot resolve %s (%s). Your internet/DNS is down: check Wi-Fi, then retry." % (host, e))


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
    excluded_prev = 0
    if SUFFIX:  # stage 2: drop stage-1 candidates (already assessed)
        prev = {x["code_station"] for x in json.load(open(os.path.join(NET, "stations.json")))["stations"]}
        excluded_prev = sum(1 for x in keep if x["code_station"] in prev)
        keep = [x for x in keep if x["code_station"] not in prev]
    os.makedirs(NET, exist_ok=True)
    with open(f("stations.json"), "w") as fh:
        json.dump({"url": url, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "api_count": js.get("count"), "excluded_stage1": excluded_prev, "stations": keep},
                  fh, indent=1, ensure_ascii=False)
    print("candidates: %d (api count %s, %d stage-1 candidates excluded)" % (len(keep), js.get("count"), excluded_prev))


def prescreen(c, workers):
    """One cheap request per candidate: hourly readings in the 2025 test window. A station needs at least
    min_test_days_2025 eligible days, and an eligible day needs >= 18 readings, so fewer than 18 x min_test_days
    readings means the pre-registered rule already excludes it; its full history is not downloaded."""
    st = json.load(open(f("stations.json")))["stations"]
    need = 18 * int(c["eligibility"]["min_test_days_2025"])

    def one(s):
        q = {"code_station": s["code_station"], "date_debut_mesure": "2025-01-01", "date_fin_mesure": "2025-08-21",
             "size": 1, "fields": "code_station"}
        try:
            js = get_json("https://hubeau.eaufrance.fr/api/v1/temperature/chronique?" + urllib.parse.urlencode(q))
            return s["code_station"], int(js.get("count") or 0), None
        except Exception as e:  # noqa: BLE001 - keep going, re-run later
            return s["code_station"], None, str(e)[-160:]

    old = {}
    pre = f("prescreen.json")
    if os.path.exists(pre):
        old = json.load(open(pre)).get("stations", {})
    todo = [s for s in st if old.get(s["code_station"], {}).get("readings_2025_test") is None]
    res = {k: v for k, v in old.items() if v.get("readings_2025_test") is not None}
    with cf.ThreadPoolExecutor(workers) as ex:
        for code, n, err in ex.map(one, todo):
            res[code] = {"readings_2025_test": n, "pass": None if n is None else n >= need}
            if err:
                res[code]["error"] = err
                print("  %s: request failed (%s)" % (code, err), flush=True)
    json.dump({"threshold_readings": need, "stations": res}, open(f("prescreen.json"), "w"), indent=1)
    failed = sum(1 for v in res.values() if v["pass"] is None)
    print("prescreen: %d of %d candidates can still meet the 2025 rule (>= %d readings); %d requests failed%s"
          % (sum(1 for v in res.values() if v["pass"]), len(res), need, failed,
             " -> run 'prescreen' again" if failed else ""))


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]


def water(workers):
    st = json.load(open(f("stations.json")))["stations"]
    pre = f("prescreen.json")
    if os.path.exists(pre):
        ok = {k for k, v in json.load(open(pre))["stations"].items() if v["pass"]}
        st = [s for s in st if s["code_station"] in ok]
        print("downloading full history for %d prescreened stations" % len(st), flush=True)

    def one(s):
        code = s["code_station"]
        rc, tail = run([sys.executable, os.path.join(ROOT, "scripts", "fetch_hubeau.py"), "--station", code,
                        "--root", os.path.join(NET, code)])
        return code, rc, tail[0]

    with cf.ThreadPoolExecutor(workers) as ex:
        for i, (code, rc, tail) in enumerate(ex.map(one, st), 1):
            print("[%d/%d] %s rc=%d %s" % (i, len(st), code, rc, tail), flush=True)


def weather(workers, c):
    """Weather for every station to be analysed: stage-1 eligible + stage-2 sampled (whichever files exist)."""
    todo = []
    for name in ("eligible.json", "eligible_s2.json"):
        p = os.path.join(NET, name)
        if os.path.exists(p):
            todo += [s for s in json.load(open(p))["eligible"] if s.get("sampled", True)
                     and s["code_station"] != str(c["reporting"].get("primary_station", ""))]  # primary already has its runs
    el = {"eligible": todo}
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
    ap.add_argument("steps", nargs="+", choices=["stations", "prescreen", "water", "weather"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--stage", type=int, choices=[1, 2], default=1)
    a = ap.parse_args()
    global CFG_PATH, SUFFIX
    if a.stage == 2:
        CFG_PATH = os.path.join(ROOT, "config", "network_stage2.toml")
        SUFFIX = "_s2"
    c = cfg()
    check_network()
    for s in a.steps:
        if s == "stations":
            stations(c)
        elif s == "prescreen":
            prescreen(c, a.workers)
        elif s == "water":
            water(a.workers)
        else:
            weather(a.workers, c)


if __name__ == "__main__":
    main()
