"""Shared non-semantic JSONL marshaling for locked adapter subprocesses."""
from __future__ import annotations
import argparse, json, time, traceback
from pathlib import Path

def arguments():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--repo',required=True)
    return p.parse_args()

def load(path):
    with open(path,encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]

def blank(row,status='ok',reason=''):
    return {'fixture_id':row['fixture_id'],'adapter_status':status,'status_reason':reason,'extracted_answer':None,'native_correct':None,'exception_class':'','exception_message':'','swallowed_error_observed':None,'swallowed_error_detail':''}

def serialize(value):
    if value is None: return None
    if isinstance(value,(str,int,float,bool)): return str(value)
    if isinstance(value,(list,tuple)): return json.dumps([serialize(x) for x in value],ensure_ascii=False,separators=(',',':'))
    if callable(value): return f"{getattr(value, '__module__', '')}.{getattr(value, '__qualname__', getattr(value, '__name__', type(value).__name__))}"
    rendered = str(value)
    if " at 0x" in rendered and rendered.startswith("<") and rendered.endswith(">"):
        return f"<{type(value).__module__}.{type(value).__qualname__}>"
    return rendered

def marshal_math_gold(value):
    """Apply the audit's one non-semantic math-environment wrapper to gold text."""
    gold=str(value)
    if "\\" in gold and "$" not in gold and not gold.startswith((r"\(",r"\[")):
        return f"${gold}$"
    return gold

def run_rows(rows, function):
    out=[]; timings=[]
    for row in rows:
        started=time.perf_counter()
        try:
            result=blank(row); result.update(function(row) or {})
        except Exception as exc:
            result=blank(row);result.update({'exception_class':type(exc).__name__,'exception_message':str(exc).replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r')})
        timings.append({'fixture_id':row['fixture_id'],'duration_ms':round((time.perf_counter()-started)*1000,6)})
        out.append(result)
    return out,timings

def write(path,rows):
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

def main(importer, function_builder):
    args=arguments(); rows=load(args.input)
    try:
        imported=importer(Path(args.repo)); function=function_builder(imported)
        out,timings=run_rows(rows,function)
    except Exception as exc:
        reason=f'{type(exc).__name__}: {str(exc)}'
        out=[blank(row,'import_failed',reason) for row in rows];timings=[]
    write(args.output,out)
    # Timing is captured separately and intentionally excluded from deterministic result artifacts.
    write(args.output+'.timings.jsonl',timings)
