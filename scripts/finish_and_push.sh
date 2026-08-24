#!/usr/bin/env bash
# finish_and_push.sh — one-shot: sort loose root docs into docs/, commit today's
# work in four reviewable commits, and push the branch so other devices can pull.
#
# Run from anywhere INSIDE the repo on the Mac (normal terminal, not a sandbox):
#   bash scripts/finish_and_push.sh
#
# Safe by construction: no deletions of content, no edits to frozen files
# (PREREGISTRATION*, confirmatory_artifacts/, observational/pipeline.py untouched),
# every move is guarded, every commit is skipped if empty. Re-runnable.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
BRANCH="$(git branch --show-current)"
echo "== repo: $(pwd) | branch: $BRANCH"

# ---- 0. clean up lockfiles/temp junk left by the cloud-bridge session (its
#         sandbox could rename but not delete; your terminal can delete).
rm -f .git/index.lock .git/index.lock.stale .git/stale_lock_* 2>/dev/null || true
find .git/objects -name 'tmp_obj_*' -delete 2>/dev/null || true

# ---- 1. keep raw benchmark JSONLs out of git (repo convention: reacquire locally;
#         bytes are pinned by hash in capabilities/sources_manifest.json).
#         Sanitized gpqa_main.jsonl IS committed; restricted_local/ is already ignored.
if ! grep -q "capabilities/mmlu_pro.jsonl" .gitignore; then
cat >> .gitignore <<'EOF'

# Reacquirable benchmark JSONLs (regenerate: python3 capabilities/acquire.py;
# expected hashes pinned in capabilities/sources_manifest.json)
capabilities/mmlu_pro.jsonl
capabilities/ifeval.jsonl
capabilities/wildbench_v2.jsonl
capabilities/omni_math.jsonl
EOF
fi

# ---- 2. commit 1: capabilities acquisition pipeline
git add .gitignore capabilities/acquire.py capabilities/validate.py \
        capabilities/README.md capabilities/sources_manifest.json \
        capabilities/validation_report.json capabilities/gpqa_main.jsonl
git diff --cached --quiet || git commit -m "Add capabilities source-acquisition pipeline

All five HELM-Capabilities benchmarks pulled from pinned original sources
(MMLU-Pro 12,032+70, GPQA main 448, IFEval 541, WildBench v2 1,024,
Omni-MATH 4,428), normalized to source-item-v1 JSONL with per-row hashes.
Byte-identical across independent runs; validate.py recomputes everything.
GPQA committed sanitized only (no question text; hash-linked to a
gitignored local plaintext file). Open-text JSONLs are not vendored:
regenerate with acquire.py; hashes pinned in sources_manifest.json.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014j92Se72koAnMBJf2AuacZ"

# ---- 3. commit 2: meeting-review docs and prompt archive
git add reap/23_POST_MEETING_REVIEW_2026-08-23.md \
        reap/13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md \
        reap/14_PHASE3_EXTERNAL_REVIEW_2026-08-10.md \
        reap/prompts/ 2>/dev/null || true
git diff --cached --quiet || git commit -m "Add 2026-08-23 post-meeting review and prompt archive

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014j92Se72koAnMBJf2AuacZ"

# ---- 4. commit 3: sort loose root documents into docs/
mkdir -p docs/meetings docs/paper docs/outreach docs/visuals

mv_u() { [ -e "$1" ] && mv -n "$1" "$2" && echo "  mv  $1 -> $2" || true; }       # untracked
mv_t() { [ -e "$1" ] && git mv -k "$1" "$2" && echo "  gmv $1 -> $2" || true; }   # tracked

# meetings (all untracked)
for f in BENCHMARK_TABLE_FOR_CHIRAG.md CALL_CRIB_ONE_PAGE.md CALL_NOTES_TEMPLATE.md \
         CALL_PREP_KM_CHEATSHEET.md CALL_RUNBOOK.md CHIRAG_MEETING_DECISIONS.md \
         CHIRAG_MEETING_MASTER_GUIDE.md; do mv_u "$f" docs/meetings/; done
# paper (all untracked)
for f in PAPER_OUTLINE_FOR_CHIRAG.md PAPER_OUTLINE_FOR_CHIRAG_v2.md \
         REVIEW_PROMPT_FOR_PAPER_OUTLINE.md Thinking_Cut_Short_outline.docx; do
  mv_u "$f" docs/paper/; done
# outreach (tracked)
mv_t OUTREACH_PACKET.md docs/outreach/
mv_t OUTREACH_RESEARCH.md docs/outreach/
# visuals (html untracked; tldraw tracked)
for f in benchmark_table_for_chirag.html call_crib.html chirag_meeting_master.html \
         chirag_story_visual.html intersection_visual.html km_math_visual_explainer.html; do
  mv_u "$f" docs/visuals/; done
mv_t thinking-cut-short-explainer.tldraw docs/visuals/

# fix the one root README link that pointed at a moved file (non-frozen file)
sed -i '' 's|(OUTREACH_RESEARCH.md)|(docs/outreach/OUTREACH_RESEARCH.md)|' README.md 2>/dev/null \
  || sed -i 's|(OUTREACH_RESEARCH.md)|(docs/outreach/OUTREACH_RESEARCH.md)|' README.md

git add docs/ README.md scripts/finish_and_push.sh
git diff --cached --quiet || git commit -m "Organize loose root documents into docs/

Meeting prep -> docs/meetings, paper drafts -> docs/paper, outreach ->
docs/outreach, HTML/tldraw visuals -> docs/visuals. Content unmodified;
one README link updated. Frozen and evidence-chain files (PREREGISTRATION*,
RESEARCH_LOG, CAP_SEMANTICS, TRUNCATION_STUDY, METHODS_BRIEF,
CONFIRMATORY_PREFLIGHT, configs) stay at root. Index: docs/README.md.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014j92Se72koAnMBJf2AuacZ"

# ---- 5. commit 4: dashboard state that was already modified locally
git add reap/status/index.html reap/status/phase_status.json 2>/dev/null || true
git diff --cached --quiet || git commit -m "Update status dashboard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014j92Se72koAnMBJf2AuacZ"

# ---- 6. push everything (includes the 8 commits that were already ahead)
git push origin "$BRANCH"

echo ""
echo "== DONE. Pushed '$BRANCH' to origin. Deliberately left uncommitted:"
git status --short | sed 's/^/   /' || true
echo ""
echo "== On the Linux device:"
echo "   git clone https://github.com/cwklurks/effort-atlas.git && cd effort-atlas   # or: git fetch && git checkout $BRANCH && git pull"
echo "   pip install huggingface_hub pandas pyarrow"
echo "   python3 capabilities/acquire.py     # rebuilds the JSONLs byte-identically (hashes in sources_manifest.json)"
echo "   python3 capabilities/validate.py    # must print PASS"
