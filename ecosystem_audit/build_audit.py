#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
receipts=json.loads((ROOT/'receipt_index.json').read_text(encoding='utf-8'))['receipts']
issues=json.loads((ROOT/'issue_receipts.json').read_text(encoding='utf-8'))['issues']
by_target=defaultdict(list)
for row in receipts: by_target[row['target']].append(row)

def table(rows, headers):
    out=['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    for row in rows:
        out.append('| '+' | '.join(str(x).replace('|','\\|').replace('\n',' ') for x in row)+' |')
    return '\n'.join(out)

def refs(categories):
    rows=[]
    for r in receipts:
        if r['category'] in categories:
            rows.append((r['target'],r['claim'],f"[{r['finding_id']}](#{r['finding_id'].lower()})"))
    return table(rows,['Target','Finding','Receipt'])

lines=['# Ecosystem audit','','## Scope and method','',
'This is a source-code audit and an isolated post-generation diagnostic, not an end-to-end model evaluation. External repositories are frozen in `repos.lock.json`; code receipts are UTF-8 decoded without whitespace normalization and use 1-indexed inclusive line ranges. No model or paid API call is part of the workflow.','',
'All code claims below resolve to the literal quote in the receipt ledger. Absence claims and exact searches are recorded in `GAPS.md`. Issue facts are kept separate from code claims.','',
'## Output-token settings','',refs({'default_cap','default_cap_resolution','model_cap'}),'',
'## Reasoning-task settings and inheritance','',refs({'task_cap','task_cap_inheritance'}),'',
'Not applicable means the repository is an extractor/scorer library rather than a generation harness. An unset value is not converted here into a guessed provider default. Adapter-specific defaults are scoped to the adapter named in the receipt.','',
'## Extraction, normalization, and scoring','',refs({'extraction','extraction_call','extraction_fallback','extraction_incomplete','extraction_scoring','scoring','scoring_call'}),'',
'Extraction is reported separately from correctness. A returned nonempty value on a truncated fixture is the operational answer-returned event; it is not by itself evidence that answer text was newly invented. Native correctness is used only where the actual downstream path is runnable.','',
'## Truncation visibility','']
visibility=[
('lm-evaluation-harness','No','No','No','No','not found; see GAPS.md'),
('opencompass','Yes in inspected streaming adapter','Yes, aggregate counts','Yes, as result counts','No evidence','F010-F011'),
('helm','Yes','Yes, finish metrics','Yes, as metrics','No; reported alongside scoring','F013-F014'),
('inspect_ai','Yes','Yes in ModelOutput/log','Yes','No in inspected match scorer','F017-F018'),
('inspect_evals','Via inspect_ai','Via inspect_ai','Via inspect_ai','No in AIME scorer','F019-F020'),
('simple-evals','No','No','No','No','not found; see GAPS.md'),
('lighteval','No in inspected LiteLLM conversion','No','No','No','finish reason dropped; receipt ledger'),
('livebench','Partial for empty token exhaustion','Coarse eval_status','Coarse status','Only coarse failure status, not nonempty truncation','receipt ledger'),
('math-verify','Not applicable','Not applicable','Not applicable','No finish input','text-only library'),
('matharena','Raw provider log may capture it','Raw log only; semantic result drops it','Heuristic warning only','Actual reason no; length heuristic after wrong score','receipt ledger'),
]
lines += [table(visibility,['Target','Captured','Persisted/logged','User-visible','Used to distinguish truncated from wrong','Evidence']),'',
'## Issue receipts','',
'These issue facts corroborate but do not replace code evidence. Retrieval metadata and hashes are in `issue_receipts.json`.','']
issue_rows=[]
for x in issues:
    if x.get('html_url'):
        issue_rows.append((x['repository'],f"[#{x['number']}]({x['html_url']})",x['title'],x['state'],x['created_at'],x.get('closed_at') or '',x['retrieved_at'][:10]))
    else:
        issue_rows.append((x['repository'],f"#{x['number']}",'unavailable','unavailable','','',x['retrieved_at'][:10]))
lines += [table(issue_rows,['Repository','Issue','Title','State','Created','Closed','Retrieved']),'',
'- `lm-evaluation-harness` #3382 directly describes incomplete reasoning being parsed as a final response after truncation.','- #3044 concerns reasoning models and token limits; #3391 concerns thinking-model MMLU-Pro behavior.','- `inspect_ai` #3582 concerns token-limited responses not being readily visible to end users.','',
'## Finding inventory','',table(sorted(Counter(r['target'] for r in receipts).items()),['Target','Atomic code findings']),'',
'## Receipt ledger','']
for r in receipts:
    lines += [f"### {r['finding_id']}",'',r['claim'],'',
              f"Repository: `{r['repository']}` at `{r['sha']}`  ",
              f"Path: `{r['path']}` lines {r['line_start']}-{r['line_end']}  ",
              f"Permalink: {r['permalink']}  ",
              f"Encoding/line endings: `{r['encoding']}` / `{r['line_ending']}`; generated file: `{str(r['generated_file']).lower()}`.",'',
              '````text',r['quote'].rstrip('\r\n'),'````','']
lines += ['## Verification log','',
'Phase 1 receipt gate: `.venv/bin/python ecosystem_audit/validate_receipts.py` (exit 0).','',
'Full offline, strict, executable-reproduction, root-suite, and PR gates are recorded here only after they run successfully.','']
# Phase 3 appends generated narrative when available.
timeline=ROOT/'timeline.csv'
if timeline.exists():
    with timeline.open(newline='',encoding='utf-8') as f: trows=list(csv.DictReader(f))
    status=Counter(r['status'] for r in trows)
    lines += ['## Git archaeology and era comparison','',
              f"`timeline.csv` contains {len(trows)} generated setting histories. Status counts: "+', '.join(f"{k}={v}" for k,v in sorted(status.items()))+'.','',
              'OpenAI o1 (`2024-09`) and DeepSeek R1 (`2025-01`) are supplied contextual era markers, not causal evidence. Each row preserves its exact history command and validation status.','']
(ROOT/'AUDIT.md').write_text('\n'.join(lines),encoding='utf-8')
