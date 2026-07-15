"""effort-atlas: per-domain effort/performance curves for Inkling."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or ROOT / "config.yaml"
    with cfg_path.open() as fh:
        return yaml.safe_load(fh)
