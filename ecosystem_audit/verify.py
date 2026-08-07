#!/usr/bin/env python3
"""Dependency-free offline/strict verifier for the pinned ecosystem audit."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'ecosystem_audit';REAL=ROOT/'observational/real_truncated_fixtures.jsonl.gz'
REAL_SHA='b84adb85eccd6b628829cdadb71c29fa25eb4dc0a37d387f554464b312d96f43'
REQUIRED=['AUDIT.md','audit_data.csv','results_table.md','fixture_results.csv','pipeline_metrics.csv','timeline.csv','GAPS.md','repos.lock.json','receipt_index.json','adapter_manifest.json','execution_log.json','synthetic_fixtures.jsonl','run_executable_audit.py','validate_receipts.py','validate_timeline.py']

def command(args,check=True):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if check and result.returncode: raise AssertionError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}{result.stderr}")
    return result

def table(path):
    with path.open(newline='',encoding='utf-8') as handle:return list(csv.DictReader(handle))

def verify_files():
    missing=[name for name in REQUIRED if not (A/name).is_file()];assert not missing,f'missing files: {missing}'
    result_required={'target','pipeline_id','commit','fixture_id','kind','stratum','shape','truncated','applicable','adapter_status','applicability_reason','extracted_answer','answer_returned','native_correct','escaped_exception','exception_class','exception_message','swallowed_error_observed','swallowed_error_detail','duration_status'}
    metric_required={'target','pipeline_id','commit','pipeline_status','stratum','metric','numerator','denominator','pct','value'}
    timeline_required={'harness','pipeline_or_task','setting','value','introduced_commit','introduced_date','remediated_value','remediated_commit','remediated_date','era_relation','evidence_command','status'}
    for path,required in [(A/'fixture_results.csv',result_required),(A/'pipeline_metrics.csv',metric_required),(A/'timeline.csv',timeline_required)]:
        rows=table(path);assert rows and required<=set(rows[0]),f'columns missing in {path.name}: {required-set(rows[0])}'

def verify_corpora():
    compressed=REAL.read_bytes();assert hashlib.sha256(compressed).hexdigest()==REAL_SHA
    raw=gzip.decompress(compressed);lines=raw.splitlines(keepends=True);assert len(lines)==195 and raw.endswith(b'\n')
    records=[json.loads(line) for line in lines];assert Counter(r['kind'] for r in records)=={'truncated':131,'control_correct':64}
    assert sum(r['kind']=='truncated' and r['text']=='' for r in records)==12
    sys.path.insert(0,str(ROOT/'trunccheck/src'))
    from trunccheck import fixtures_to_jsonl,generate_synthetic_fixtures
    synthetic=(A/'synthetic_fixtures.jsonl').read_bytes();generated=fixtures_to_jsonl(generate_synthetic_fixtures(1729));assert synthetic==generated
    parsed=[json.loads(line) for line in synthetic.splitlines()]
    assert len(parsed)==100 and Counter(r['shape'] for r in parsed)=={s:20 for s in ('mid_box','mid_multiple_choice_enumeration','post_final_answer','degeneration_loop_plausible_number','mid_latex_expression')}
    assert all(r['seed']==1729 and r['kind']=='truncated' for r in parsed)

def verify_results():
    command([sys.executable,str(A/'verify_phase2.py')])
    results=table(A/'fixture_results.csv');app=table(A/'applicability.csv');pipelines={r['pipeline_id'] for r in app}
    assert len(results)==295*len(pipelines)
    for pipeline in pipelines:
        rows=[r for r in results if r['pipeline_id']==pipeline];assert len(rows)==295 and len({r['fixture_id'] for r in rows})==295
        for row in rows:
            if row['adapter_status']!='ok':assert row['status_reason'] or row['applicability_reason'],f'missing reason: {pipeline}/{row["fixture_id"]}'
    manifest=json.loads((A/'adapter_manifest.json').read_text())
    assert {r['pipeline_id'] for r in manifest['pipelines']}==pipelines and manifest['no_model_calls'] is True
    for pipeline in manifest['pipelines']:
        env=pipeline['environment'];path=ROOT/env['lock_file'];assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==env['lock_sha256']
        assert pipeline['source_receipts'] and pipeline['status'] in {'ok','control_disqualified','import_failed','install_failed','not_runnable'}
    deterministic=json.loads((A/'determinism_manifest.json').read_text());assert deterministic['seed']==1729 and deterministic['independent_runs_compared']==2 and deterministic['byte_identical'] is True
    for name,digest in deterministic['sha256'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==digest

def verify_git_contract():
    repro=json.loads((A/'reproduction_manifest.json').read_text());start=repro['task_start_commit'];base=repro['merge_base']
    allowed=('TASK.md','observational/real_truncated_fixtures.jsonl.gz','ecosystem_audit/','trunccheck/')
    changed=command(['git','diff','--name-only',f'{base}...HEAD']).stdout.splitlines()
    assert changed and all(path in allowed[:2] or path.startswith(allowed[2:]) for path in changed),f'disallowed committed paths: {changed}'
    for path in ('TASK.md','observational/real_truncated_fixtures.jsonl.gz'):
        result=subprocess.run(['git','show',f'{start}:{path}'],cwd=ROOT,capture_output=True)
        assert result.returncode==0 and (ROOT/path).read_bytes()==result.stdout,f'seed input changed: {path}'
    assert hashlib.sha256(REAL.read_bytes()).hexdigest()==REAL_SHA
    assert command(['git','diff','--check']).returncode==0
    status=command(['git','status','--porcelain=v1','--untracked-files=all']).stdout
    assert status=='',f'working tree is not clean:\n{status}'

def verify_strict_repositories():
    lock=json.loads((A/'repos.lock.json').read_text())['repositories']
    for entry in lock:
        repo=A/'_repos'/entry['name'];assert (repo/'.git').exists(),f"missing checkout: {entry['name']}"
        def git(*args,check=True):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
            if check and result.returncode:raise AssertionError(f"{entry['name']} git {' '.join(args)}: {result.stderr}")
            return result
        assert git('rev-parse','HEAD').stdout.strip()==entry['sha']
        assert git('rev-parse','--is-shallow-repository').stdout.strip()=='false'
        assert int(git('rev-list','--count','HEAD').stdout)>1
        remote=git('remote','get-url','origin').stdout.strip();assert '@' not in remote and re.fullmatch(r'https://github\.com/[^/]+/[^/]+(?:\.git)?',remote)
        assert remote.removesuffix('.git').lower()==('https://github.com/'+entry['repository']).lower()
        modules=git('show',f"{entry['sha']}:.gitmodules",check=False)
        if entry['submodule_state']=='none_declared':assert modules.returncode!=0
        elif entry['submodule_state']=='present_uninitialized':
            assert modules.returncode==0
            status=git('submodule','status').stdout.splitlines();assert status and all(line.startswith('-') for line in status)
        else:raise AssertionError(f"unknown submodule state: {entry['submodule_state']}")
        attrs=git('show',f"{entry['sha']}:.gitattributes",check=False)
        has_lfs=attrs.returncode==0 and 'filter=lfs' in attrs.stdout
        assert has_lfs==(entry['lfs_state']=='attributes_present')
    command([sys.executable,str(A/'validate_receipts.py')])
    command([sys.executable,str(A/'validate_timeline.py')])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--strict',action='store_true');args=parser.parse_args()
    verify_files();verify_corpora();verify_results()
    if args.strict:verify_strict_repositories()
    elif not args.offline:print('note: repository receipt/history checks require --strict')
    verify_git_contract()
    print(f"ecosystem audit verified ({'strict' if args.strict else 'offline' if args.offline else 'standard'}): 10 targets, 2950 fixture-pipeline rows")
if __name__=='__main__':main()
