"""Thursday go/no-go gate, computed only from frozen selection + test outputs."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import metrics as M
from .config import Paths, split
from .backtest import paired


def _load_run(paths: Paths, run: str) -> pd.DataFrame:
    df = pd.read_csv(paths.reports / "test_predictions.csv")
    df = df[df["run"] == run].copy()
    for c in ("origin", "target"):
        df[c] = pd.to_datetime(df[c])
    return df


def run_gate(cfg: dict, paths: Paths) -> dict:
    g = cfg["gate"]
    frozen = json.loads(paths.frozen.read_text())
    chron = json.loads((paths.reports / "chronology.json").read_text())
    t0, t1 = split(cfg, "test")
    h = int(cfg["timing"]["primary_lead"])
    prod = frozen["primary"]["product_model"]

    P = paired(_load_run(paths, "primary"), h, t0, t1)
    n = len(P)
    summer = P["target"].dt.month.isin([5, 6, 7, 8])
    mae = lambda c, m=slice(None): float(np.mean(np.abs(P.loc[m, c] - P.loc[m, "y"]))) if n else np.nan
    mae_prod, mae_pers, mae_clim = mae(prod), mae("persistence"), mae("climatology")
    s3 = 1 - mae_prod / mae_pers if n else np.nan
    delta = mae_pers - mae_prod
    val_pers = frozen["primary"]["val_persistence_mae"][str(h)]
    delta_min = max(g["min_delta_abs_c"], g["min_delta_rel_to_val_persistence"] * val_pers)
    d = (np.abs(P["persistence"] - P["y"]) - np.abs(P[prod] - P["y"])).to_numpy()
    boot14 = M.block_bootstrap_ci(P.index, d, g["boot_block_days"], g["boot_reps"], g["boot_seed"]) if n else None
    boot28 = M.block_bootstrap_ci(P.index, d, g["boot_block_days_check"], g["boot_reps"], g["boot_seed"]) if n else None

    P1 = paired(_load_run(paths, "delay1"), h, t0, t1)
    prod1 = frozen["delay1"]["product_model"]
    s3_d1 = (1 - np.mean(np.abs(P1[prod1] - P1["y"])) / np.mean(np.abs(P1["persistence"] - P1["y"]))
             if len(P1) else np.nan)

    crit = [
        {"id": 1, "name": f"N paired >= {g['min_paired']} and May-Aug >= {g['min_paired_may_aug']}",
         "value": {"n": n, "n_may_aug": int(summer.sum())},
         "passed": n >= g["min_paired"] and int(summer.sum()) >= g["min_paired_may_aug"]},
        {"id": 2, "name": f"S{h} >= {g['min_skill']:.0%}", "value": s3, "passed": bool(s3 >= g["min_skill"])},
        {"id": 3, "name": f"Delta{h} >= max({g['min_delta_abs_c']} C, {g['min_delta_rel_to_val_persistence']} x "
                          f"2024 persistence MAE) = {delta_min:.3f} C",
         "value": delta, "passed": bool(delta >= delta_min)},
        {"id": 4, "name": "95% moving-block bootstrap lower bound on Delta > 0 (14-day and 28-day blocks)",
         "value": {"b14": boot14, "b28": boot28},
         "passed": bool(boot14 and boot28 and boot14["lo"] > 0 and boot28["lo"] > 0)},
        {"id": 5, "name": "beats climatology overall and persistence in May-Aug",
         "value": {"mae_prod": mae_prod, "mae_clim": mae_clim,
                   "mae_prod_may_aug": mae(prod, summer.to_numpy()),
                   "mae_pers_may_aug": mae("persistence", summer.to_numpy())},
         "passed": bool(mae_prod < mae_clim and mae(prod, summer.to_numpy()) < mae("persistence", summer.to_numpy()))},
        {"id": 6, "name": "chronology assertions pass and 24h-delay sensitivity keeps positive skill",
         "value": {"chronology_passed": chron["passed"], "S_delay1": s3_d1},
         "passed": bool(chron["passed"] and s3_d1 > 0)},
    ]
    passed = all(c["passed"] for c in crit)
    res = {"synthetic": paths.is_synthetic(), "product_model": prod, "primary_lead": h,
           "decision": "GO: Track 6 forecast product" if passed else f"NO-GO: switch to {g['fallback']}",
           "passed": passed, "criteria": crit,
           "mae": {"product": mae_prod, "persistence": mae_pers, "climatology": mae_clim}}
    (paths.reports / "gate.json").write_text(json.dumps(res, indent=1, default=float))
    (paths.reports / "gate.md").write_text(render_md(res))
    return res


def render_md(res: dict) -> str:
    L = []
    if res["synthetic"]:
        L.append("> **SYNTHETIC DATA - pipeline smoke test only. These are NOT results.**\n")
    L.append(f"# Go/no-go gate - lead {res['primary_lead']} - product `{res['product_model']}`\n")
    L.append(f"**Decision: {res['decision']}**\n")
    L.append("| # | criterion | value | pass |\n|---|---|---|---|")
    for c in res["criteria"]:
        v = c["value"]
        if isinstance(v, float):
            v = f"{v:.4f}"
        elif isinstance(v, dict):
            v = ", ".join(f"{k}={_fmt(x)}" for k, x in v.items())
        L.append(f"| {c['id']} | {c['name']} | {v} | {'yes' if c['passed'] else 'NO'} |")
    return "\n".join(L) + "\n"


def _fmt(x):
    if isinstance(x, dict):
        return f"[{x.get('lo', float('nan')):.3f}, {x.get('hi', float('nan')):.3f}]"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)
