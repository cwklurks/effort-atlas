#!/usr/bin/env bash
# Loop B metric. Prints one float (higher is better). No network, no args.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 score_power.py
