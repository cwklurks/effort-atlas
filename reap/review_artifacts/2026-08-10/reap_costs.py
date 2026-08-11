"""Independent recomputation of REAP Phase 3 generation counts and cost maxima.

Convention tested: conservative planning maximum = every request bills its full
prompt bound as input and its full output cap as output. No caching discounts,
no shared prefill.
"""

M = 1_000_000

def panel(name, items, arms):
    """arms: list of (arm_name, n_efforts, caps_list, n, prompt_bound)"""
    total_gens = 0
    total_prompt = 0
    total_out = 0
    for arm_name, n_eff, caps, n, pb in arms:
        gens = items * n_eff * len(caps) * n
        prompt = gens * pb
        out = items * n_eff * n * sum(caps)
        total_gens += gens
        total_prompt += prompt
        total_out += out
        print(f"  {arm_name}: gens={gens:,}  prompt_bound={prompt:,}  output_bound={out:,}")
    print(f"  TOTAL {name}: gens={total_gens:,}  prompt={total_prompt:,}  output={total_out:,}"
          f"  all_tokens={total_prompt+total_out:,}")
    return total_gens, total_prompt, total_out

print("== Inkling standard, 30 items ==")
ink = panel("Inkling", 30, [
    ("Arm A", 2, [4096, 16384], 20, 8192),
    ("Arm B", 4, [2048, 4096, 8192, 16384, 32768], 8, 8192),
    ("Arm C", 4, [49152], 8, 8192),
])

print("== GPT-OSS-120B standard, 60 items ==")
oss = panel("GPT-OSS-120B", 60, [
    ("Arm A", 2, [4096, 16384], 20, 8192),
    ("Arm B", 4, [2048, 4096, 8192, 12288, 16384], 8, 8192),
    ("Arm C", 4, [20480], 8, 8192),
])

print("== Breadth panel (Nemotron / Qwen), 30 items ==")
br = panel("Breadth", 30, [("Arm A-style", 2, [4096, 16384], 8, 8192)])
print(f"  doc claims prompt bound 7,864,320 and output bound 9,830,400 -> "
      f"{'MATCH' if br[1]==7_864_320 and br[2]==9_830_400 else 'MISMATCH'}")

print("== Terra, 30 items, prompt bound 4096 ==")
terra = panel("Terra", 30, [("Arm A-style", 2, [4096, 16384], 8, 4096)])

# --- Costs reproducible from rates recorded in the Phase 3 doc itself ---
print("\n== OpenAI direct (rates from doc: terra $2/$12, luna $0.2/$1.2, sol $5/$30 per M) ==")
for name, ci, co in [("terra", 2, 12), ("luna", 0.2, 1.2), ("sol", 5, 30)]:
    cost = terra[1] / M * ci + terra[2] / M * co
    print(f"  {name}: ${cost:,.2f}")

print("\n== OpenRouter anchor, 30 items, prompt bound 8192 (rates from doc) ==")
for name, ci, co in [("Baseten", 0.10, 0.50), ("Groq", 0.15, 0.60), ("Cerebras", 0.35, 0.75)]:
    cost = br[1] / M * ci + br[2] / M * co
    print(f"  {name}: ${cost:,.3f}")

# --- Tinker: attempt reproduction from the ONLY recorded repo rates (reap/02, uniform per-token) ---
print("\n== Tinker attempts with reap/02 recorded rates (uniform $/M, dated pre-2026-08-10) ==")
for name, (g, p, o), rate, claimed in [
    ("Inkling", ink, 4.68, 746.09),
    ("GPT-OSS-120B (60 items)", oss, 0.84, 187.03),
]:
    full = (p + o) / M * rate
    cached = (p * 0.2 + o) / M * rate      # cached prefill -80%
    print(f"  {name}: full=${full:,.2f}  cached-prefill=${cached:,.2f}  claimed=${claimed:,.2f}")
    print(f"    implied uniform rate from claim: ${claimed / ((p + o) / M):.4f}/M "
          f"(cached-prefill convention: ${claimed / ((p * 0.2 + o) / M):.4f}/M)")

for name, claimed in [("Nemotron Ultra 550B", 80.78), ("Qwen3.5 397B", 97.32)]:
    p, o = br[1], br[2]
    print(f"  {name}: no repo rate recorded; implied uniform rate ${claimed / ((p + o) / M):.4f}/M, "
          f"implied cached-prefill rate ${claimed / ((p * 0.2 + o) / M):.4f}/M")

print("\n== Portfolio totals as displayed ==")
tot = 746.09 + 187.03 + 80.78 + 97.32
print(f"  746.09+187.03+80.78+97.32 = {tot:.2f}  (doc says 1,111.21)")
print(f"  1,492.18 / 2 = {1492.18/2:.2f}  (doc's 60->30 item halving for Inkling)")
