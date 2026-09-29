"""Contract loading and repository paths."""
from __future__ import annotations

import hashlib
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = REPO_ROOT / "config" / "contract.toml"

MODEL_IDS = ("water_ridge_v1", "weather_corr_v1", "persistence", "climatology")


def load_contract(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_CONTRACT
    raw = p.read_bytes()
    cfg = tomllib.loads(raw.decode("utf-8"))
    cfg["_sha256"] = hashlib.sha256(raw).hexdigest()
    cfg["_path"] = str(p)
    return cfg


def all_leads(cfg: dict) -> list[int]:
    t = cfg["timing"]
    return sorted(set(t["product_leads"]) | set(t["exploratory_leads"]))


def split(cfg: dict, name: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    s = cfg["splits"]
    return pd.Timestamp(s[f"{name}_start"]), pd.Timestamp(s[f"{name}_end"])


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_version(root: Path | None = None) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=root or REPO_ROOT,
                             capture_output=True, text=True, timeout=5)
        sha = out.stdout.strip()
        if not sha:
            return "nogit"
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                               cwd=root or REPO_ROOT, capture_output=True, text=True, timeout=5)
        return sha + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        return "nogit"


@dataclass(frozen=True)
class Paths:
    root: Path = REPO_ROOT

    @property
    def raw_hubeau(self) -> Path:
        return self.root / "data" / "raw" / "hubeau"

    @property
    def raw_runs(self) -> Path:
        return self.root / "data" / "raw" / "single_runs"

    @property
    def processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def manifests(self) -> Path:
        return self.root / "data" / "manifests"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def daily_water(self) -> Path:
        return self.processed / "daily_water.csv"

    @property
    def air_runs(self) -> Path:
        return self.processed / "air_runs_daily.csv"

    @property
    def frozen(self) -> Path:
        return self.reports / "frozen_selection.json"

    @property
    def test_lock(self) -> Path:
        return self.reports / "test_lock.json"

    @property
    def synthetic_marker(self) -> Path:
        return self.root / "data" / "raw" / "SYNTHETIC"

    def is_synthetic(self) -> bool:
        return self.synthetic_marker.exists()

    def ensure(self) -> "Paths":
        for p in (self.raw_hubeau, self.raw_runs, self.processed, self.manifests, self.reports):
            p.mkdir(parents=True, exist_ok=True)
        return self
