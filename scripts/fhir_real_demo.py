#!/usr/bin/env python3
"""Export a validator-sized FHIR Bundle from the REAL pipeline outputs.

The full replay (6,489 forecasts, 52 alerts) exports fine (~56 MB, ~13k resources) but is
too large to commit or to validate in CI on every push. This script selects whole issue
dates from reports/forecasts.jsonl (all models, all leads), keeps their alerts with
forecast_refs re-indexed, optionally records one clearly labelled demo acknowledgement,
and calls the unchanged exporter.

    PYTHONPATH=src python3 scripts/fhir_real_demo.py                      # 2025-06-20 + demo ack
    PYTHONPATH=src python3 scripts/fhir_real_demo.py --origins 2025-05-31 2025-06-20 --no-ack
    PYTHONPATH=src python3 -m streampulse.fhir_export --output /tmp/full.json   # everything
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from streampulse.fhir_export import export

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origins", nargs="+", default=["2025-06-20"])
    ap.add_argument("--no-ack", action="store_true", help="leave alerts open")
    ap.add_argument("--out-dir", default=str(ROOT / "reports" / "fhir"))
    a = ap.parse_args()

    fc = [json.loads(x) for x in (ROOT / "reports" / "forecasts.jsonl").read_text().splitlines() if x.strip()]
    al = [json.loads(x) for x in (ROOT / "reports" / "alerts.jsonl").read_text().splitlines() if x.strip()]
    keep = set(a.origins)
    old_to_new, sub = {}, []
    for i, f in enumerate(fc):
        if f["origin_date"] in keep:
            old_to_new[i] = len(sub)
            sub.append(f)
    missing = keep - {f["origin_date"] for f in sub}
    if missing:
        raise SystemExit(f"no forecasts for origins: {sorted(missing)}")

    alerts = []
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    for x in al:
        if x["origin_date"] not in keep:
            continue
        x = dict(x, forecast_refs=[old_to_new[j] for j in x["forecast_refs"]])
        if not a.no_ack and not alerts:
            x["status"] = "acknowledged"
            x["ack"] = {"by": "Demo field technician", "at": now,
                        "note": "Demo acknowledgement recorded for the FHIR export; no sampling was performed."}
        alerts.append(x)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fpath, apath = out / "demo_forecasts.jsonl", out / "demo_alerts.jsonl"
    fpath.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in sub))
    apath.write_text("".join(json.dumps(x) + "\n" for x in alerts))
    bundle = export(ROOT / "data/processed/daily_water.csv", fpath, apath,
                    ROOT / "data/reference/station_05174000.json", out / "bundle.json")
    kinds = {}
    for e in bundle["entry"]:
        t = e["resource"]["resourceType"]
        kinds[t] = kinds.get(t, 0) + 1
    print(f"origins {sorted(keep)}: {len(sub)} forecasts, {len(alerts)} alerts -> {out / 'bundle.json'} {kinds}")


if __name__ == "__main__":
    main()
