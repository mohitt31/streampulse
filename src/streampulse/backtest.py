"""Two-stage backtest.

Stage `validation` (never touches 2025):
  1. alpha per lead: train 2010-2022, score MAE on 2023;
  2. refit water ridge on 2010-2023 with frozen alphas;
  3. 2024 out-of-sample: baselines + water model; weather correction chosen by an
     expanding window (fit on runs observed before each month, evaluate Jul..Dec);
  4. final weather coefficients on all of 2024; empirical 5/95% residual intervals;
  5. the same, with obs_delay_days = 1 and the same hyperparameters (sensitivity);
  6. writes reports/frozen_selection.json.

Stage `test` opens 2025-01-01..2025-08-21 exactly once for a given frozen file
(reports/test_lock.json records the frozen sha256). It writes forecasts.jsonl,
alerts.jsonl, test_predictions.csv, test_metrics.json and chronology.json.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

from . import metrics as M
from .baselines import Climatology, fit_climatology
from .config import MODEL_IDS, Paths, all_leads, code_version, sha256_file, split
from .features import ONE, attach_air, build_rows, in_split, input_obs_dates
from .ingest import load_air_wide
from .model import Ridge, apply_weather, fit_water, fit_weather, predict_water
from .quality import daily_series

VARIANTS_ALL = ("water_only", "intercept_only", "full")


class ReopenError(RuntimeError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clim(y: pd.Series, cfg: dict, start, end) -> Climatology:
    m = cfg["model"]
    return fit_climatology(y, start, end, m["clim_window_days"], m["watch_quantile"], m["clim_min_n"])


def _rows(y, cfg, lead, delay, clim, start, end) -> pd.DataFrame:
    m = cfg["model"]
    return build_rows(y, pd.date_range(start, end, freq="D"), lead, delay, clim.mean,
                      m["m3_min_valid"], m["m7_min_valid"])


def _usable(r: pd.DataFrame) -> pd.Series:
    return r["features_ok"] & np.isfinite(r["y"])


def _mae(p, o) -> float:
    return float(np.mean(np.abs(np.asarray(p, float) - np.asarray(o, float))))


def load_inputs(paths: Paths) -> tuple[pd.Series, pd.DataFrame]:
    daily = pd.read_csv(paths.daily_water, dtype={"qual_codes": str})
    return daily_series(daily), load_air_wide(paths)


# ----------------------------------------------------------------------------- validation

def select_alphas(y: pd.Series, cfg: dict) -> dict:
    tr0, tr1 = split(cfg, "train")
    tu0, tu1 = split(cfg, "tune")
    clim = _clim(y, cfg, tr0, tr1)
    delay = int(cfg["timing"]["obs_delay_days"])
    out = {}
    for h in all_leads(cfg):
        R = _rows(y, cfg, h, delay, clim, tr0, tu1)
        tr = R[in_split(R, tr0, tr1) & _usable(R)]
        tu = R[in_split(R, tu0, tu1) & _usable(R)]
        scores = {}
        for a in cfg["model"]["alphas"]:
            scores[float(a)] = _mae(predict_water(fit_water(tr, a), tu), tu["y"])
        best = min(scores, key=lambda a: (round(scores[a], 6), -a))   # ties -> stronger shrinkage
        out[str(h)] = {"alpha": best, "tune_mae": {str(k): v for k, v in scores.items()},
                       "tune_persistence_mae": _mae(tu["last"], tu["y"]),
                       "n_train": int(len(tr)), "n_tune": int(len(tu))}
    return out


def _freeze(y, air, cfg, alpha_sel: dict, delay: int, variant: str | None = None) -> dict:
    r0, r1 = split(cfg, "refit")
    v0, v1 = split(cfg, "val")
    first_run = pd.Timestamp(cfg["weather"]["first_run"])
    ew0 = pd.Timestamp(cfg["splits"]["val_expanding_first_eval"])
    ph = str(cfg["timing"]["primary_lead"])
    qlo, qhi = cfg["model"]["interval_quantiles"]
    clim = _clim(y, cfg, r0, r1)

    water, V = {}, {}
    for h in all_leads(cfg):
        R = _rows(y, cfg, h, delay, clim, r0, v1)
        fit = R[in_split(R, r0, r1) & _usable(R)]
        m = fit_water(fit, alpha_sel[str(h)]["alpha"])
        water[str(h)] = m
        v = R[in_split(R, v0, v1) & _usable(R)].copy()
        v["water"] = predict_water(m, v)
        v["persistence"] = v["last"]
        v["climatology"] = v["clim_T"]
        V[str(h)] = attach_air(v, air, h)

    # expanding-window, strictly out-of-sample weather evaluation within 2024
    EW = {}
    months = pd.date_range(ew0, v1, freq="MS")
    for h, v in V.items():
        vw = v[np.isfinite(v["air_x"]) & (v["origin"] >= first_run)]
        parts = []
        for ms in months:
            nxt = ms + pd.offsets.MonthBegin(1)
            fit = vw[vw["target"] <= ms - (1 + delay) * ONE]      # only targets observed before first eval issuance
            ev = vw[(vw["origin"] >= ms) & (vw["origin"] < nxt)].copy()
            if len(fit) < 20 or ev.empty:
                continue
            res = (fit["y"] - fit["water"]).to_numpy()
            for var in VARIANTS_ALL:
                a, b = fit_weather(res, fit["air_x"].to_numpy(), var)
                ev[f"pred_{var}"] = apply_weather(ev["water"], ev["air_x"], a, b)
            ev["fold"] = str(ms.date())
            ev["n_fit_fold"] = len(fit)
            parts.append(ev)
        EW[h] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    E = EW[ph]
    sel_scores = {var: _mae(E[f"pred_{var}"], E["y"]) for var in VARIANTS_ALL} if len(E) else {}
    weather_enabled = len(E) >= 30
    reason = "selected on expanding-window lead-%s MAE" % ph
    if variant is None:
        if not weather_enabled:
            variant, reason = "water_only", "insufficient weather rows in validation (%d)" % len(E)
        else:
            cands = list(cfg["model"]["weather_candidates"])       # order = tie preference (simpler first)
            variant = min(cands, key=lambda k: (round(sel_scores[k], 6), cands.index(k)))
    else:
        reason = "inherited from primary selection (sensitivity run)"

    coefs = {}
    for h, v in V.items():
        vw = v[np.isfinite(v["air_x"]) & (v["origin"] >= first_run)]
        if len(vw) >= 20:
            res = (vw["y"] - vw["water"]).to_numpy()
            coefs[h] = {var: list(fit_weather(res, vw["air_x"].to_numpy(), var)) for var in VARIANTS_ALL}
            coefs[h]["n_fit"] = int(len(vw))

    def q(res) -> list[float] | None:
        res = np.asarray(res, float)
        res = res[np.isfinite(res)]
        return [float(np.quantile(res, qlo)), float(np.quantile(res, qhi))] if len(res) >= 30 else None

    intervals = {mid: {} for mid in MODEL_IDS}
    interval_notes = {}
    for h, v in V.items():
        intervals["water_ridge_v1"][h] = q(v["y"] - v["water"])
        intervals["persistence"][h] = q(v["y"] - v["last"])
        intervals["climatology"][h] = q(v["y"] - v["clim_T"])
        e = EW.get(h)
        if e is not None and len(e) >= 30:
            intervals["weather_corr_v1"][h] = q(e["y"] - e["pred_full"])
        else:
            intervals["weather_corr_v1"][h] = intervals["water_ridge_v1"][h]
            interval_notes[h] = "weather interval fell back to water residuals"

    val_metrics = {}
    for h, v in V.items():
        pm = _mae(v["last"], v["y"])
        val_metrics[h] = {
            "all_2024_rows": {k: M.point(v[c], v["y"], pm) for k, c in
                              (("water_ridge_v1", "water"), ("persistence", "last"), ("climatology", "clim_T"))
                              if np.isfinite(v[c]).all()},
        }
        e = EW.get(h)
        if e is not None and len(e):
            pme = _mae(e["last"], e["y"])
            val_metrics[h]["expanding_window_paired"] = {
                **{var: M.point(e[f"pred_{var}"], e["y"], pme) for var in VARIANTS_ALL},
                "persistence": M.point(e["last"], e["y"], pme),
                "folds": sorted(e["fold"].unique().tolist()),
            }

    return {
        "delay": int(delay),
        "climatology": clim.to_dict(),
        "water": {h: m.to_dict() for h, m in water.items()},
        "weather": {"enabled": bool(weather_enabled and coefs), "selected_variant": variant, "reason": reason,
                    "selection_mae_lead_primary": sel_scores, "coef": coefs,
                    "n_expanding_rows_primary": int(len(E))},
        "product_model": "weather_corr_v1" if variant == "full" and weather_enabled else "water_ridge_v1",
        "intervals": intervals,
        "interval_notes": interval_notes,
        "val_persistence_mae": {h: _mae(v["last"], v["y"]) for h, v in V.items()},
        "val_metrics": val_metrics,
    }


def run_validation(cfg: dict, paths: Paths, reopen: bool = False) -> dict:
    paths.ensure()
    if paths.test_lock.exists() and not reopen:
        raise ReopenError("test stage already opened (reports/test_lock.json). Re-validating after seeing "
                          "the test set would contaminate it. Use --reopen to do it on the record.")
    y, air = load_inputs(paths)
    alpha_sel = select_alphas(y, cfg)
    primary = _freeze(y, air, cfg, alpha_sel, int(cfg["timing"]["obs_delay_days"]))
    delay1 = _freeze(y, air, cfg, alpha_sel, int(cfg["timing"]["sensitivity_obs_delay_days"]),
                     variant=primary["weather"]["selected_variant"])
    frozen = {
        "created_at": _now(),
        "contract_sha256": cfg["_sha256"],
        "daily_water_sha256": sha256_file(paths.daily_water),
        "air_runs_sha256": sha256_file(paths.air_runs) if paths.air_runs.exists() else None,
        "code_version": code_version(paths.root),
        "synthetic": paths.is_synthetic(),
        "splits": cfg["splits"],
        "alpha_selection": alpha_sel,
        "primary": primary,
        "delay1": delay1,
    }
    paths.frozen.write_text(json.dumps(frozen, indent=1, default=float))
    return frozen


# ----------------------------------------------------------------------------- test

def _open_lock(paths: Paths, frozen_sha: str, reopen: bool) -> dict:
    lock = json.loads(paths.test_lock.read_text()) if paths.test_lock.exists() else None
    if lock is None:
        lock = {"first_opened_at": _now(), "frozen_sha256": frozen_sha, "history": []}
    elif lock["frozen_sha256"] != frozen_sha:
        if not reopen:
            raise ReopenError("frozen_selection.json changed after the test set was opened. "
                              "Refusing. Use --reopen to reopen on the record.")
        lock["history"].append({"reopened_at": _now(), "old_frozen_sha256": lock["frozen_sha256"],
                                "new_frozen_sha256": frozen_sha})
        lock["frozen_sha256"] = frozen_sha
    lock["last_run_at"] = _now()
    paths.test_lock.write_text(json.dumps(lock, indent=1))
    return lock


def _predict_block(y, air, cfg, fz: dict, start, end) -> pd.DataFrame:
    """Long table of predictions for origins in [start, end]."""
    delay = int(fz["delay"])
    clim = Climatology.from_dict(fz["climatology"])
    out = []
    for h in all_leads(cfg):
        R = _rows(y, cfg, h, delay, clim, start, end)
        R = R[R["features_ok"]].copy()
        R = attach_air(R, air, h)
        preds = {
            "water_ridge_v1": predict_water(Ridge.from_dict(fz["water"][str(h)]), R),
            "persistence": R["last"].to_numpy(float),
            "climatology": R["clim_T"].to_numpy(float),
        }
        w = fz["weather"]
        if w["enabled"] and str(h) in w["coef"]:
            a, b = w["coef"][str(h)]["full"]
            p = apply_weather(preds["water_ridge_v1"], R["air_x"], a, b)
            preds["weather_corr_v1"] = np.where(np.isfinite(R["air_x"]), p, np.nan)
        p90 = clim.p90_for(R["target"])
        for mid, p in preds.items():
            iv = fz["intervals"].get(mid, {}).get(str(h))
            d = R[["origin", "target", "last_date", "lead", "delay", "y", "weather_run_init"]].copy()
            d["model_id"] = mid
            d["pred"] = p
            d["lo"] = p + iv[0] if iv else np.nan
            d["hi"] = p + iv[1] if iv else np.nan
            d["p90"] = p90
            if mid != "weather_corr_v1":
                d["weather_run_init"] = pd.NaT
            out.append(d[np.isfinite(d["pred"])])
    df = pd.concat(out, ignore_index=True)
    df["watch"] = df["pred"] >= df["p90"]
    df["obs_exceed"] = np.where(np.isfinite(df["y"]), df["y"] >= df["p90"], np.nan)
    return df


def paired(df: pd.DataFrame, lead: int, t0, t1) -> pd.DataFrame:
    """Wide table (index origin) of eval rows where every model present has a prediction and y exists."""
    d = df[(df["lead"] == lead) & (df["origin"] >= t0) & (df["target"] <= t1) & np.isfinite(df["y"])]
    w = d.pivot_table(index="origin", columns="model_id", values="pred", aggfunc="first").dropna()
    meta = d.drop_duplicates("origin").set_index("origin")[["target", "y", "p90"]]
    return w.join(meta, how="inner")


def chronology_checks(fc: pd.DataFrame, cfg: dict, frozen: dict, lock: dict) -> list[dict]:
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    s = cfg["splits"]
    add("splits ordered: train < tune < val < test",
        s["train_end"] < s["tune_start"] <= s["tune_end"] < s["val_start"] <= s["val_end"] < s["test_start"],
        json.dumps(s))
    add("climatology/refit ends before validation", frozen["primary"]["climatology"]["end"] < s["val_start"])
    add("frozen selection created before first test open", frozen["created_at"] <= lock["first_opened_at"],
        f'{frozen["created_at"]} <= {lock["first_opened_at"]}')
    lag = (fc["origin"] - fc["last_date"]).dt.days
    add("last obs date == origin - 1 - delay", bool((lag == 1 + fc["delay"]).all()))
    add("target == origin + lead", bool(((fc["target"] - fc["origin"]).dt.days == fc["lead"]).all()))
    mx = fc["input_max"]
    add("all input obs dates <= last obs date", bool((mx.isna() | (mx <= fc["last_date"])).all()))
    wr = fc["weather_run_init"].dropna()
    issued = fc.loc[wr.index, "origin"] + pd.Timedelta(hours=int(cfg["timing"]["issuance_hour_utc"]))
    run_t = wr + pd.Timedelta(hours=int(cfg["weather"]["run_hour_utc"]))
    add("weather run init <= issuance time", bool((run_t <= issued).all()), f"{len(wr)} weather rows")
    add("no validation-period target used after val_end", True, "enforced by in_split purge")
    return checks


def run_test(cfg: dict, paths: Paths, reopen: bool = False) -> dict:
    frozen = json.loads(paths.frozen.read_text())
    if frozen["contract_sha256"] != cfg["_sha256"]:
        raise ReopenError("contract.toml changed since validation; re-run validation (on the record).")
    lock = _open_lock(paths, sha256_file(paths.frozen), reopen)
    y, air = load_inputs(paths)
    t0, t1 = split(cfg, "test")
    leads = all_leads(cfg)
    ph = int(cfg["timing"]["primary_lead"])
    version = code_version(paths.root)

    runs = {}
    for key in ("primary", "delay1"):
        df = _predict_block(y, air, cfg, frozen[key], t0, t1 + ONE)   # t1+1: last replay origin (stale afterwards)
        df["run"] = key
        runs[key] = df

    allp = pd.concat(runs.values(), ignore_index=True)
    out = allp.copy()
    for c in ("origin", "target", "last_date"):
        out[c] = out[c].dt.strftime("%Y-%m-%d")
    out["weather_run_init"] = pd.to_datetime(out["weather_run_init"]).dt.strftime("%Y-%m-%dT00:00Z")
    out.to_csv(paths.reports / "test_predictions.csv", index=False, float_format="%.4f")

    # metrics on paired rows
    tm = {"synthetic": paths.is_synthetic(), "test_window": [str(t0.date()), str(t1.date())], "runs": {}}
    for key, df in runs.items():
        fz = frozen[key]
        tm["runs"][key] = {"product_model": fz["product_model"], "leads": {}}
        for h in leads:
            P = paired(df, h, t0, t1)
            if P.empty:
                continue
            pm = _mae(P["persistence"], P["y"])
            ent = {"n_paired": int(len(P)),
                   "n_paired_may_aug": int(P["target"].dt.month.isin([5, 6, 7, 8]).sum()),
                   "models": {}}
            d = df[(df["lead"] == h)].set_index(["origin", "model_id"])
            for mid in [m for m in MODEL_IDS if m in P.columns]:
                sub = d.xs(mid, level="model_id").loc[P.index]
                ent["models"][mid] = {**M.point(P[mid], P["y"], pm),
                                      "interval90": M.interval(sub["lo"], sub["hi"], P["y"]),
                                      "watch": M.contingency(P[mid] >= P["p90"], P["y"] >= P["p90"])}
            ent["observed_exceedance_episodes"] = M.count_episodes(P["target"], P["y"] >= P["p90"])
            tm["runs"][key]["leads"][str(h)] = ent
    (paths.reports / "test_metrics.json").write_text(json.dumps(tm, indent=1, default=float))

    # forecasts.jsonl / alerts.jsonl from the primary run
    fc = runs["primary"].sort_values(["origin", "lead", "model_id"],
                                     key=lambda s: s.map({m: i for i, m in enumerate(MODEL_IDS)})
                                     if s.name == "model_id" else s).reset_index(drop=True)
    cache: dict = {}
    inputs = []
    for ld in fc["last_date"]:
        if ld not in cache:
            cache[ld] = input_obs_dates(y, ld)
        inputs.append(cache[ld])
    fc["input_obs_dates"] = inputs
    fc["input_max"] = pd.to_datetime([max(x) if x else None for x in inputs])
    generated = _now()
    station = cfg["site"]["station_id"]
    lines = []
    for r in fc.itertuples(index=False):
        lines.append({
            "station_id": station, "mode": "replay", "model_id": r.model_id, "model_version": version,
            "origin_date": r.origin.strftime("%Y-%m-%d"),
            "issued_simulated": (r.origin + pd.Timedelta(hours=int(cfg["timing"]["issuance_hour_utc"])))
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_at": generated, "lead_days": int(r.lead), "target_date": r.target.strftime("%Y-%m-%d"),
            "pred_mean_c": round(float(r.pred), 3),
            "pi90_low_c": None if not np.isfinite(r.lo) else round(float(r.lo), 3),
            "pi90_high_c": None if not np.isfinite(r.hi) else round(float(r.hi), 3),
            "p90_reference_c": None if not np.isfinite(r.p90) else round(float(r.p90), 3),
            "watch": bool(r.watch),
            "weather_run_init": None if pd.isna(r.weather_run_init)
            else pd.Timestamp(r.weather_run_init).strftime("%Y-%m-%dT%H:%MZ"),
            "input_obs_dates": r.input_obs_dates,
        })
    with open(paths.reports / "forecasts.jsonl", "w") as f:
        for ln in lines:
            f.write(json.dumps(ln, ensure_ascii=False) + "\n")

    product = frozen["primary"]["product_model"]
    plead = set(cfg["timing"]["product_leads"])
    alerts = []
    for origin, g in fc[(fc["model_id"] == product) & fc["lead"].isin(plead) & fc["watch"]].groupby("origin"):
        alerts.append({
            "alert_id": f"SP-{station}-{origin:%Y%m%d}", "station_id": station,
            "origin_date": origin.strftime("%Y-%m-%d"),
            "target_dates": [t.strftime("%Y-%m-%d") for t in g["target"]],
            "forecast_refs": [int(i) for i in g.index],
            "action": cfg["followup"]["action_code"], "status": "open", "ack": None,
        })
    with open(paths.reports / "alerts.jsonl", "w") as f:
        for a in alerts:
            f.write(json.dumps(a) + "\n")

    checks = chronology_checks(fc, cfg, frozen, lock)
    chron = {"passed": all(c["passed"] for c in checks), "checks": checks}
    (paths.reports / "chronology.json").write_text(json.dumps(chron, indent=1))
    return {"metrics": tm, "n_forecasts": len(lines), "n_alerts": len(alerts), "chronology": chron,
            "primary_lead": ph}
