#!/bin/sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"$PYTHON_BIN" -c 'import sys; required = (3, 10); current = sys.version_info[:2]; sys.exit(f"Python {current[0]}.{current[1]} is unsupported; require >=3.10") if current < required else None'
"$PYTHON_BIN" scripts/render_phase_status.py --check
# capabilities/ source-item JSONLs: validate when present (four of five are
# gitignored reacquirables; regenerate with capabilities/acquire.py). Never silent.
if [ -f capabilities/mmlu_pro.jsonl ] && [ -f capabilities/omni_math.jsonl ] \
   && [ -f capabilities/ifeval.jsonl ] && [ -f capabilities/wildbench_v2.jsonl ]; then
  "$PYTHON_BIN" capabilities/validate.py
else
  echo "capabilities/validate.py SKIPPED: reacquirable JSONLs absent (run: $PYTHON_BIN capabilities/acquire.py)"
fi
mkdir -p .cache/matplotlib
MPLCONFIGDIR=.cache/matplotlib PYTHONPATH=src \
  "$PYTHON_BIN" -m unittest discover -s tests -v
