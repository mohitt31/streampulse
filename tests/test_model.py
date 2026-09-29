import numpy as np
import pytest

from streampulse.model import Ridge, apply_weather, fit_weather


def test_ridge_small_alpha_matches_ols():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(300, 4))
    t = X @ np.array([1.0, -2.0, 0.5, 0.0]) + 3 + rng.normal(0, 0.01, 300)
    m = Ridge.fit(X, t, 1e-9)
    A = np.column_stack([np.ones(300), X])
    beta, *_ = np.linalg.lstsq(A, t, rcond=None)
    np.testing.assert_allclose(m.predict(X), A @ beta, atol=1e-6)


def test_ridge_matches_sklearn_if_available():
    sk = pytest.importorskip("sklearn.linear_model")
    rng = np.random.default_rng(2)
    X = rng.normal(size=(200, 5)) * [1, 10, 100, 0.1, 1]
    t = rng.normal(size=200)
    mu, sd = X.mean(0), X.std(0)
    ref = sk.Ridge(alpha=10.0).fit((X - mu) / sd, t)
    m = Ridge.fit(X, t, 10.0)
    np.testing.assert_allclose(m.coef, ref.coef_, atol=1e-10)


def test_ridge_roundtrip():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(50, 7))
    m = Ridge.fit(X, rng.normal(size=50), 1.0)
    d = m.to_dict()
    m2 = Ridge.from_dict(d)
    np.testing.assert_allclose(m.predict(X), m2.predict(X))


def test_weather_variants():
    x = np.array([0.0, 1.0, 2.0, 3.0])
    r = 0.5 + 2.0 * x
    assert fit_weather(r, x, "water_only") == (0.0, 0.0)
    a, b = fit_weather(r, x, "intercept_only")
    assert b == 0.0 and a == pytest.approx(r.mean())
    a, b = fit_weather(r, x, "full")
    assert a == pytest.approx(0.5) and b == pytest.approx(2.0)
    # water_only must not propagate NaN weather inputs
    assert np.isfinite(apply_weather([1.0], [np.nan], 0.0, 0.0)).all()
