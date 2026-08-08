#!/usr/bin/env python3
"""Deterministic offline orchestrator for locked post-generation adapters."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'ecosystem_audit'
REPOS=AUDIT/'_repos'
ENVS=AUDIT/'_envs'
FIXTURE=ROOT/'observational/real_truncated_fixtures.jsonl.gz'
TRUNCSRC=ROOT/'trunccheck/src'
OUTPUTS=('fixture_results.csv','pipeline_metrics.csv','results_table.md')
PYTHONS={
 'lm-evaluation-harness':ENVS/'lm_eval/bin/python','opencompass':ENVS/'opencompass/bin/python',
 'helm':ENVS/'helm/bin/python','inspect_ai':ENVS/'inspect/bin/python','inspect_evals':ENVS/'inspect/bin/python',
 'simple-evals':ENVS/'simple/bin/python','lighteval':ENVS/'lighteval/bin/python','livebench':ENVS/'livebench/bin/python',
 'math-verify':ENVS/'math_verify/bin/python','matharena':ENVS/'matharena/bin/python',
}
RESULT_COLUMNS=('target','pipeline_id','repository_sha','fixture_id','kind','stratum','shape','dataset','problem_idx','text_empty','control_gold_eligible','pre_truncation_answer_present','applicable','applicability_reason','adapter_status','status_reason','extracted_answer','answer_returned','answer_is_numeric','exception_class','exception_message','swallowed_error_observed','swallowed_error_detail','native_correct','duration_status')
METRIC_COLUMNS=('target','pipeline_id','pipeline_status','metric','stratum','numerator','denominator','percent','metric_status')
INTEGER_GOLD=re.compile(r'^[+-]?\d+$')
PRE_TRUNCATION_ANSWER=re.compile(r'\\boxed\{.+?\}',re.DOTALL)
MINIMUM_REAL_N=20

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boolstr(value): return '' if value is None else ('true' if value else 'false')
def parsebool(value):
    if value in (True,'true','True','1',1): return True
    if value in (False,'false','False','0',0): return False
    return None

def control_gold_eligible(row):
    """Frozen round-2 control schema: a scalar base-10 integer gold answer."""
    value=row.get('gold_answer')
    return value is not None and not isinstance(value,bool) and INTEGER_GOLD.fullmatch(str(value).strip()) is not None

def pre_truncation_answer_present(text):
    """Whether the frozen nonempty complete-box marker occurs before the cut."""
    return PRE_TRUNCATION_ANSWER.search(str(text or '')) is not None

def locked():
    data=json.loads((AUDIT/'repos.lock.json').read_text())
    return {r['name']:r for r in data['repositories']}

def check_locks(entries):
    for name,row in entries.items():
        repo=REPOS/name
        if not repo.is_dir(): raise RuntimeError(f'missing locked checkout: {name}')
        head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        if head != row['sha']: raise RuntimeError(f'{name}: HEAD {head} != {row["sha"]}')

def load_fixtures(seed):
    sys.path.insert(0,str(TRUNCSRC))
    from trunccheck import generate_synthetic_fixtures, load_real_fixtures
    real=load_real_fixtures(FIXTURE)
    synth=generate_synthetic_fixtures(seed)
    fixtures=[f for f in real if f.kind=='truncated']+list(synth)+[f for f in real if f.kind=='control_correct']
    out=[]
    for f in fixtures:
        row=f.to_dict(); row.update(dict(f.metadata)); row['output_tokens']=int(row.get('output_tokens') or 4096)
        row['control_gold_eligible']=bool(f.kind=='control_correct' and control_gold_eligible(row))
        row['pre_truncation_answer_present']=(pre_truncation_answer_present(row.get('text')) if row.get('stratum')=='real_truncated' else None)
        out.append(row)
    return out

def write_jsonl(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='\n') as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n')

def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as f:return [json.loads(x) for x in f if x.strip()]

def applicability():
    with (AUDIT/'applicability.csv').open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def run_once(outdir,seed,require_locked):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    entries=locked()
    if require_locked: check_locks(entries)
    fixtures=load_fixtures(seed)
    input_path=outdir/'adapter_input.jsonl';write_jsonl(input_path,fixtures)
    app=applicability(); all_results=[]
    fixture_by_id={r['fixture_id']:r for r in fixtures}
    for config in app:
        target=config['target']; pipeline=config['pipeline_id']; python=PYTHONS[target]; adapter=AUDIT/'adapters'/config['adapter_file']
        raw=outdir/f'{pipeline}.jsonl'
        if not python.is_file():
            adapter_rows=[{'fixture_id':f['fixture_id'],'adapter_status':'install_failed','status_reason':f'missing interpreter {python}','extracted_answer':None,'native_correct':None,'exception_class':'','exception_message':'','swallowed_error_observed':None,'swallowed_error_detail':''} for f in fixtures]
        elif not adapter.is_file():
            adapter_rows=[{'fixture_id':f['fixture_id'],'adapter_status':'not_runnable','status_reason':f'missing adapter {adapter.name}','extracted_answer':None,'native_correct':None,'exception_class':'','exception_message':'','swallowed_error_observed':None,'swallowed_error_detail':''} for f in fixtures]
        else:
            env=os.environ.copy();env['PYTHONHASHSEED']='0';env.pop('OPENAI_API_KEY',None);env.pop('ANTHROPIC_API_KEY',None)
            cmd=[str(python),str(adapter),'--input',str(input_path),'--output',str(raw),'--repo',str(REPOS/target)]
            try:
                proc=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=1200)
                if proc.returncode:
                    reason=f'adapter exit {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:500]}'
                    adapter_rows=[{'fixture_id':f['fixture_id'],'adapter_status':'not_runnable','status_reason':reason,'extracted_answer':None,'native_correct':None,'exception_class':'','exception_message':'','swallowed_error_observed':None,'swallowed_error_detail':''} for f in fixtures]
                else: adapter_rows=read_jsonl(raw)
            except subprocess.TimeoutExpired:
                adapter_rows=[{'fixture_id':f['fixture_id'],'adapter_status':'not_runnable','status_reason':'adapter aggregate timeout 1200s','extracted_answer':None,'native_correct':None,'exception_class':'','exception_message':'','swallowed_error_observed':None,'swallowed_error_detail':''} for f in fixtures]
        got={r['fixture_id']:r for r in adapter_rows}
        if set(got)!=set(fixture_by_id): raise RuntimeError(f'{pipeline}: incomplete adapter coverage')
        for fixture in fixtures:
            result=got[fixture['fixture_id']]; status=result.get('adapter_status','ok')
            extracted=result.get('extracted_answer')
            if status!='ok': returned=None
            elif 'answer_returned' in result: returned=parsebool(result.get('answer_returned'))
            else: returned=bool(extracted is not None and str(extracted).strip())
            answer_is_numeric=(any(char.isdigit() for char in str(extracted)) if returned is True else None)
            all_results.append({
              'target':target,'pipeline_id':pipeline,'repository_sha':entries[target]['sha'],'fixture_id':fixture['fixture_id'],
              'kind':fixture['kind'],'stratum':fixture['stratum'],'shape':fixture.get('shape') or '',
              'dataset':fixture.get('dataset') or '','problem_idx':fixture.get('problem_idx') if fixture.get('problem_idx') is not None else '',
              'text_empty':boolstr(not bool(fixture.get('text'))),
              'control_gold_eligible':boolstr(fixture.get('control_gold_eligible')),
              'pre_truncation_answer_present':boolstr(fixture.get('pre_truncation_answer_present')),
              'applicable':boolstr(status!='not_applicable'),'applicability_reason':result.get('status_reason','') if status=='not_applicable' else '',
              'adapter_status':status,'status_reason':result.get('status_reason',''),'extracted_answer':'' if extracted is None else str(extracted),
              'answer_returned':boolstr(returned),'answer_is_numeric':boolstr(answer_is_numeric),'exception_class':result.get('exception_class',''),'exception_message':result.get('exception_message',''),
              'swallowed_error_observed':boolstr(result.get('swallowed_error_observed')),'swallowed_error_detail':result.get('swallowed_error_detail',''),
              'native_correct':boolstr(result.get('native_correct')),'duration_status':'captured_ephemeral',
            })
    write_csv(outdir/'fixture_results.csv',RESULT_COLUMNS,all_results)
    metrics=calculate_metrics(all_results,app)
    write_csv(outdir/'pipeline_metrics.csv',METRIC_COLUMNS,metrics)
    (outdir/'results_table.md').write_text(markdown(metrics,entries,all_results),encoding='utf-8')
    return {name:(outdir/name).read_bytes() for name in OUTPUTS}

def write_csv(path,columns,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows(rows)

def metric(name,stratum,subset,field,measured=True):
    if not measured:return (name,stratum,'','','','not_measured')
    vals=[parsebool(r[field]) is True for r in subset]; n=sum(vals);d=len(vals);pct='' if not d else f'{100*n/d:.6f}'
    return (name,stratum,str(n),str(d),pct,'ok' if d else 'not_applicable')

def calculate_metrics(results,app):
    out=[]
    for config in app:
        target,pipeline=config['target'],config['pipeline_id']; rows=[r for r in results if r['pipeline_id']==pipeline]
        fatal=Counter(r['adapter_status'] for r in rows if r['adapter_status'] not in ('ok','not_applicable'))
        applicable=[r for r in rows if r['adapter_status']=='ok']
        scorer=any(r['native_correct']!='' for r in applicable)
        swallowed=any(r['swallowed_error_observed']!='' for r in applicable)
        controls=[r for r in rows if r['stratum']=='finished_control' and parsebool(r['control_gold_eligible']) is True]
        control_measured=(len(controls)==28 and all(r['adapter_status']=='ok' and r['native_correct']!='' for r in controls))
        control_failed=bool(applicable) and (not control_measured or any(parsebool(r['native_correct']) is not True for r in controls))
        real=[r for r in applicable if r['stratum']=='real_truncated']
        if config['headline_eligible']!='true': status='wrong_task_dispatch'
        elif not applicable: status=(fatal.most_common(1)[0][0] if fatal else 'not_applicable')
        elif len(real)<MINIMUM_REAL_N: status='insufficient_power'
        elif control_failed: status='control_disqualified'
        else: status='ok'
        groups={
                'real':real,
                'real_pre_answer':[r for r in real if parsebool(r['pre_truncation_answer_present']) is True],
                'real_no_pre_answer':[r for r in real if parsebool(r['pre_truncation_answer_present']) is False],
                'synthetic':[r for r in applicable if r['stratum']=='synthetic_truncated']}
        m=[]
        for label,subset in groups.items():
            answer_measured=any(r['answer_returned']!='' for r in subset)
            m += [metric('answer_returned_after_truncation_pct',label,subset,'answer_returned',answer_measured),metric('crash_pct',label,subset,'exception_class')]
            # exception_class isn't bool: recompute crash.
            crash_n=sum(bool(r['exception_class']) for r in subset);m[-1]=('crash_pct',label,str(crash_n),str(len(subset)),f'{100*crash_n/len(subset):.6f}' if subset else '','ok' if subset else 'not_applicable')
            m += [metric('swallowed_error_pct',label,subset,'swallowed_error_observed',swallowed),metric('accidental_correct_pct',label,subset,'native_correct',scorer)]
            returned=[r for r in subset if parsebool(r['answer_returned']) is True]
            m += [metric('answer_is_numeric_pct',label,returned,'answer_is_numeric',answer_measured)]
        m += [metric('control_pass_pct','control',controls,'native_correct',control_measured)]
        for name,label,n,d,pct,mstatus in m:
            out.append({'target':target,'pipeline_id':pipeline,'pipeline_status':status,'metric':name,'stratum':label,'numerator':n,'denominator':d,'percent':pct,'metric_status':mstatus})
    return out

def format_metric(index,pipeline,name,stratum):
    r=index.get((pipeline,name,stratum))
    if not r or r['metric_status']!='ok':return '`not_measured`' if r and r['metric_status']=='not_measured' else '`not_applicable`'
    return f"{r['numerator']}/{r['denominator']} ({r['percent']}%)"

def markdown(metrics,entries,results):
    idx={(r['pipeline_id'],r['metric'],r['stratum']):r for r in metrics};status={r['pipeline_id']:r['pipeline_status'] for r in metrics}
    app=applicability()
    lines=['# Executable truncation diagnostic','',
      'This executes pinned post-generation callables in isolation. It is not end-to-end harness evaluation and performs no generation. Real and constructed synthetic rows are reported in separate tables and never share a denominator.','',
      '## Limitations','',
      'The public corpus is found data, not a probability sample. Pipelines with identical applicable fixture sets and identical outputs are one repeated measurement through equivalent fallback behavior, not independent replications. A returned answer is an operational extraction event, not proof that the harness invented text. `insufficient_power` means fewer than 20 applicable real truncated rows; it is descriptive and not headline-eligible.','',
      'The frozen control gate uses exactly the 28 finished-correct rows whose gold matches `^[+-]?\\d+$` (four unique dataset/problem/gold items) for every runnable pipeline. Task-specific applicability is used only for truncated-result reporting.','',
      'For `inspect_evals/aime_last_line_numeric`, the task-matched real control subset is six replicates of one AIME problem (`n_eff=1`); its real truncated result has n=7, five empty texts, and three unique problems. The uniform 28-row cross-pipeline control table does not cure that power limitation.','',
      'The real corpus has 131 truncated generations: 26 contain the frozen nonempty `\\boxed{...}` marker before the cut and 105 do not.','',
      'For lm-eval GSM8K flexible extraction, six of the 111 returned real values contain no digit: `$$` (3), `$.` (2), and `$,` (1). The per-row `answer_is_numeric` field keeps these operational sentinel-like strings visible.','',
      '## Real truncated generations','',
      '| Target | Pipeline | Status | n | n_eff | Empty | Answer returned | Numeric among returned | Accidental correct | Marker present | Marker absent | Uniform controls |',
      '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in app:
        p=r['pipeline_id']
        if r['headline_eligible']!='true': continue
        real=[x for x in results if x['pipeline_id']==p and x['stratum']=='real_truncated' and x['adapter_status']=='ok']
        n_eff=len({(x['dataset'],x['problem_idx']) for x in real})
        empty=sum(parsebool(x['text_empty']) is True for x in real)
        lines.append('| '+' | '.join([r['target'],p,status.get(p,'not_runnable'),str(len(real)),str(n_eff),str(empty),format_metric(idx,p,'answer_returned_after_truncation_pct','real'),format_metric(idx,p,'answer_is_numeric_pct','real'),format_metric(idx,p,'accidental_correct_pct','real'),format_metric(idx,p,'answer_returned_after_truncation_pct','real_pre_answer'),format_metric(idx,p,'answer_returned_after_truncation_pct','real_no_pre_answer'),format_metric(idx,p,'control_pass_pct','control')])+' |')
    lines += ['','Rows marked `control_disqualified`, `insufficient_power`, or non-runnable are retained with explicit real denominators but excluded from headline comparison. `not_measured` means the upstream task path does not expose an extracted-answer value.','',
      '## Constructed synthetic probes','',
      '**Constructed probes only. These strings were authored to exercise parser shapes and are not model generations, prevalence estimates, or evidence of real-world correctness.**','',
      '| Target | Pipeline | n | Answer returned | Accidental correct | Crash |','|---|---|---:|---:|---:|---:|']
    for r in app:
        p=r['pipeline_id']
        if r['headline_eligible']!='true': continue
        synthetic=[x for x in results if x['pipeline_id']==p and x['stratum']=='synthetic_truncated' and x['adapter_status']=='ok']
        lines.append('| '+' | '.join([r['target'],p,str(len(synthetic)),format_metric(idx,p,'answer_returned_after_truncation_pct','synthetic'),format_metric(idx,p,'accidental_correct_pct','synthetic'),format_metric(idx,p,'crash_pct','synthetic')])+' |')
    demoted=[r for r in app if r['headline_eligible']!='true']
    lines += ['','## Demoted wrong-dispatch diagnostics','']
    for r in demoted:
        lines.append(f"- `{r['pipeline_id']}` is retained for audit history but is `wrong_task_dispatch`: {r['exclusion_reason']}")
    lines += ['','## Headline-eligible real-data pipeline rows','']
    eligible=[r for r in app if status.get(r['pipeline_id'])=='ok' and r['headline_eligible']=='true']
    if eligible:
        lines += ['| Target | Pipeline | Answer returned after truncation |','|---|---|---:|']
        for r in eligible:
            p=r['pipeline_id'];lines.append(f"| {r['target']} | {p} | {format_metric(idx,p,'answer_returned_after_truncation_pct','real')} |")
    else:lines.append('None; every runnable scored pipeline failed at least one applicable finished-correct control or remained not measurable.')
    lines += ['','## Locked repositories','']
    for r in app:lines.append(f"- `{r['target']}` at `{entries[r['target']]['sha']}`; `{r['callable']}`")
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--locked',action='store_true');p.add_argument('--seed',type=int,default=1729);p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.seed!=1729:raise SystemExit('locked audit requires seed 1729')
    if args.check:
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            first=run_once(a,args.seed,args.locked);second=run_once(b,args.seed,args.locked)
            for name in OUTPUTS:
                if first[name]!=second[name]:raise SystemExit(f'nondeterministic output: {name}')
                committed=(AUDIT/name).read_bytes()
                if first[name]!=committed:raise SystemExit(f'committed output differs: {name}')
        expected=(AUDIT/'synthetic_fixtures.jsonl').read_bytes()
        sys.path.insert(0,str(TRUNCSRC));from trunccheck import fixtures_to_jsonl,generate_synthetic_fixtures
        if fixtures_to_jsonl(generate_synthetic_fixtures(args.seed))!=expected:raise SystemExit('synthetic fixture differs')
        print('locked executable audit reproduced twice and matches committed outputs')
    else:
        with tempfile.TemporaryDirectory() as directory:
            generated=run_once(directory,args.seed,args.locked)
            for name,data in generated.items(): (AUDIT/name).write_bytes(data)
        sys.path.insert(0,str(TRUNCSRC));from trunccheck import fixtures_to_jsonl,generate_synthetic_fixtures
        (AUDIT/'synthetic_fixtures.jsonl').write_bytes(fixtures_to_jsonl(generate_synthetic_fixtures(args.seed)))
        print('wrote '+', '.join(OUTPUTS))
if __name__=='__main__':main()
