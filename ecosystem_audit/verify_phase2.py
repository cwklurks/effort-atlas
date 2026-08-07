#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'ecosystem_audit'
sys.path.insert(0,str(ROOT/'trunccheck/src'))
from trunccheck import fixtures_to_jsonl,generate_synthetic_fixtures,load_real_fixtures

def main():
    synth=(A/'synthetic_fixtures.jsonl').read_bytes(); expected=fixtures_to_jsonl(generate_synthetic_fixtures(1729))
    assert synth==expected,'synthetic bytes differ'
    parsed=[json.loads(x) for x in synth.splitlines()]
    assert len(parsed)==100 and Counter(r['shape'] for r in parsed)=={s:20 for s in ('mid_box','mid_multiple_choice_enumeration','post_final_answer','degeneration_loop_plausible_number','mid_latex_expression')}
    assert all(r['seed']==1729 for r in parsed)
    real=load_real_fixtures(ROOT/'observational/real_truncated_fixtures.jsonl.gz');assert len(real)==195
    with (A/'fixture_results.csv').open(newline='',encoding='utf-8') as f:results=list(csv.DictReader(f))
    with (A/'applicability.csv').open(newline='',encoding='utf-8') as f:app=list(csv.DictReader(f))
    assert len(results)==295*len(app)
    expected_ids={f.fixture_id for f in real}|{r['fixture_id'] for r in parsed}
    for row in app:
        subset=[r for r in results if r['pipeline_id']==row['pipeline_id']]
        assert len(subset)==295 and {r['fixture_id'] for r in subset}==expected_ids
        for result in subset:
            assert result['adapter_status'] in {'ok','not_applicable','not_runnable','install_failed','import_failed'}
            if result['adapter_status']=='not_applicable':assert result['applicability_reason']
    spec=importlib.util.spec_from_file_location('audit_runner',A/'run_executable_audit.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    expected_metrics=module.calculate_metrics(results,app)
    with (A/'pipeline_metrics.csv').open(newline='',encoding='utf-8') as f:metrics=list(csv.DictReader(f))
    assert metrics==expected_metrics,'metric recalculation differs'
    entries=module.locked();assert (A/'results_table.md').read_text()==module.markdown(metrics,entries)
    statuses={r['pipeline_id']:r['pipeline_status'] for r in metrics}
    md=(A/'results_table.md').read_text()
    for pipeline,status in statuses.items():
        if status=='control_disqualified':
            assert f'| {pipeline} | control_disqualified |' in md
            headline=md.split('## Headline-eligible pipeline rows',1)[1].split('## Locked repositories',1)[0]
            assert f'| {pipeline} |' not in headline
    print(f'phase 2 verified: {len(results)} fixture-pipeline rows; synthetic sha256={hashlib.sha256(synth).hexdigest()}')
if __name__=='__main__':main()
