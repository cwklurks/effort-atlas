"""Generate the offline question sets.

Standard item schema (data/*.jsonl):
  {"id": str, "domain": str, "prompt": str, "answer": str,
   "grader": "numeric" | "multiple_choice" | "exact_field", "meta": {...}}

Two things are generated here with zero downloads:
  1. extraction — synthetic structured-extraction tasks (the low-reasoning control)
  2. tiny built-in math/knowledge samples so --mock works before any HF fetch
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from . import ROOT, load_config

FIRST = ["Aria", "Ben", "Chloe", "Dmitri", "Elena", "Farid", "Grace", "Hiro",
         "Imani", "Jonas", "Kira", "Liam", "Mona", "Nadia", "Omar", "Priya"]
LAST = ["Anderson", "Baptiste", "Chen", "Dubois", "Eriksen", "Fuentes", "Gupta",
        "Haddad", "Ivanova", "Johansson", "Kowalski", "Larsson", "Moreau",
        "Nakamura", "Okafor", "Petrov"]
ITEMS = ["laptop stand", "USB-C hub", "monitor arm", "webcam", "microphone",
         "desk mat", "keyboard", "trackball", "headset", "docking station"]
CITIES = ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Halifax"]


def gen_extraction(n: int, seed: int) -> list[dict]:
    """Invoices rendered as messy prose; question asks for one exact field."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        inv = f"INV-{rng.randint(2026000, 2026999)}"
        city = rng.choice(CITIES)
        lines = rng.sample(ITEMS, k=rng.randint(3, 6))
        prices = {item: round(rng.uniform(15, 400), 2) for item in lines}
        qty = {item: rng.randint(1, 5) for item in lines}
        total = round(sum(prices[i_] * qty[i_] for i_ in lines), 2)
        body = f"Invoice {inv} — issued to {name}, shipping to {city}.\n"
        for item in lines:
            body += f"  {qty[item]} x {item} @ ${prices[item]:.2f}\n"
        body += f"Invoice total: ${total:.2f}\n"
        # rotate through field types so the task isn't a single pattern
        kind = i % 4
        if kind == 0:
            q, ans = "the invoice number", inv
        elif kind == 1:
            q, ans = "the shipping city", city
        elif kind == 2:
            item = rng.choice(lines)
            q, ans = f"the quantity of '{item}' ordered", str(qty[item])
        else:
            item = rng.choice(lines)
            q, ans = f"the unit price of '{item}' in dollars", f"{prices[item]:.2f}"
        prompt = (
            f"{body}\nFrom the invoice above, extract {q}. "
            "Reply with the value only on the last line, prefixed 'Final answer:'."
        )
        out.append({"id": f"extraction_{i:04d}", "domain": "extraction",
                    "prompt": prompt, "answer": ans, "grader": "exact_field",
                    "meta": {"kind": kind}})
    return out


# Tiny built-in samples so the pipeline runs before any HF fetch. The real
# sweep should use fetch_data.py subsets; these are placeholders, not benchmarks.
SAMPLE_MATH = [
    ("What is the sum of all positive integers n < 100 such that n is divisible "
     "by 7 and n+1 is divisible by 3?", "735"),
    ("A bag has 5 red and 3 blue marbles. Two are drawn without replacement. "
     "What is the probability both are red, as a fraction m/n in lowest terms? "
     "Give m+n.", "19"),
    ("Compute the remainder when 2^100 is divided by 125.", "76"),
    ("How many positive divisors does 8!, factorial of 8, have?", "96"),
    ("What is the smallest positive integer with exactly 12 divisors?", "60"),
]
SAMPLE_KNOWLEDGE = [
    ("Which quantity is conserved due to time-translation symmetry?\n"
     "A) Momentum\nB) Energy\nC) Charge\nD) Angular momentum", "B"),
    ("Which of these is NOT a noble gas?\nA) Argon\nB) Krypton\nC) Radon\nD) Radium", "D"),
    ("The Krebs cycle occurs in which organelle?\n"
     "A) Nucleus\nB) Ribosome\nC) Mitochondrion\nD) Golgi apparatus", "C"),
    ("Which sorting algorithm has the best worst-case time complexity?\n"
     "A) Quicksort\nB) Mergesort\nC) Bubble sort\nD) Insertion sort", "B"),
    ("Which layer of the OSI model handles routing?\n"
     "A) Transport\nB) Data link\nC) Network\nD) Session", "C"),
]


def _sample_items(pairs: list[tuple[str, str]], domain: str, grader: str) -> list[dict]:
    tail = ("\nEnd with the answer on its own last line, prefixed 'Final answer:'."
            if grader == "numeric"
            else "\nEnd with only the letter on the last line, prefixed 'Final answer:'.")
    return [
        {"id": f"{domain}_{i:04d}", "domain": domain, "prompt": q + tail,
         "answer": a, "grader": grader, "meta": {"source": "builtin_sample"}}
        for i, (q, a) in enumerate(pairs)
    ]


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["paths"]["data"]
    data_dir.mkdir(parents=True, exist_ok=True)
    n = cfg["sweep"]["items_per_domain"]
    seed = cfg["sweep"]["seed"]

    sets = {
        "extraction": gen_extraction(n, seed),
        "math": _sample_items(SAMPLE_MATH, "math", "numeric"),
        "knowledge": _sample_items(SAMPLE_KNOWLEDGE, "knowledge", "multiple_choice"),
    }
    for domain, items in sets.items():
        path = data_dir / f"{domain}.jsonl"
        if domain != "extraction" and path.exists():
            print(f"keep existing {path} (probably fetched subset)")
            continue
        with path.open("w") as fh:
            for item in items:
                fh.write(json.dumps(item) + "\n")
        tag = "" if domain == "extraction" else "  [builtin sample — replace via fetch_data.py]"
        print(f"wrote {len(items):>4} items → {path}{tag}")


if __name__ == "__main__":
    main()
