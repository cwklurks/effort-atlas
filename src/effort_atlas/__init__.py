"""effort-atlas: per-domain effort/performance curves for Inkling."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path is not None else ROOT / "config.yaml"
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    with cfg_path.open() as fh:
        return yaml.safe_load(fh)
