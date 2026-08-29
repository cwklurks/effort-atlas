"""Pilot item selection for the exploratory Inkling length pilot.

Emits *both* candidate selection rules so the human decision (which one to run)
is a one-line switch, not a code change:

  first200       the literal first N rows of the pilot split, by source_row_index
  stratified200  seeded, proportional to a per-dataset stratum, exactly N rows

Selection files are content-free: identifiers, row indices, strata, and hashes.
They never contain prompt text, so they are safe to commit for every dataset,
including GPQA.

    python -m effort_atlas.pilot_select --rule both --seed 20260830 --n 200

This module makes no network or provider call and authorizes none.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from . import ROOT

SELECTION_SCHEMA = "pilot-selection-v1"
DEFAULT_SEED = 20260830
DEFAULT_N = 200
CAPABILITIES_DIR = ROOT / "capabilities"


def _omni_stratum(row: dict) -> str:
    """Omni-MATH domains look like 'Mathematics -> Geometry -> Plane Geometry'.

    The first segment is always 'Mathematics'; the second is the useful stratum.
    Rows with no domain fall into 'unlabeled' rather than being dropped.
    """
    domains = (row.get("meta") or {}).get("domain") or []
    if not domains:
        return "unlabeled"
    parts = [p.strip() for p in str(domains[0]).split("->")]
    return parts[1] if len(parts) > 1 else parts[0]


DATASETS: dict[str, dict] = {
    "mmlu_pro": {
        "file": "mmlu_pro.jsonl",
        "split": "test",
        "stratum_key": "meta.category",
        "stratum": lambda row: row["meta"]["category"],
    },
    "gpqa_main": {
        "file": "gpqa_main.jsonl",
        "split": "main",
        "stratum_key": "meta.high_level_domain",
        "stratum": lambda row: row["meta"]["high_level_domain"],
    },
    "ifeval": {
        "file": "ifeval.jsonl",
        "split": "train",
        "stratum_key": None,  # IFEval carries no category; seeded uniform sample
        "stratum": None,
    },
    "wildbench_v2": {
        "file": "wildbench_v2.jsonl",
        "split": "test",
        "stratum_key": "meta.primary_tag",
        "stratum": lambda row: row["meta"]["primary_tag"],
    },
    "omni_math": {
        "file": "omni_math.jsonl",
        "split": "test",
        "stratum_key": "meta.domain[0] second segment",
        "stratum": _omni_stratum,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _entry(row: dict, stratum: str | None) -> dict:
    return {
        "source_row_index": row["source_row_index"],
        "source_item_id": row["source_item_id"],
        "split": row["split"],
        "stratum": stratum,
        "prompt_sha256": row["prompt_sha256"],
    }


def select_first_n(rows: list[dict], split: str, n: int) -> list[dict]:
    pool = sorted((r for r in rows if r["split"] == split), key=lambda r: r["source_row_index"])
    if len(pool) < n:
        raise ValueError(f"split {split!r} has {len(pool)} rows, fewer than n={n}")
    return [_entry(r, None) for r in pool[:n]]


def largest_remainder(counts: dict[str, int], n: int) -> dict[str, int]:
    """Proportional allocation of n across strata, exactly summing to n.

    Hamilton / largest-remainder rounding. Ties in remainder break on stratum
    name so the allocation is deterministic regardless of dict order.
    """
    total = sum(counts.values())
    if total < n:
        raise ValueError(f"{total} rows available, fewer than n={n}")
    quotas = {k: n * c / total for k, c in counts.items()}
    alloc = {k: int(q) for k, q in quotas.items()}
    remaining = n - sum(alloc.values())
    order = sorted(counts, key=lambda k: (-(quotas[k] - alloc[k]), k))
    for k in order[:remaining]:
        alloc[k] += 1
    # never allocate more than a stratum holds (only possible with tiny strata)
    for k in sorted(alloc):
        if alloc[k] > counts[k]:
            raise ValueError(f"stratum {k!r} allocated {alloc[k]} > available {counts[k]}")
    return alloc


def select_stratified(
    rows: list[dict],
    split: str,
    n: int,
    seed: int,
    dataset: str,
    stratum_fn: Callable[[dict], str] | None,
) -> tuple[list[dict], dict[str, int]]:
    pool = sorted((r for r in rows if r["split"] == split), key=lambda r: r["source_row_index"])
    if stratum_fn is None:
        rng = random.Random(f"{seed}:{dataset}:uniform")
        picked = rng.sample(pool, n)
        picked.sort(key=lambda r: r["source_row_index"])
        return [_entry(r, None) for r in picked], {"uniform": n}
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for r in pool:
        by_stratum[str(stratum_fn(r))].append(r)
    counts = {k: len(v) for k, v in by_stratum.items()}
    alloc = largest_remainder(counts, n)
    picked: list[tuple[dict, str]] = []
    for stratum in sorted(by_stratum):
        k = alloc[stratum]
        if k == 0:
            continue
        rng = random.Random(f"{seed}:{dataset}:{stratum}")
        for r in rng.sample(by_stratum[stratum], k):
            picked.append((r, stratum))
    picked.sort(key=lambda t: t[0]["source_row_index"])
    return [_entry(r, s) for r, s in picked], alloc


def build_selection(
    rule: str,
    *,
    seed: int = DEFAULT_SEED,
    n: int = DEFAULT_N,
    cap_dir: Path = CAPABILITIES_DIR,
    datasets: dict[str, dict] | None = None,
) -> dict:
    datasets = datasets or DATASETS
    manifest = json.loads((cap_dir / "sources_manifest.json").read_text())
    pinned = {o["path"]: o["sha256"] for o in manifest["outputs"]}
    out: dict = {
        "schema_version": SELECTION_SCHEMA,
        "rule": rule,
        "seed": seed if rule == "stratified200" else None,
        "n_per_dataset": n,
        "purpose": (
            "Exploratory Inkling length pilot: which source items would be asked. "
            "Content-free. Authorizes no provider call."
        ),
        "datasets": {},
    }
    for name, spec in datasets.items():
        path = cap_dir / spec["file"]
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run capabilities/acquire.py first")
        digest = sha256_file(path)
        if name in pinned or spec["file"] in pinned:
            expected = pinned.get(spec["file"])
            if expected and digest != expected:
                raise ValueError(
                    f"{spec['file']} sha256 {digest[:12]} != manifest {expected[:12]}; "
                    "refusing to select from unpinned bytes"
                )
        rows = load_rows(path)
        revisions = {r["source_revision"] for r in rows}
        if len(revisions) != 1:
            raise ValueError(f"{name}: mixed source revisions {sorted(revisions)}")
        if rule == "first200":
            items = select_first_n(rows, spec["split"], n)
            # Record which strata the literal rule happens to hit; the
            # "MMLU-Pro first 200 == 100% business" finding lives here.
            by_index = {(r["split"], r["source_row_index"]): r for r in rows}
            for e in items:
                if spec["stratum"]:
                    e["stratum"] = str(spec["stratum"](by_index[(e["split"], e["source_row_index"])]))
            alloc = dict(Counter(e["stratum"] or "uniform" for e in items))
        elif rule == "stratified200":
            items, alloc = select_stratified(rows, spec["split"], n, seed, name, spec["stratum"])
        else:
            raise ValueError(f"unknown rule {rule!r}")
        out["datasets"][name] = {
            "file": spec["file"],
            "file_sha256": digest,
            "source_revision": revisions.pop(),
            "split": spec["split"],
            "stratum_key": spec["stratum_key"],
            "strata_counts": dict(sorted(alloc.items())),
            "n": len(items),
            "items": items,
        }
    out["selection_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return out


def default_filename(rule: str, seed: int) -> str:
    return f"selection_{rule}_v1.json" if rule == "first200" else f"selection_{rule}_seed{seed}_v1.json"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule", choices=["first200", "stratified200", "both"], default="both")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--out-dir", default=str(CAPABILITIES_DIR / "selections"))
    args = ap.parse_args(argv)
    rules = ["first200", "stratified200"] if args.rule == "both" else [args.rule]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for rule in rules:
        sel = build_selection(rule, seed=args.seed, n=args.n)
        path = out_dir / default_filename(rule, args.seed)
        path.write_text(json.dumps(sel, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{rule}: wrote {path.relative_to(ROOT) if path.is_absolute() and ROOT in path.parents else path}")
        for name, d in sel["datasets"].items():
            print(f"  {name:<14} n={d['n']:<4} strata={d['strata_counts']}")


if __name__ == "__main__":
    main()
