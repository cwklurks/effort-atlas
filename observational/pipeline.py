#!/usr/bin/env python3
"""REAP observational pipeline — EXPLORATORY. Computes truncation/length metrics
from public eval archives (MathArena parquets, HELM runs). Deterministic: all
statistics are computed here, never by an agent. Cycle agents run this script and
narrate deltas; they do not modify it.
Usage: python3 pipeline.py [--figures]   (expects data/ populated, pinned in hf_manifest.json)
"""
import json, re, sys, glob, os
import pandas as pd
import numpy as np
from scipy import stats as sps

CAP_FRAC = 0.995          # row is "at cap" if output_tokens >= CAP_FRAC * model max
MIN_N = 30                # ignore model series with fewer rows
EFFORT_RE = re.compile(r"\((none|minimal|low|medium|high|xhigh|max)\)\s*$", re.I)

def is_round_cap(v):
    return v % 1000 == 0 or (v & (v - 1) == 0 and v >= 4096)

def matharena_metrics(path):
    df = pd.read_parquet(path, columns=["model_name","output_tokens","correct","parsed_answer"])
    rows = []
    for m, g in df.groupby("model_name"):
        if len(g) < MIN_N: continue
        mx = int(g.output_tokens.max())
        if mx <= 0: continue  # missing token accounting (e.g. K2-Think) — excluded, noted in RESULTS
        at_cap = g[g.output_tokens >= CAP_FRAC*mx]
        below = g[g.output_tokens < CAP_FRAC*mx]
        exact = int((g.output_tokens == mx).sum())
        eff = EFFORT_RE.search(m)
        rows.append(dict(
            dataset=os.path.basename(path).replace(".parquet",""), model=m,
            base_model=EFFORT_RE.sub("", m).strip(), effort=(eff.group(1).lower() if eff else None),
            n=len(g), max_tokens_observed=mx, round_cap=bool(is_round_cap(mx)),
            n_at_cap=len(at_cap), n_exact_max=exact,
            acc_at_cap=(float(at_cap.correct.mean()) if len(at_cap) else None),
            acc_below_cap=(float(below.correct.mean()) if len(below) else None),
            acc_overall=float(g.correct.mean()),
            p10=float(g.output_tokens.quantile(.10)), p50=float(g.output_tokens.median()),
            p90=float(g.output_tokens.quantile(.90)), p99=float(g.output_tokens.quantile(.99)),
            lognorm_mu=float(np.log(g.output_tokens[g.output_tokens>0]).mean()),
            lognorm_sigma=float(np.log(g.output_tokens[g.output_tokens>0]).std()),
        ))
    return pd.DataFrame(rows)

def helm_metrics(helm_dir):
    rows = []
    for f in sorted(glob.glob(f"{helm_dir}/*__scenario_state.json")):
        model = os.path.basename(f).split("__")[0]
        ss = json.load(open(f))
        dp = {d["instance_id"]: d for d in json.load(open(f.replace("scenario_state","display_predictions")))}
        recs = []
        for st in ss["request_states"]:
            iid = st["instance"]["id"]
            comp = st["result"]["completions"][0]
            fr = (comp.get("finish_reason") or {}).get("reason","")
            d = dp.get(iid, {})
            recs.append(dict(iid=iid, finish=fr, mx=st["request"]["max_tokens"],
                out_tok=d.get("stats",{}).get("num_output_tokens"),
                correct=d.get("stats",{}).get("chain_of_thought_correctness")))
        h = pd.DataFrame(recs)
        length_rows = h[h.finish=="length"]; other = h[h.finish!="length"]
        labeled = h.finish.replace("", np.nan).notna().any() and (h.finish != "").any()
        rows.append(dict(dataset="helm_gpqa_cot_v1.15.0", model=model, n=len(h),
            max_tokens_requested=int(h.mx.iloc[0]), finish_labeled=bool((h.finish!="").any()),
            n_finish_length=len(length_rows),
            acc_finish_length=(float(length_rows.correct.mean()) if len(length_rows) else None),
            acc_other=float(other.correct.mean()), acc_overall=float(h.correct.mean()),
            out_p50=(float(h.out_tok.median()) if h.out_tok.notna().any() else None),
            out_p90=(float(h.out_tok.quantile(.90)) if h.out_tok.notna().any() else None)))
    return pd.DataFrame(rows)

def main():
    ma = pd.concat([matharena_metrics(p) for p in sorted(glob.glob("data/*_outputs.parquet"))])
    hm = helm_metrics("data/helm")
    ma.to_parquet("results_matharena.parquet"); hm.to_parquet("results_helm.parquet")
    # dose-response table: base models with >=2 effort levels in a dataset
    eff = ma[ma.effort.notna()]
    dr = eff.groupby(["dataset","base_model"]).filter(lambda g: g.effort.nunique() >= 2)
    dr = dr.sort_values(["dataset","base_model","p50"])
    dr.to_parquet("results_dose_response.parquet")
    print(f"MathArena: {len(ma)} model-series across {ma.dataset.nunique()} datasets; "
          f"{int(ma.n_at_cap.sum())} at-cap rows total")
    print(f"HELM: {len(hm)} runs; labeled: {hm[hm.finish_labeled].model.tolist()}")
    print(f"Dose-response families: {dr.groupby(['dataset','base_model']).ngroups}")
    if "--figures" in sys.argv:
        import figures; figures.make_all(ma, hm, dr)

if __name__ == "__main__":
    main()
