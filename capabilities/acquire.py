#!/usr/bin/env python3
"""Acquire the five HELM-Capabilities source datasets from their original sources.

Emits, under an output directory (default: the directory containing this script):
  sources_manifest.json          pinned URL + revision + bytes + sha256 for every input and output
  mmlu_pro.jsonl                 12,032 test + 70 validation rows   (TIGER-Lab/MMLU-Pro)
  gpqa_main.jsonl                448 SANITIZED rows (no question text; hashes only)
  restricted_local/gpqa_main.RESTRICTED.jsonl   448 full rows — NEVER commit or share
  ifeval.jsonl                   541 rows                            (google/IFEval)
  wildbench_v2.jsonl             1,024 rows                          (allenai/WildBench, config v2)
  omni_math.jsonl                all rows of test.jsonl              (KbsdJames/Omni-MATH)

Row schema: source-item-v1 (one row per source item, exact source text, no model-facing
wrapper). grading.kind is a tagged union because not every benchmark has a gold answer:
  gold_choice             MMLU-Pro, GPQA        (correct option)
  gold_answer             Omni-MATH             (answer string)
  verifiable_instructions IFEval                (instruction_id_list + kwargs, graded by code)
  judge_checklist         WildBench             (checklist, graded by LLM judge)

GPQA access conditions: question text must never be committed to git, pasted into
shared docs, or published. The committed gpqa_main.jsonl therefore nulls all content
fields and keeps only IDs, domains, and SHA-256 hashes; the full rows go to
restricted_local/ (gitignored). full_row_sha256 is identical in both files, which
proves the sanitized skeleton corresponds to the withheld text.

Run:  python3 acquire.py [--out DIR]
Deps: pip install huggingface_hub pandas pyarrow
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

# ---------------------------------------------------------------- pinned sources

HF_DATASETS = {
    # repo_id: the exact data files we consume (repo-relative paths)
    "TIGER-Lab/MMLU-Pro": ["data/test-00000-of-00001.parquet",
                           "data/validation-00000-of-00001.parquet"],
    "google/IFEval": ["ifeval_input_data.jsonl"],
    "allenai/WildBench": ["v2/test-00000-of-00001.parquet"],
    "KbsdJames/Omni-MATH": ["test.jsonl"],
}

GPQA_GIT_URL = "https://github.com/idavidrein/gpqa.git"
GPQA_COMMIT = "d46dc8d5e01b40bcde0bed6bee68a5de953a58f8"   # matches observational/benchmark_sources_manifest.json
GPQA_ZIP_SHA256 = "461ae7329f15a3e35f8184d2dac24b990f34fdf12f366ca4062d8e6638cd08dc"
GPQA_ZIP_PASSWORD = "deserted-untie-orchid"  # published in the GPQA README to block crawlers, not humans

EXPECTED_COUNTS = {"mmlu_pro": 12102, "gpqa_main": 448, "ifeval": 541, "wildbench_v2": 1024}
# omni_math: card says 4,428; HF viewer reports 4,430 — acquire records the true file count.

# ---------------------------------------------------------------- helpers


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_py(obj):
    """Convert numpy arrays/scalars from parquet into plain JSON-safe Python values."""
    if hasattr(obj, "tolist"):
        return _to_py(obj.tolist())
    if isinstance(obj, dict):
        return {k: _to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_py(v) for v in obj]
    if isinstance(obj, float) and obj != obj:  # NaN
        return None
    return obj


def canonical(obj) -> str:
    return json.dumps(_to_py(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def finish_row(row: dict) -> dict:
    """Add full_row_sha256 over the canonical row (computed before sanitization)."""
    row = dict(row)
    row["full_row_sha256"] = sha256_text(canonical(row))
    return row


def write_jsonl(path: Path, rows: list) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(canonical(r) + "\n")
    return {"path": path.name, "rows": len(rows), "bytes": path.stat().st_size,
            "sha256": sha256_file(path)}


def base_row(dataset, split, source_url, revision, idx, item_id, prompt_text):
    return {
        "schema_version": "source-item-v1",
        "dataset": dataset,
        "split": split,
        "source_url": source_url,
        "source_revision": revision,
        "source_row_index": idx,
        "source_item_id": str(item_id),
        "prompt_text": prompt_text,
        "prompt_sha256": sha256_text(prompt_text) if prompt_text is not None else None,
    }


# ---------------------------------------------------------------- acquisition

def fetch_hf(api, repo_id, files, manifest):
    info = api.dataset_info(repo_id, files_metadata=True)
    revision = info.sha
    meta = {s.rfilename: s for s in info.siblings}
    local = {}
    for rf in files:
        p = Path(hf_hub_download(repo_id, rf, repo_type="dataset", revision=revision))
        digest = sha256_file(p)
        lfs = getattr(meta.get(rf), "lfs", None)
        lfs_sha = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        if lfs_sha and lfs_sha != digest:
            sys.exit(f"HASH MISMATCH {repo_id}/{rf}: computed {digest} != HF-reported {lfs_sha}")
        manifest["inputs"].append({
            "source_id": f"{repo_id.split('/')[-1].lower()}-{Path(rf).name}",
            "role": "question_source",
            "url": f"https://huggingface.co/datasets/{repo_id}/resolve/{revision}/{rf}",
            "revision": revision, "bytes": p.stat().st_size, "sha256": digest,
            "hf_lfs_sha256_match": bool(lfs_sha) or "not_lfs_tracked",
        })
        local[rf] = p
    return revision, local


def build_mmlu_pro(api, manifest, out):
    repo = "TIGER-Lab/MMLU-Pro"
    rev, files = fetch_hf(api, repo, HF_DATASETS[repo], manifest)
    url = f"https://huggingface.co/datasets/{repo}"
    rows = []
    for split, rf in [("test", "data/test-00000-of-00001.parquet"),
                      ("validation", "data/validation-00000-of-00001.parquet")]:
        df = pd.read_parquet(files[rf])
        for idx, r in enumerate(df.itertuples(index=False)):
            options = [str(o) for o in list(r.options)]
            row = base_row("mmlu_pro", split, url, rev, idx, r.question_id, str(r.question))
            row.update({
                "choices": options,
                "grading": {"kind": "gold_choice", "gold": str(r.answer),
                            "gold_index": int(r.answer_index)},
                "license_policy": "open_commit_ok",
                "meta": {"category": str(r.category), "src": str(r.src)},
            })
            assert 0 <= row["grading"]["gold_index"] < len(options)
            assert options and "ABCDEFGHIJ"[row["grading"]["gold_index"]] == row["grading"]["gold"]
            rows.append(finish_row(row))
    return write_jsonl(out / "mmlu_pro.jsonl", rows)


def build_ifeval(api, manifest, out):
    repo = "google/IFEval"
    rev, files = fetch_hf(api, repo, HF_DATASETS[repo], manifest)
    url = f"https://huggingface.co/datasets/{repo}"
    rows = []
    with open(files["ifeval_input_data.jsonl"], encoding="utf-8") as f:
        for idx, line in enumerate(l for l in f if l.strip()):
            r = json.loads(line)
            row = base_row("ifeval", "train", url, rev, idx, r["key"], r["prompt"])
            row.update({
                "choices": None,
                "grading": {"kind": "verifiable_instructions",
                            "instruction_id_list": r["instruction_id_list"],
                            "kwargs": r["kwargs"]},
                "license_policy": "open_commit_ok",
            })
            assert row["grading"]["instruction_id_list"], f"ifeval row {idx}: no instructions"
            rows.append(finish_row(row))
    return write_jsonl(out / "ifeval.jsonl", rows)


def build_wildbench(api, manifest, out):
    repo = "allenai/WildBench"
    rev, files = fetch_hf(api, repo, HF_DATASETS[repo], manifest)
    url = f"https://huggingface.co/datasets/{repo}"
    df = pd.read_parquet(files["v2/test-00000-of-00001.parquet"])
    rows = []
    for idx, rec in enumerate(df.to_dict("records")):
        convo = json.loads(canonical(rec["conversation_input"]))  # normalize numpy types
        row = base_row("wildbench_v2", "test", url, rev, idx,
                       rec.get("session_id") or rec.get("id") or idx, None)
        row["conversation_input"] = convo          # multi-turn: exact structure, no serialization choice baked in
        row["prompt_sha256"] = sha256_text(canonical(convo))
        checklist = json.loads(canonical(rec.get("checklist")))
        row.update({
            "choices": None,
            "grading": {"kind": "judge_checklist", "checklist": checklist},
            "license_policy": "open_commit_ok",
            "meta": {"primary_tag": str(rec.get("primary_tag"))},
        })
        assert convo, f"wildbench row {idx}: empty conversation"
        rows.append(finish_row(row))
    return write_jsonl(out / "wildbench_v2.jsonl", rows)


def build_omni_math(api, manifest, out):
    repo = "KbsdJames/Omni-MATH"
    rev, files = fetch_hf(api, repo, HF_DATASETS[repo], manifest)
    url = f"https://huggingface.co/datasets/{repo}"
    rows = []
    with open(files["test.jsonl"], encoding="utf-8") as f:
        for idx, line in enumerate(l for l in f if l.strip()):
            r = json.loads(line)
            row = base_row("omni_math", "test", url, rev, idx, idx, r["problem"])
            answer = r.get("answer")
            row.update({
                "choices": None,
                "grading": {"kind": "gold_answer",
                            "gold": None if answer is None else str(answer)},
                "license_policy": "open_commit_ok",
                "meta": {"domain": r.get("domain"), "difficulty": r.get("difficulty"),
                         "source": r.get("source")},
            })
            assert row["prompt_text"].strip(), f"omni_math row {idx}: empty problem"
            rows.append(finish_row(row))
    return write_jsonl(out / "omni_math.jsonl", rows)


def build_gpqa(manifest, out):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "clone", "--quiet", GPQA_GIT_URL, td], check=True)
        subprocess.run(["git", "-C", td, "checkout", "--quiet", GPQA_COMMIT], check=True)
        zip_path = Path(td) / "dataset.zip"
        digest = sha256_file(zip_path)
        if digest != GPQA_ZIP_SHA256:
            sys.exit(f"GPQA dataset.zip hash {digest} != pinned {GPQA_ZIP_SHA256}")
        manifest["inputs"].append({
            "source_id": "gpqa-main-source-archive", "role": "question_source_restricted",
            "url": f"https://raw.githubusercontent.com/idavidrein/gpqa/{GPQA_COMMIT}/dataset.zip",
            "revision": GPQA_COMMIT, "bytes": zip_path.stat().st_size, "sha256": digest,
            "policy": "gpqa_restricted_no_plaintext",
        })
        subprocess.run(["unzip", "-o", "-q", "-P", GPQA_ZIP_PASSWORD, str(zip_path), "-d", td],
                       check=True)
        df = pd.read_csv(Path(td) / "dataset" / "gpqa_main.csv")

    url = f"https://github.com/idavidrein/gpqa/tree/{GPQA_COMMIT}"
    full_rows, sanitized_rows = [], []
    for idx, rec in enumerate(df.to_dict("records")):
        choices = [str(rec["Correct Answer"]), str(rec["Incorrect Answer 1"]),
                   str(rec["Incorrect Answer 2"]), str(rec["Incorrect Answer 3"])]
        row = base_row("gpqa_main", "main", url, GPQA_COMMIT, idx, rec["Record ID"],
                       str(rec["Question"]))
        row.update({
            "choices": choices,  # source order: [correct, inc1, inc2, inc3]; shuffle at wrapper time with a seed
            "grading": {"kind": "gold_choice", "gold": choices[0], "gold_index": 0},
            "license_policy": "restricted_no_plaintext",
            "meta": {"subdomain": str(rec["Subdomain"]),
                     "high_level_domain": str(rec["High-level domain"])},
        })
        full = finish_row(row)
        full_rows.append(full)
        s = dict(full)
        s["prompt_text"] = None
        s["choices"] = None
        s["grading"] = {"kind": "gold_choice", "gold": None, "gold_index": None}
        sanitized_rows.append(s)   # keeps prompt_sha256 + full_row_sha256 of the real content

    restricted = write_jsonl(out / "restricted_local" / "gpqa_main.RESTRICTED.jsonl", full_rows)
    sanitized = write_jsonl(out / "gpqa_main.jsonl", sanitized_rows)
    return sanitized, restricted


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    manifest = {
        "schema_version": "capabilities-source-manifest-v1",
        "purpose": ("Pinned original sources for the five HELM-Capabilities benchmarks and the "
                    "normalized source-item-v1 JSONLs derived from them. Exploratory acquisition "
                    "artifact; authorizes no provider call."),
        "helm_context": {
            "suite": "HELM Capabilities (mmlu_pro, gpqa, ifeval, wildbench, omni_math)",
            "leaderboard": "https://crfm.stanford.edu/helm/capabilities/latest/",
            "launch_post": "https://crfm.stanford.edu/2025/03/20/helm-capabilities.html",
        },
        "inputs": [], "outputs": [],
    }

    print("[1/5] MMLU-Pro ...");   manifest["outputs"].append(build_mmlu_pro(api, manifest, out))
    print("[2/5] Omni-MATH ...");  manifest["outputs"].append(build_omni_math(api, manifest, out))
    print("[3/5] WildBench v2 ..."); manifest["outputs"].append(build_wildbench(api, manifest, out))
    print("[4/5] IFEval ...");     manifest["outputs"].append(build_ifeval(api, manifest, out))
    print("[5/5] GPQA main ...")
    sanitized, restricted = build_gpqa(manifest, out)
    manifest["outputs"].append(sanitized)
    manifest["restricted_local_outputs"] = [restricted]

    for o in manifest["outputs"]:
        name = Path(o["path"]).stem
        exp = EXPECTED_COUNTS.get(name)
        status = "OK" if exp is None or exp == o["rows"] else f"MISMATCH expected {exp}"
        print(f"    {o['path']:>22}: {o['rows']:>6} rows  {o['bytes']/1e6:6.1f} MB  {status}")
        if status.startswith("MISMATCH"):
            sys.exit(1)

    mpath = out / "sources_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest -> {mpath}")


if __name__ == "__main__":
    main()
