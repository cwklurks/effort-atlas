"""Analyze sweep results → effort curves + summary.

  python -m effort_atlas.analyze [results/sweep_xxx.jsonl]

Outputs:
  reports/effort_curves.png     accuracy vs effort, and accuracy vs mean tokens
  reports/summary.csv           per (domain, effort): n, accuracy, CI, tokens, knee
Prints the headline table with 95% Wilson intervals.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import ROOT, load_config  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - half), min(1.0, center + half))


def latest_results(results_dir: Path) -> Path:
    files = sorted(results_dir.glob("sweep_*.jsonl"))
    if not files:
        raise SystemExit("No results found. Run the sweep first.")
    return files[-1]


def effort_ordinal(cfg: dict, effort: object) -> float:
    ordinal = cfg["effort"].get("ordinal", {})
    key = str(effort)
    if key in ordinal:
        return float(ordinal[key])
    return float(effort)


def find_knee(sub: pd.DataFrame) -> object:
    """Lowest effort whose accuracy is within 2pp of this domain's max."""
    best = sub["accuracy"].max()
    ok = sub[sub["accuracy"] >= best - 0.02]
    return ok.sort_values("effort_ordinal").iloc[0]["effort"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", help="JSONL file to analyze")
    ap.add_argument(
        "--config",
        default=None,
        help="configuration file (default: config.yaml)",
    )
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    results_dir = ROOT / cfg["paths"]["results"]
    reports_dir = ROOT / cfg["paths"]["reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)

    path = Path(args.results) if args.results else latest_results(results_dir)
    rows = [json.loads(line) for line in path.open()]
    df = pd.DataFrame(rows)
    if "error" in df.columns:
        n_failed = int(df["error"].notna().sum())
        if n_failed:
            print(f"skipping {n_failed} failed rows (connection errors)")
        df = df[df["error"].isna()]
    # resumed/combined runs can contain the same (item, effort) twice via cache replay
    before = len(df)
    df = df.drop_duplicates(
        subset=["domain", "item_id", "effort"], keep="last"
    )
    if len(df) < before:
        print(f"deduplicated {before - len(df)} replayed rows")
    if df.empty:
        raise SystemExit("No successful rows to analyze.")
    df["effort_ordinal"] = df["effort"].map(
        lambda effort: effort_ordinal(cfg, effort)
    )
    print(f"analyzing {path.name}  ({len(df)} rows, mock={bool(df['mock'].iloc[0])})\n")

    grp = (
        df.groupby(["domain", "effort", "effort_ordinal"], sort=False)
        .agg(n=("correct", "size"), k=("correct", "sum"),
             mean_tokens=("completion_tokens", "mean"),
             mean_latency=("latency_s", "mean"))
        .reset_index()
    )
    grp = grp.sort_values(["domain", "effort_ordinal"])
    grp["accuracy"] = grp["k"] / grp["n"]
    grp[["ci_lo", "ci_hi"]] = grp.apply(
        lambda r: pd.Series(wilson(int(r["k"]), int(r["n"]))), axis=1
    )

    knees = {d: find_knee(sub) for d, sub in grp.groupby("domain")}
    grp["knee_effort"] = grp["domain"].map(knees)
    grp.to_csv(reports_dir / "summary.csv", index=False)

    # headline table
    print(f"{'domain':<12} {'effort':>7} {'acc':>7} {'95% CI':>15} {'tokens':>9}")
    for _, r in grp.iterrows():
        ci = f"[{r['ci_lo']:.2f},{r['ci_hi']:.2f}]"
        effort_label = str(r["effort"])
        print(f"{r['domain']:<12} {effort_label:>7} {r['accuracy']:>6.1%} "
              f"{ci:>15} {r['mean_tokens']:>9,.0f}")
    print("\nknee (lowest effort within 2pp of max accuracy):")
    for d, e in sorted(knees.items()):
        print(f"  {d:<12} effort={e}")

    # charts
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for domain, sub in grp.groupby("domain"):
        sub = sub.sort_values("effort_ordinal")
        yerr = [sub["accuracy"] - sub["ci_lo"], sub["ci_hi"] - sub["accuracy"]]
        axes[0].errorbar(sub["effort_ordinal"], sub["accuracy"], yerr=yerr,
                         marker="o", capsize=3, label=domain)
        axes[1].errorbar(sub["mean_tokens"], sub["accuracy"], yerr=yerr,
                         marker="o", capsize=3, label=domain)
    effort_ticks = (
        grp[["effort", "effort_ordinal"]]
        .drop_duplicates()
        .sort_values("effort_ordinal")
    )
    axes[0].set_xticks(
        effort_ticks["effort_ordinal"],
        [str(effort) for effort in effort_ticks["effort"]],
    )
    axes[0].set_xlabel("thinking effort")
    axes[1].set_xlabel("mean completion tokens")
    axes[1].set_xscale("log")
    for ax in axes:
        ax.set_ylabel("accuracy")
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.3)
        ax.legend()
    src = "MOCK DATA — pipeline test only" if bool(df["mock"].iloc[0]) else \
        f"Inkling via {cfg['provider']['model']}"
    fig.suptitle(f"Effort/performance by domain — {src} (95% Wilson CI)")
    fig.tight_layout()
    out = reports_dir / "effort_curves.png"
    fig.savefig(out, dpi=150)
    print(f"\ncharts → {out}\nsummary → {reports_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
