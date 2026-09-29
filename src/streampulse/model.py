"""Direct per-lead ridge on water history + linear weather correction.

Ridge: standardise X with training mean/sd only, centre the target, solve
(Z'Z + alpha I) b = Z'(t - mean t). Equivalent to sklearn Ridge on standardised X,
but dependency-free and exactly serialisable (the web replay can re-run it).

Water model predicts t = y_T - last, so y_hat = last + ridge(X).
Weather correction on top of the frozen water model:
    y_hat_w = y_hat_water + a_h + b_h * (mean forecast air over D+1..D+h - last)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import FEATURES


@dataclass
class Ridge:
    alpha: float
    mu: np.ndarray
    sd: np.ndarray
    coef: np.ndarray
    intercept: float
    n_fit: int = 0

    @classmethod
    def fit(cls, X: np.ndarray, t: np.ndarray, alpha: float) -> "Ridge":
        X = np.asarray(X, dtype=float)
        t = np.asarray(t, dtype=float)
        if len(t) < X.shape[1] + 2:
            raise ValueError(f"too few rows to fit ridge: {len(t)}")
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd[sd == 0] = 1.0
        Z = (X - mu) / sd
        tm = t.mean()
        A = Z.T @ Z + float(alpha) * np.eye(Z.shape[1])
        coef = np.linalg.solve(A, Z.T @ (t - tm))
        return cls(float(alpha), mu, sd, coef, float(tm), int(len(t)))

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (np.asarray(X, dtype=float) - self.mu) / self.sd
        return Z @ self.coef + self.intercept

    def to_dict(self) -> dict:
        return {"alpha": self.alpha, "features": FEATURES, "mu": self.mu.tolist(), "sd": self.sd.tolist(),
                "coef": self.coef.tolist(), "intercept": self.intercept, "n_fit": self.n_fit,
                "target": "y_T - last"}

    @classmethod
    def from_dict(cls, d: dict) -> "Ridge":
        if list(d["features"]) != FEATURES:
            raise ValueError("frozen feature list differs from code FEATURES")
        return cls(d["alpha"], np.array(d["mu"]), np.array(d["sd"]), np.array(d["coef"]),
                   d["intercept"], d.get("n_fit", 0))


def X_of(rows: pd.DataFrame) -> np.ndarray:
    return rows[FEATURES].to_numpy(dtype=float)


def fit_water(rows: pd.DataFrame, alpha: float) -> Ridge:
    return Ridge.fit(X_of(rows), (rows["y"] - rows["last"]).to_numpy(), alpha)


def predict_water(model: Ridge, rows: pd.DataFrame) -> np.ndarray:
    return rows["last"].to_numpy(dtype=float) + model.predict(X_of(rows))


def fit_weather(resid: np.ndarray, x: np.ndarray, variant: str) -> tuple[float, float]:
    """Return (a, b) for residual r = y - y_water."""
    resid = np.asarray(resid, dtype=float)
    x = np.asarray(x, dtype=float)
    if variant == "water_only":
        return 0.0, 0.0
    if variant == "intercept_only":
        return float(resid.mean()), 0.0
    if variant == "full":
        A = np.column_stack([np.ones_like(x), x])
        (a, b), *_ = np.linalg.lstsq(A, resid, rcond=None)
        return float(a), float(b)
    raise ValueError(variant)


def apply_weather(y_water: np.ndarray, x: np.ndarray, a: float, b: float) -> np.ndarray:
    y = np.asarray(y_water, dtype=float) + a
    if b != 0.0:
        y = y + b * np.asarray(x, dtype=float)
    return y
