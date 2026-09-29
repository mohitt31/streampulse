"""streampulse CLI: synth | ingest | validate | test | gate | all"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import REPO_ROOT, Paths, load_contract


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="streampulse")
    ap.add_argument("command", choices=["synth", "ingest", "validate", "test", "gate", "all"])
    ap.add_argument("--root", default=str(REPO_ROOT), help="project root holding data/ and reports/")
    ap.add_argument("--contract", default=None)
    ap.add_argument("--reopen", action="store_true", help="re-run after the test set was opened (recorded)")
    ap.add_argument("--allow-synthetic-in-repo", action="store_true")
    a = ap.parse_args(argv)

    cfg = load_contract(a.contract)
    paths = Paths(Path(a.root)).ensure()

    if a.command == "synth":
        if Path(a.root).resolve() == REPO_ROOT.resolve() and not a.allow_synthetic_in_repo:
            print("refusing to write synthetic data into the repo root; pass --root /tmp/sp", file=sys.stderr)
            return 2
        from .synth import generate
        print(json.dumps(generate(paths, cfg)))
        return 0

    from .backtest import run_test, run_validation
    from .gate import run_gate
    from .ingest import run_ingest

    steps = ["ingest", "validate", "test", "gate"] if a.command == "all" else [a.command]
    for s in steps:
        if s == "ingest":
            r = run_ingest(cfg, paths)
            print(f"ingest: {r['eligible_days']}/{r['days']} eligible days, {r['first_date']}..{r['last_date']}, "
                  f"runs={r['air_runs']['runs']}")
        elif s == "validate":
            fz = run_validation(cfg, paths, reopen=a.reopen)
            w = fz["primary"]["weather"]
            print(f"validate: alphas={ {h: v['alpha'] for h, v in fz['alpha_selection'].items()} } "
                  f"weather={w['selected_variant']} ({w['reason']}) product={fz['primary']['product_model']}")
        elif s == "test":
            r = run_test(cfg, paths, reopen=a.reopen)
            print(f"test: {r['n_forecasts']} forecasts, {r['n_alerts']} alerts, "
                  f"chronology={'PASS' if r['chronology']['passed'] else 'FAIL'}")
        elif s == "gate":
            r = run_gate(cfg, paths)
            print(("[SYNTHETIC] " if r["synthetic"] else "") + r["decision"])
            for c in r["criteria"]:
                print(f"  {c['id']}. {'PASS' if c['passed'] else 'FAIL'}  {c['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
