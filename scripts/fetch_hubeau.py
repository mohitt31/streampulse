#!/usr/bin/env python3
"""Fetch Hub'eau water-temperature history for one station, one file per year.

Stdlib only (runs on any Python >= 3.8). Resumable: years already on disk with a
matching sha256 in the manifest are skipped unless --refresh is given.

Usage:
    python3 scripts/fetch_hubeau.py                       # 2010..2025, station 05174000
    python3 scripts/fetch_hubeau.py --years 2024 2025 --refresh
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://hubeau.eaufrance.fr/api/v1/temperature"
FIELDS = ",".join([
    "code_station", "date_mesure_temp", "heure_mesure_temp", "resultat",
    "code_qualification", "code_unite", "symbole_unite",
])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "streampulse/0.1 (hackathon research; github.com/mohitt31/streampulse)"


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_json(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status not in (200, 206):
                    raise RuntimeError("HTTP %s" % r.status)
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, RuntimeError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(2 ** i)
    raise RuntimeError("failed after %d tries: %s (%s)" % (tries, url, last))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"source": "hubeau temperature chronique", "entries": {}}


def save_manifest(path, man):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def fetch_year(station, year, size):
    q = {
        "code_station": station,
        "date_debut_mesure": "%d-01-01" % year,
        "date_fin_mesure": "%d-12-31" % year,
        "size": str(size),
        "fields": FIELDS,
        "sort": "asc",
    }
    url = BASE + "/chronique?" + urllib.parse.urlencode(q)
    urls, data, count = [], [], None
    while url:
        urls.append(url)
        js = get_json(url)
        count = js.get("count", count)
        data.extend(js.get("data", []))
        url = js.get("next")
        time.sleep(0.3)
    return urls, data, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--station", default="05174000")
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2010, 2026)))
    ap.add_argument("--size", type=int, default=20000)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    raw_dir = os.path.join(a.root, "data", "raw", "hubeau")
    man_path = os.path.join(a.root, "data", "manifests", "hubeau.json")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(os.path.dirname(man_path), exist_ok=True)
    man = load_manifest(man_path)

    meta_url = BASE + "/station?" + urllib.parse.urlencode({"code_station": a.station, "size": "1"})
    meta = get_json(meta_url)
    meta_path = os.path.join(raw_dir, "station_%s.json" % a.station)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    man["station_meta"] = {"url": meta_url, "retrieved_at": now(), "sha256": sha256_file(meta_path)}
    save_manifest(man_path, man)

    for y in a.years:
        path = os.path.join(raw_dir, "chronique_%s_%d.json" % (a.station, y))
        key = str(y)
        ent = man["entries"].get(key)
        if not a.refresh and ent and os.path.exists(path) and sha256_file(path) == ent.get("sha256"):
            print("skip %d (%s rows, cached)" % (y, ent.get("rows")))
            continue
        urls, data, count = fetch_year(a.station, y, a.size)
        if count is not None and count != len(data):
            print("WARNING %d: API count=%s but got %d rows" % (y, count, len(data)), file=sys.stderr)
        payload = {"station": a.station, "year": y, "urls": urls, "api_count": count, "data": data}
        with open(path, "w") as f:
            json.dump(payload, f, ensure_ascii=False)
        man["entries"][key] = {
            "url": urls[0], "pages": len(urls), "retrieved_at": now(),
            "sha256": sha256_file(path), "rows": len(data), "api_count": count,
            "path": os.path.relpath(path, a.root),
        }
        save_manifest(man_path, man)
        print("year %d: %d rows" % (y, len(data)))


if __name__ == "__main__":
    main()
