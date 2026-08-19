#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
repomix_bin=${REPOMIX_BIN:-repomix}
destination="$repo_root/reap/linux_handoff/REPO_CONTEXT.xml"
temporary=$(mktemp "$repo_root/reap/linux_handoff/REPO_CONTEXT.XXXXXX.xml")
trap 'rm -f "$temporary"' EXIT HUP INT TERM

if ! command -v "$repomix_bin" >/dev/null 2>&1; then
  echo "repomix is required to rebuild the Linux context pack" >&2
  exit 1
fi

cd "$repo_root"
"$repomix_bin" . \
  --output "$temporary" \
  --style xml \
  --parsable-style \
  --include-logs \
  --include-logs-count 20 \
  --header-text "REAP Linux orientation bundle. Canonical repository files and current Git state override this convenience copy. Contains no authorization for provider, smoke, or confirmatory calls." \
  --include "AGENTS.md,README.md,pyproject.toml,uv.lock,PREREGISTRATION*.md,reap/**/*.md,reap/phase3_evidence/*.json,reap/status/phase_status.json,observational/RESULTS.md,observational/INPUT_PROVENANCE.md,observational/state_manifest.json,observational/benchmark_sources_manifest.json,observational/benchmark_question_capabilities_summary.json,src/effort_atlas/**/*.py,scripts/**/*.py,scripts/**/*.sh,tests/**/*.py" \
  --ignore "reap/linux_handoff/REPO_CONTEXT*.xml,reap/linux_handoff/CONTEXT_BUILD_RECEIPT.md,reap/next_chapter/index.html,reap/next_chapter/artifact.json,observational/benchmark_question_capabilities.jsonl,tests/fixtures/**,reap/relay_reviews/**,reap/phase3_review_artifacts/**"

mv "$temporary" "$destination"
trap - EXIT HUP INT TERM

bytes=$(wc -c < "$destination" | tr -d ' ')
digest=$(shasum -a 256 "$destination" | awk '{print $1}')
echo "Wrote reap/linux_handoff/REPO_CONTEXT.xml ($bytes bytes, sha256=$digest)"
