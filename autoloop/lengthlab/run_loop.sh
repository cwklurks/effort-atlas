#!/usr/bin/env bash
# lengthlab autoresearch driver — deterministic keep/revert harness.
#
# The agent proposes ONE hypothesis per iteration and edits ONE file.
# This script — not the agent — runs the metric, enforces the editable
# surface (reverts anything else the agent touched), applies the min_delta
# rule, and commits kept steps. Run it inside a DEDICATED clone/worktree,
# never your main working copy.
#
# Usage:
#   ./run_loop.sh A          # loop A: estimators.py, minimize recovery error
#   ./run_loop.sh B          # loop B: design.py, maximize worst-case power
#   ITERS=200 ./run_loop.sh A
#   AGENT_CMD='codex exec --full-auto' ./run_loop.sh A   # non-Claude proposer
#   touch autoloop/lengthlab/STOP                        # graceful stop
set -euo pipefail

LOOP="${1:?usage: run_loop.sh A|B}"
cd "$(git rev-parse --show-toplevel)"
LAB="autoloop/lengthlab"
ITERS="${ITERS:-100}"
AGENT_CMD="${AGENT_CMD:-claude --dangerously-skip-permissions -p}"

if [ "$LOOP" = "A" ]; then
  EDITABLE="$LAB/estimators.py"; METRIC="$LAB/metric_recovery.sh"
  DIRECTION="min"; MIN_DELTA=0.003; LOG="$LAB/RUN_LOG_A.md"
  GOAL="reduce the mean recovery error of median/q90/P(length>=c) under censoring"
elif [ "$LOOP" = "B" ]; then
  EDITABLE="$LAB/design.py"; METRIC="$LAB/metric_power.sh"
  DIRECTION="max"; MIN_DELTA=0.006; LOG="$LAB/RUN_LOG_B.md"
  GOAL="raise worst-case detection power; a 0.0 score means a hard gate failed (budget or type-I) — run 'python3 $LAB/score_power.py --json' mentally via the log, the scorer docstring explains the gates"
else
  echo "loop must be A or B" >&2; exit 2
fi

command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 1; }
python3 -c "import numpy" 2>/dev/null || { echo "numpy missing: try 'uv run --with numpy' variants or install numpy" >&2; exit 1; }
[ -f "$LOG" ] || printf '# lengthlab loop %s run log\n\n' "$LOOP" > "$LOG"

score() { bash "$METRIC" 2>>"$LAB/metric_err.log"; }
is_float() { python3 -c "import sys; float(sys.argv[1])" "$1" 2>/dev/null; }
improved() { # improved <new> <best>
  python3 - "$1" "$2" "$DIRECTION" "$MIN_DELTA" <<'PY'
import sys
new, best, d, md = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], float(sys.argv[4])
ok = (new < best - md) if d == "min" else (new > best + md)
sys.exit(0 if ok else 1)
PY
}

revert_out_of_scope() {
  # Revert/delete every change the agent made outside the editable file + log.
  git status --porcelain -- . | while IFS= read -r line; do
    st="${line:0:2}"; f="${line:3}"
    case "$f" in "$EDITABLE"|"$LOG"|"$LAB/metric_err.log") continue ;; esac
    if [ "$st" = "??" ]; then rm -rf -- "$f"; else git checkout -q -- "$f" || true; fi
  done
}

best="$(score || true)"
is_float "$best" || { echo "baseline metric failed: '$best'" >&2; exit 1; }
echo "[$LOOP] baseline: $best (direction $DIRECTION, min_delta $MIN_DELTA)"
SESSION="$(date +%Y%m%d-%H%M)"

for i in $(seq 1 "$ITERS"); do
  [ -f "$LAB/STOP" ] && { echo "STOP file found, exiting"; rm -f "$LAB/STOP"; break; }

  PROMPT="You are iteration $SESSION/$i of a keep-or-revert optimization loop.
Goal: $GOAL. Current best score: $best (direction: $DIRECTION; a change only
survives if it beats best by more than $MIN_DELTA — noise-sized tweaks are wasted turns).
Steps, exactly these:
1. Read $LOG (past hypotheses and outcomes — do not repeat a failed idea).
2. Read $EDITABLE, and read-only for context: $LAB/generator.py and the scorer.
3. Append to $LOG: '## $SESSION/$i HYPOTHESIS: <one sentence>' BEFORE editing.
4. Implement that ONE hypothesis by editing ONLY $EDITABLE.
Rules: edit no file except $EDITABLE and $LOG. Do not run git. Do not run the
metric or claim a score. No network. Do not touch generator.py or score_*.py.
Keep $EDITABLE's function signatures/contract unchanged."

  $AGENT_CMD "$PROMPT" >/dev/null 2>>"$LAB/agent_err.log" || true
  revert_out_of_scope

  new="$(score || true)"
  if is_float "$new" && improved "$new" "$best"; then
    best="$new"
    printf 'RESULT %s/%s: %s  KEPT (new best)\n\n' "$SESSION" "$i" "$new" >> "$LOG"
    git add -- "$EDITABLE" "$LOG"; git commit -qm "loop$LOOP $SESSION/$i: $new"
    echo "[$LOOP] iter $i KEPT  $new"
  else
    git checkout -q -- "$EDITABLE"
    printf 'RESULT %s/%s: %s  reverted (best %s)\n\n' "$SESSION" "$i" "${new:-crash}" "$best" >> "$LOG"
    git add -- "$LOG"; git commit -qm "loop$LOOP $SESSION/$i: reverted"
    echo "[$LOOP] iter $i rev   ${new:-crash} (best $best)"
  fi
done

echo "[$LOOP] done. best: $best  — log: $LOG, kept steps in git log."
echo "Now run the holdout: LENGTHLAB_HOLDOUT_SEED=<secret> python3 $LAB/final_eval.py"
