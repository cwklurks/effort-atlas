#!/bin/sh
# Extend the canonical suite with the actual pinned upstream/SDK lane and a
# 1,000-item synthetic rehearsal. No provider access is possible through Python.
set -eu
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
BASELINE_PYTHON_BIN="${BASELINE_PYTHON_BIN:-.cache/inkling-baseline-env/bin/python}"
REAP_VERIFY_GUARD="$(pwd)/scripts/offline_guard"
REAP_VERIFY_PYTHON="$PYTHON_BIN"
export REAP_VERIFY_GUARD REAP_VERIFY_PYTHON
reap_verify_wrapper=$(mktemp /tmp/reap-baseline-offline.XXXXXX)
trap 'rm -f "$reap_verify_wrapper"' EXIT HUP INT TERM
cat > "$reap_verify_wrapper" <<'WRAPPER'
#!/bin/sh
PYTHONPATH="$REAP_VERIFY_GUARD:${PYTHONPATH:-}" exec "$REAP_VERIFY_PYTHON" "$@"
WRAPPER
chmod 700 "$reap_verify_wrapper"
PYTHON_BIN="$reap_verify_wrapper" ./scripts/verify_offline.sh
REAP_VERIFY_PYTHON="$BASELINE_PYTHON_BIN"
export REAP_VERIFY_PYTHON
PYTHONPATH=src:tests "$reap_verify_wrapper" -m unittest discover -s tests/baseline -v
PYTHONPATH=src "$reap_verify_wrapper" -m effort_atlas.inkling_baseline --mock
