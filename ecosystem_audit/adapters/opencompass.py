"""Locked OpenCompass GSM8K postprocessing and evaluator adapter."""
from __future__ import annotations
import math, sys
from pathlib import Path
from common import main, serialize

def numeric(value):
    try:return value is not None and not isinstance(value,bool) and math.isfinite(float(str(value).strip().replace(',','')))
    except (TypeError,ValueError):return False

def importer(repo: Path):
    sys.path.insert(0,str(repo.resolve()))
    from opencompass.datasets.gsm8k import Gsm8kEvaluator,gsm8k_postprocess
    return gsm8k_postprocess,Gsm8kEvaluator

def function_builder(imported):
    postprocess,evaluator_class=imported;evaluator=evaluator_class()
    def evaluate(row):
        if not numeric(row.get('gold_answer')):return {'adapter_status':'not_applicable','status_reason':'non-numeric gold_answer'}
        extracted=postprocess(row['text'])
        # NULL is the registered failure sentinel, not an answer.
        answer=None if extracted=='NULL' else serialize(extracted)
        scored=evaluator.score([extracted],[str(row['gold_answer'])])
        return {'extracted_answer':answer,'native_correct':bool(scored['details'][0]['correct'])}
    return evaluate
if __name__=='__main__':main(importer,function_builder)
