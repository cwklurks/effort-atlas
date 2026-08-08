#!/bin/sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"$PYTHON_BIN" -c 'import sys; required = (3, 10); current = sys.version_info[:2]; sys.exit(f"Python {current[0]}.{current[1]} is unsupported; require >=3.10") if current < required else None'
mkdir -p .cache/matplotlib
MPLCONFIGDIR=.cache/matplotlib PYTHONPATH=src \
  "$PYTHON_BIN" -m unittest discover -s tests -v
