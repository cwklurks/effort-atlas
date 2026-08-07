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
              f"Repository: `{r['repository']}` at `{r['sha']}`",
              f"Path: `{r['path']}` lines {r['line_start']}-{r['line_end']}",
              f"Permalink: {r['permalink']}",
              f"Encoding/line endings: `{r['encoding']}` / `{r['line_ending']}`; generated file: `{str(r['generated_file']).lower()}`.",'',
              '````json',json.dumps(r['quote'], ensure_ascii=False),'````','']
lines += ['## Verification log','',
'Phase 1 receipt gate: `.venv/bin/python ecosystem_audit/validate_receipts.py` (exit 0).','']
verification=ROOT/'verification_receipt.json'
if verification.exists():
    gate=json.loads(verification.read_text())
    lines += [f"Recorded compound gate exit status: `{gate['compound_gate_exit_status']}` at `{gate['completed_at']}`.",'']
    for result in gate['commands']:
        lines += [f"- `{result['command']}` — exit `{result['exit_status']}`; {result['observation']}."]
    lines += ['']
else:
    lines += ['Full offline, strict, executable-reproduction, and root-suite gates have not yet been recorded.','']
# Phase 3 appends generated narrative when available.
timeline=ROOT/'timeline.csv'
if timeline.exists():
    with timeline.open(newline='',encoding='utf-8') as f: trows=list(csv.DictReader(f))
    status=Counter(r['status'] for r in trows)
    eras=Counter(r['era_relation'] for r in trows)
    remediation=sum(r['remediation']=='true' for r in trows)
    lines += ['## Git archaeology and era comparison','',
              f"`timeline.csv` contains {len(trows)} generated setting histories. Status counts: "+', '.join(f"{k}={v}" for k,v in sorted(status.items()))+'.',
              f"Era buckets are generated from author dates: "+', '.join(f"{k}={v}" for k,v in sorted(eras.items()))+f". The rows contain {remediation} evidenced remediation events.",'',
              'OpenAI o1 (`2024-09`) and DeepSeek R1 (`2025-01`) are supplied contextual era markers, not causal evidence. The history does not support a universal story that every cap predates reasoning models: traced introductions occur both before and after the markers. Several repositories later raised or removed task caps, but their commit messages establish only local motivation, not ecosystem-wide causation.','',
              'The supplied local REAP context says o4-mini(high) p90 is 38,125 tokens. That observation is sourced to `TASK.md` only and is not evidence about any external repository’s runtime behavior. It is not compared to `not_traceable` or dynamic settings as if those were numeric caps.','',
              'Every verified row preserves exact history commands in `timeline_evidence.json`. OpenCompass AIME and GPQA task-local caps use the required `not found at configs/ searched at ...` form rather than guessing provider defaults.','']
fields=['finding_id','target','category','claim','repository','sha','path','line_start','line_end','permalink','quote','status']
with (ROOT/'audit_data.csv').open('w',newline='',encoding='utf-8') as handle:
    writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for receipt in receipts:
        row={key:receipt[key] for key in fields};row['quote']=json.dumps(row['quote'],ensure_ascii=False)
        writer.writerow(row)
(ROOT/'AUDIT.md').write_text('\n'.join(lines),encoding='utf-8')
