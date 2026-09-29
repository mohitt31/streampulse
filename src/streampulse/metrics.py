"""Point, interval and watch metrics + gap-aware moving-block bootstrap."""
from __future__ import annotations

import numpy as np
import pandas as pd


def point(pred, obs, ref_mae: float | None = None) -> dict:
    pred = np.asarray(pred, dtype=float)
    obs = np.asarray(obs, dtype=float)
    e = pred - obs
    out = {"n": int(len(e)), "mae": float(np.mean(np.abs(e))) if len(e) else np.nan,
           "rmse": float(np.sqrt(np.mean(e ** 2))) if len(e) else np.nan,
           "bias": float(np.mean(e)) if len(e) else np.nan}
    if ref_mae is not None and ref_mae and np.isfinite(ref_mae):
        out["skill_vs_persistence"] = 1.0 - out["mae"] / ref_mae
    return out


def interval(lo, hi, obs) -> dict:
    lo, hi, obs = (np.asarray(a, dtype=float) for a in (lo, hi, obs))
    m = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(obs)
    if not m.any():
        return {"n": 0, "coverage": np.nan, "mean_width": np.nan}
    cov = ((obs[m] >= lo[m]) & (obs[m] <= hi[m])).mean()
    return {"n": int(m.sum()), "coverage": float(cov), "mean_width": float(np.mean(hi[m] - lo[m]))}


def contingency(pred_flag, obs_flag) -> dict:
    p = np.asarray(pred_flag, dtype=bool)
    o = np.asarray(obs_flag, dtype=bool)
    tp, fp = int((p & o).sum()), int((p & ~o).sum())
    fn, tn = int((~p & o).sum()), int((~p & ~o).sum())
    div = lambda a, b: float(a / b) if b else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": div(tp, tp + fp), "recall": div(tp, tp + fn),
            "false_alarm_ratio": div(fp, tp + fp), "false_positive_rate": div(fp, fp + tn)}


def count_episodes(dates, flags) -> int:
    """Number of runs of consecutive calendar days with flag True."""
    s = pd.Series(np.asarray(flags, dtype=bool), index=pd.DatetimeIndex(dates)).sort_index()
    s = s[s]
    if s.empty:
        return 0
    gaps = s.index.to_series().diff().dt.days.fillna(99).to_numpy()
    return int((gaps != 1).sum())


def _blocks(dates: pd.DatetimeIndex, block: int) -> list[tuple[int, int]]:
    """All admissible (start, length) blocks that never span a calendar gap."""
    days = dates.to_numpy().astype("datetime64[D]").astype(np.int64)
    breaks = np.flatnonzero(np.diff(days) != 1) + 1
    starts = np.concatenate([[0], breaks])
    ends = np.concatenate([breaks, [len(days)]])
    out: list[tuple[int, int]] = []
    for s, e in zip(starts, ends):
        n = e - s
        if n >= block:
            out.extend((s + i, block) for i in range(n - block + 1))
        elif n > 0:
            out.append((s, n))
    return out


def block_bootstrap_ci(dates, d, block: int, reps: int, seed: int, level: float = 0.95) -> dict:
    order = np.argsort(pd.DatetimeIndex(dates).to_numpy())
    dates = pd.DatetimeIndex(dates)[order]
    d = np.asarray(d, dtype=float)[order]
    n = len(d)
    blocks = _blocks(dates, block)
    rng = np.random.default_rng(seed)
    means = np.empty(reps)
    for r in range(reps):
        parts, tot = [], 0
        while tot < n:
            s, ln = blocks[rng.integers(len(blocks))]
            parts.append(d[s:s + ln])
            tot += ln
        means[r] = np.concatenate(parts)[:n].mean()
    a = (1 - level) / 2
    return {"mean": float(d.mean()), "lo": float(np.quantile(means, a)), "hi": float(np.quantile(means, 1 - a)),
            "block_days": block, "reps": reps, "n": n, "n_blocks_admissible": len(blocks)}
