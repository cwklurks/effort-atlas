"""Fetch small fixed benchmark subsets from Hugging Face → data/*.jsonl.

⚠ Verify these dataset ids still resolve before relying on them (day-1 TODO).
Requires: pip install datasets

Math      → AIME 2025 (30 items, integer answers, hard reasoning)
Knowledge → MMLU-Pro random subset (10-option MC, not gated)
"""

from __future__ import annotations

import json
import random
import string

from . import ROOT, load_config

MATH_TAIL = "\nEnd with the answer on its own last line, prefixed 'Final answer:'."
MC_TAIL = "\nEnd with only the letter on the last line, prefixed 'Final answer:'."


def fetch_math(n: int, seed: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("math-ai/aime25", split="test")  # ← verify id
    rows = list(ds)
    random.Random(seed).shuffle(rows)
    out = []
    for i, row in enumerate(rows[:n]):
        out.append({
            "id": f"math_{i:04d}", "domain": "math",
            "prompt": row["problem"] + MATH_TAIL,
            "answer": str(row["answer"]).strip(),
            "grader": "numeric", "meta": {"source": "math-ai/aime25"},
        })
    return out


def fetch_knowledge(n: int, seed: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")  # ← verify id
    rows = list(ds)
    random.Random(seed).shuffle(rows)
    out = []
    for i, row in enumerate(rows[:n]):
        letters = string.ascii_uppercase
        options = "\n".join(
            f"{letters[j]}) {opt}" for j, opt in enumerate(row["options"])
        )
        out.append({
            "id": f"knowledge_{i:04d}", "domain": "knowledge",
            "prompt": f"{row['question']}\n{options}" + MC_TAIL,
            "answer": letters[row["answer_index"]],
            "grader": "multiple_choice",
            "meta": {"source": "TIGER-Lab/MMLU-Pro", "category": row.get("category")},
        })
    return out


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["paths"]["data"]
    data_dir.mkdir(parents=True, exist_ok=True)
    n, seed = cfg["sweep"]["items_per_domain"], cfg["sweep"]["seed"]

    for name, fn in [("math", fetch_math), ("knowledge", fetch_knowledge)]:
        try:
            items = fn(n, seed)
        except Exception as err:  # noqa: BLE001
            print(f"FAILED {name}: {err}\n  → fix the dataset id or keep builtin samples")
            continue
        path = data_dir / f"{name}.jsonl"
        with path.open("w") as fh:
            for item in items:
                fh.write(json.dumps(item) + "\n")
        print(f"wrote {len(items):>4} items → {path}")


if __name__ == "__main__":
    main()
