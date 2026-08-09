#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, subprocess
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'ecosystem_audit';REPOS=A/'_repos'

def git(repo,*args,check=True):
    result=subprocess.run(['git','-C',str(REPOS/repo),*args],capture_output=True,text=True)
    if check and result.returncode: raise AssertionError(f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}")
    return result

def main():
    lock={row['name']:row for row in json.loads((A/'repos.lock.json').read_text())['repositories']}
    with (A/'timeline.csv').open(newline='',encoding='utf-8') as handle: rows=list(csv.DictReader(handle))
    required={'harness','pipeline_or_task','setting','value','introduced_commit','introduced_date','remediated_value','remediated_commit','remediated_date','era_relation','evidence_command','status','timeline_id','target','repository','setting_scope','event','previous_value','new_value','remediation','current_snapshot_sha','path','source_text','notes'}
    assert rows and required<=set(rows[0])
    assert len(rows)>=35 and len({r['timeline_id'] for r in rows})==len(rows)
    assert set(lock)=={r['target'] for r in rows},'every locked target must have timeline coverage'
    evidence={r['timeline_id']:r for r in json.loads((A/'timeline_evidence.json').read_text())['rows']}
    assert set(evidence)=={r['timeline_id'] for r in rows}
    for target,entry in lock.items():
        assert (REPOS/target).is_dir(),f'missing full-history clone {target}'
        assert git(target,'rev-parse','--is-shallow-repository').stdout.strip()=='false'
        assert git(target,'rev-parse','HEAD').stdout.strip()==entry['sha']
        origin=git(target,'remote','get-url','origin').stdout.strip().removesuffix('.git').lower()
        expected=('https://github.com/'+entry['repository']).lower()
        assert origin==expected,(target,origin,expected)
    for row in rows:
        assert row['repository']==lock[row['target']]['repository']
        assert row['harness']==row['target'] and row['pipeline_or_task']==row['setting_scope'] and row['value']==row['new_value']
        assert row['current_snapshot_sha']==lock[row['target']]['sha']
        if row['introduced_date']:
            day=row['introduced_date'][:10]
            expected_era='pre_o1_marker' if day<'2024-09-01' else ('o1_to_r1_markers' if day<'2025-01-01' else 'post_r1_marker')
            assert row['era_relation']==expected_era
        else: assert row['era_relation']=='not_traceable'
        item=evidence[row['timeline_id']]
        if row['status']=='verified':
            sha=row['introduced_commit'];repo=row['target']
            assert sha and len(sha)==40 and git(repo,'cat-file','-t',sha).stdout.strip()=='commit'
            assert git(repo,'merge-base','--is-ancestor',sha,row['current_snapshot_sha'],check=False).returncode==0
            assert git(repo,'show','-s','--format=%aI',sha).stdout.strip()==row['introduced_date']
            blob=git(repo,'show',f"{sha}:{row['path']}").stdout
            assert row['source_text'] and row['source_text'] in blob,(row['timeline_id'],row['source_text'])
            commands=item['commands'];assert len(commands)==2 and all(c['returncode']==0 for c in commands)
            assert commands[0]['stdout'].splitlines()[:2]==[sha,row['introduced_date']]
            assert commands[1]['stdout_sha256']==hashlib.sha256(blob.encode()).hexdigest()
            assert any(row['source_text'] in line for line in commands[1]['matching_lines'])
            if row['remediation']=='true':
                assert row['event']=='remediation' and row['previous_value'] and row['remediation_commit']==sha and row['remediation_date']==row['introduced_date']
                assert row['remediated_value']==row['new_value'] and row['remediated_commit']==sha and row['remediated_date']==row['introduced_date']
            else:
                assert not row['remediation_commit'] and not row['remediation_date'] and not row['remediated_value'] and not row['remediated_commit'] and not row['remediated_date']
        elif row['status']=='not_traceable':
            assert not row['introduced_commit'] and not row['introduced_date'] and row['notes'].startswith('not found at ')
            commands=item['commands'];assert len(commands)==1 and commands[0]['command']==row['evidence_command'] and commands[0]['returncode']==1 and not commands[0]['stdout']
        else: raise AssertionError(f"invalid status: {row['status']}")
    print(f"validated {len(rows)} timeline rows across {len(lock)} full-history clones: {dict(sorted(Counter(r['status'] for r in rows).items()))}")
if __name__=='__main__':main()
