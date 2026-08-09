#!/usr/bin/env python3
"""Render the self-contained REAP phase-status page from its JSON source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = ROOT / "reap" / "status"
SOURCE = STATUS_DIR / "phase_status.json"
TEMPLATE = STATUS_DIR / "template.html"
OUTPUT = STATUS_DIR / "index.html"
MARKER = "__REAP_STATUS_JSON__"


def validate_status(data: dict) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("phase status schema_version must be 1")
    phases = data.get("phases")
    if not isinstance(phases, list) or [phase.get("id") for phase in phases] != list(range(8)):
        raise ValueError("phases must contain ordered ids 0 through 7")
    active = [phase for phase in phases if phase.get("status") == "in_progress"]
    if len(active) > 1:
        raise ValueError("at most one phase may be in_progress")
    if data.get("project", {}).get("current_phase") not in range(8):
        raise ValueError("project.current_phase must be an id from 0 through 7")
    for phase in phases:
        progress = phase.get("progress")
        if not isinstance(progress, int) or not 0 <= progress <= 100:
            raise ValueError(f"phase {phase.get('id')} progress must be an integer from 0 to 100")


def render(source: Path = SOURCE, template: Path = TEMPLATE) -> str:
    data = json.loads(source.read_text(encoding="utf-8"))
    validate_status(data)
    template_text = template.read_text(encoding="utf-8")
    if template_text.count(MARKER) != 1:
        raise ValueError(f"template must contain exactly one {MARKER} marker")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return template_text.replace(MARKER, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if index.html is stale")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("reap/status/index.html is stale; run scripts/render_phase_status.py")
        print("phase status HTML is current")
        return
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
