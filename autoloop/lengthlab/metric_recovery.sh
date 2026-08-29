#!/usr/bin/env bash
# Loop A metric. Prints one float (lower is better). No network, no args.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 score_recovery.py
