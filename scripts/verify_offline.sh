#!/bin/sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
TINKER_PYTHON="${TINKER_PYTHON:-.venv/tinker-probe/bin/python}"

"$PYTHON_BIN" -c 'import sys; required = (3, 10); current = sys.version_info[:2]; sys.exit(f"Python {current[0]}.{current[1]} is unsupported; require >=3.10") if current < required else None'
"$PYTHON_BIN" scripts/render_phase_status.py --check
mkdir -p .cache/matplotlib
MPLCONFIGDIR=.cache/matplotlib PYTHONPATH=src \
  "$PYTHON_BIN" -m unittest discover -s tests -p 'test_*.py' -v

if [ ! -x "$TINKER_PYTHON" ]; then
  echo "exact-lock Tinker interpreter is missing or not executable: $TINKER_PYTHON" >&2
  echo "provision it with the commands documented in README.md" >&2
  exit 1
fi

project_prefix_real=$("$PYTHON_BIN" -c 'import os, sys; print(os.path.realpath(sys.prefix))')
tinker_prefix_real=$("$TINKER_PYTHON" -c 'import os, sys; print(os.path.realpath(sys.prefix))')
if [ "$project_prefix_real" = "$tinker_prefix_real" ]; then
  echo "project and Tinker interpreters must be distinct" >&2
  exit 1
fi

"$TINKER_PYTHON" -m unittest discover -s tests -p 'tinker_probe_suite.py' -v
