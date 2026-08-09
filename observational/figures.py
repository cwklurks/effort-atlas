"""Figures for the REAP observational study. Palette per repo dataviz conventions."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

INK, INK2, MUT, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"
SURF = "#fcfcfb"
FAM = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
EFF_ORDER = ["low", "medium", "high", "xhigh"]

def style(ax):
    ax.set_facecolor(SURF)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=MUT, labelsize=9)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)

def fig_dumbbell(ma, hm):
    t = ma[(ma.n_at_cap >= 4) & (ma.round_cap)].copy()
    t["label"] = t.model + "  ·  " + t.dataset.str.replace("_outputs", "", regex=False)
    g = hm[hm.model == "google_gemini-3-pro-preview"].iloc[0]
    rows = [("Gemini-3-Pro · HELM GPQA (labeled)", g.acc_other, g.acc_finish_length, int(g.n_finish_length))]
    rows += [(r.label, r.acc_below_cap, r.acc_at_cap, int(r.n_at_cap)) for r in t.itertuples()]
    rows.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(8.6, 0.42 * len(rows) + 1.6), facecolor=SURF)
    style(ax)
    for i, (lab, below, atcap, n) in enumerate(rows):
        ax.plot([atcap, below], [i, i], color=GRID, lw=2, zorder=1)
        ax.scatter([below], [i], s=52, color=BLUE, zorder=3)
        ax.scatter([atcap], [i], s=52, color=ORANGE, zorder=3)
        ax.text(1.015, i, f"n@cap={n}", va="center", fontsize=8, color=MUT, transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8.5, color=INK2)
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("accuracy", color=INK2, fontsize=10)
    ax.set_title("Accuracy below the cap vs at the cap (public leaderboard data)",
                 color=INK, fontsize=11.5, loc="left", pad=14)
    ax.scatter([], [], color=BLUE, label="finished below cap")
    ax.scatter([], [], color=ORANGE, label="at the cap (truncated)")
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig("fig1_at_cap_vs_below.png", dpi=160, facecolor=SURF)

def fig_dose(dr):
    fams = list(dr.groupby(["dataset", "base_model"]).groups)
    fig, ax = plt.subplots(figsize=(7.6, 5.0), facecolor=SURF)
    style(ax); ax.grid(axis="y", color=GRID, lw=0.8); ax.grid(axis="x", visible=False)
    for k, (key, g) in enumerate(dr.groupby(["dataset", "base_model"])):
        g = g.set_index("effort").reindex([e for e in EFF_ORDER if e in g.effort.values]).reset_index()
        x = [EFF_ORDER.index(e) for e in g.effort]
        ax.plot(x, g.p50, "-o", color=FAM[k % 6], lw=2, ms=6)
        ax.annotate(f"{key[1]} · {key[0].replace('_outputs','').replace('_',' ')}",
                    (x[-1], g.p50.iloc[-1]), textcoords="offset points", xytext=(8, 6 if k % 2 else -6),
                    fontsize=8, color=FAM[k % 6], va="center")
    ax.set_yscale("log")
    ax.set_xticks(range(4), EFF_ORDER)
    ax.set_xlim(-0.3, 4.6)
    ax.set_ylabel("median output tokens (log)", color=INK2, fontsize=10)
    ax.set_title("Effort is a length dial: median generation length by requested effort",
                 color=INK, fontsize=12, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig("fig2_effort_dose_response.png", dpi=160, facecolor=SURF)

def make_all(ma, hm, dr):
    fig_dumbbell(ma, hm); fig_dose(dr)
    print("figures written")

if __name__ == "__main__":
    make_all(pd.read_parquet("results_matharena.parquet"),
             pd.read_parquet("results_helm.parquet"),
             pd.read_parquet("results_dose_response.parquet"))
