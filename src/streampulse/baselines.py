"""Training-only climatology (mean and watch threshold) and simple baselines."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .features import doy365


@dataclass
class Climatology:
    start: str
    end: str
    window: int
    mean: np.ndarray            # 365 values, index doy-1
    p90: np.ndarray             # 365 values
    n: np.ndarray = field(default_factory=lambda: np.zeros(365, dtype=int))
    quantile: float = 0.9

    def to_dict(self) -> dict:
        r = lambda a: [None if not np.isfinite(x) else round(float(x), 4) for x in a]
        return {"start": self.start, "end": self.end, "window": self.window, "quantile": self.quantile,
                "mean": r(self.mean), "p90": r(self.p90), "n": [int(x) for x in self.n]}

    @classmethod
    def from_dict(cls, d: dict) -> "Climatology":
        f = lambda a: np.array([np.nan if x is None else x for x in a], dtype=float)
        return cls(d["start"], d["end"], d["window"], f(d["mean"]), f(d["p90"]),
                   np.array(d.get("n", [0] * 365)), d.get("quantile", 0.9))

    def mean_for(self, dates) -> np.ndarray:
        return self.mean[doy365(dates) - 1]

    def p90_for(self, dates) -> np.ndarray:
        return self.p90[doy365(dates) - 1]


def fit_climatology(y: pd.Series, start, end, window: int = 15, q: float = 0.9,
                    min_n: int = 20) -> Climatology:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    s = y[(y.index >= start) & (y.index <= end)].dropna()
    d = doy365(s.index)
    v = s.to_numpy(dtype=float)
    mean = np.full(365, np.nan)
    p90 = np.full(365, np.nan)
    n = np.zeros(365, dtype=int)
    for k in range(1, 366):
        dist = np.abs(d - k)
        dist = np.minimum(dist, 365 - dist)
        m = dist <= window
        n[k - 1] = int(m.sum())
        if n[k - 1] >= min_n:
            mean[k - 1] = v[m].mean()
            p90[k - 1] = np.quantile(v[m], q)
    return Climatology(str(start.date()), str(end.date()), window, mean, p90, n, q)
