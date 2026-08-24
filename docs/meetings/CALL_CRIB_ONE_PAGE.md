# Call crib — one page. This is all you look at.

## ★ The essentials (if you read nothing else)

- **You talk ~15 min of the hour.** Listen first — his new math comes before your pitch. Silence after you speak = him thinking, not judging. Count to three.
- **The experiment in one line:** "Does the effort penalty survive when the model has room to finish? Either answer is the finding."
- **The gap:** low-effort accuracy minus high-effort accuracy, at each wall. Pilot gap at 20k = 13.3 pts. The experiment measures the gap at 49k and compares. Closes → wall. Survives → real. Half-closes → both, reported as measured.
- **Two worlds, never merged:** his wall moves with the prompt → lengths censored → KM counts honestly. Your wall is set by you, thinking varies → answers deleted → rerun bigger. **KM = lengths only. Rerun = scores. Never cross them.**
- **0.453** = 1 − (7/8 × 5/6 × 3/4). Checkpoints are where responses actually finished; capped rows count in denominators until their wall, never as finishers.
- **Must leave with 3 decisions:** format+cycle · his note/authorship/Meta · writing workflow. Everything else → "let me put that in an email."
- **Never say:** "first," "unbiased," "the interaction decomposes the effect," or "overthinking" as a proven claim (say "completed negative scaling").
- **When over your head:** "I verified that numerically but I can't derive it — can you walk me through it?"

---

**Tabs, in order:** ① Google Doc outline · ② PREREGISTRATION.md (GitHub, pinned commit) · ③ amendment file · ④ schedule_manifest.json · ⑤ visual explainer — *only if math comes up, then click, don't lecture*

**Likely shape:** intros (long, let it run) → his new math (LISTEN, take notes) → your 5-min tour (below) → short vs long decision → AI-writing workflow → wrap. You talk ~15 min of the hour, mostly in the tour.

**Must leave with (3):** format + ARR cycle · his note / authorship / Meta review · writing workflow
**Nice to have:** replicates + budget amendment · KM descriptive-only · retitle
**Escape valve for anything:** "Let me put that in an email so we don't rush it."

---

## The only six sentences you have to deliver

1. **Format:** "Before you pick short or long — nothing paid has run yet, the critical path is still offline code and amendments, so pick the format after you see that."
2. **Budget:** "The GLM price went from $0.58 to $1.40 per million input since I preregistered, so I need a dated budget amendment either way."
3. **His note:** "Your note's already on your site — do we fold it in, post it first and cite it, or keep them separate?" *(+ ask: "Does Meta need internal review before we submit?")*
4. **KM:** "In my experiment every response in a cell has the same cap, so below the cap Kaplan-Meier just equals counting — I'd use it as description there, and its real home is your section."
5. **Title:** "I want to retitle to 'completed negative scaling' while the amendment window is still open."
6. **Writing:** "You said the paper can't read as AI-generated — I agree. You and I type every sentence in Overleaf, and I keep the tools on checking, not writing."

---

## Your 5-minute tour (screen-share the Google Doc, scroll as you talk)

1. *(30s — before scrolling)* "The question: when higher effort scores worse, is the thinking actually worse, or are responses getting cut off before they can answer? My hidden 4,096 bug was the second one wearing the first one's clothes."
2. *(45s — scroll to the panel table)* "Same 30 AIME items in a 2×2: two effort levels crossed with two output caps, pinned to one provider. 243 calls, $27 ceiling, one generation per cell."
3. *(45s — stay there)* "The main number is the effort gap at each cap. If the gap shrinks at the big cap and the cut-offs disappear, the wall was faking the decline. If the gap survives with room to finish, that's real, and we report it as completed negative scaling."
4. *(30s — flip to GitHub prereg tab)* "Everything's frozen before any paid call — hypotheses, call order, budget, stop rules, at this commit."
5. *(20s — flip to manifest)* "The call order is generated from a seed and hashed, so nothing can be quietly reordered after seeing results."
6. *(30s — back to Doc)* "Nothing paid has run yet. Before it does: the grader fix, a budget amendment for a price change I caught this week, and probes of both routes near the real caps."

**Then hand it over:** "That's the whole experiment — does it fit short, in your view?"

## The 60-second version (if he just says "tell me about the experiment")

"It's a 2-by-2. Same 30 AIME problems, run four ways: two effort settings — medium and max — crossed with two output walls, 20,000 tokens and about 49,000. Same prompts, same grader, only those two knobs change.

The 20,000 condition reproduces my pilot, where max effort looked 13 points worse but was hitting the wall twice as often. The 49,000 isn't arbitrary — one real max-effort response needed 38,603 tokens to finish, so the big wall is set where even the longest thinking can reach its answer.

The whole result is one comparison: the effort gap at the small wall versus the big wall. If the gap shrinks when there's room — and the cut-off responses are the ones that recover — the 'overthinking' was mostly starvation. If the gap survives when everything finishes, that's real too: completed negative scaling.

Two model routes as separate panels, one generation per item per condition, $27 budget, all preregistered and frozen. Nothing has run yet — first I need the answer-detection fix, a budget amendment for a price change, and probes to confirm the walls behave as requested, because I've been burned by that before."

*(Ten-second version: "Same 30 problems, two effort levels, two walls. Does the effort penalty survive when the model has room to finish? That's the whole experiment.")*

## The short-vs-long moment (right after the tour)

- He decides; your only job is the follow-up. If **short** → "What gets cut — does your framework go deep in the appendix?" and "Is NAACL/COLING via the October cycle okay, or do you want ACL, which is the January cycle?"
- If **long** → "Then timing matters for me: my crunch is November–January, so which sections would you carry through the winter?"

---

## If he asks how you got into this (he will, first 5 min — tell it as a story)

"I was measuring how the reasoning-effort setting changes accuracy on AIME problems, and my results showed this clean pattern where more effort made the model worse. Felt like a real finding. Then I noticed 78 of my responses all had exactly 4,096 completion tokens — the endpoint had been silently cutting them off, and my whole finding was an artifact. So I went looking for how you're supposed to handle measurements that get cut off before they finish, which led me to survival analysis, and then to your note, which was the first thing I found treating generation length as exactly that problem. So I emailed you."

*Lead with the bug, not achievements. It's the origin of the paper and it shows you check your own results.*

## The 0.453 walkthrough (the most likely quiz — say it like this)

"There are eight responses in the toy. Three finished on their own — at 128, 192, and 256 tokens. The other five got cut off by caps, at 128, 192, 256, 256, and 384.

I only care about the three lengths where something actually finished. At 128, all eight are still going and one finishes, so seven out of eight make it past. At 192, only six are left — the one that finished at 128 and the one that got capped at 128 are both out of the picture — and one finishes, so five out of six make it past. At 256 there are four left, and here's the one subtle part: the two responses capped exactly at 256 still count among those four, because they produced 256 full tokens without stopping, so they provably made it that far. One finishes, so three out of four make it past.

Multiply the three fractions: 7/8 times 5/6 times 3/4 is 0.547 — that's the share still generating past 256. So the share finished by 256 is one minus that, 0.453.

The capped responses never count as finishing. They just sit in the denominators while they're visible, then quietly drop out. And that at-256 counting rule matters: do it the other way and the answer moves by about 0.20, which is why the paper has to state the convention."

## Your own work — recite from the bold numbers

**The main point, spoken:** "I sent a max-tokens limit, but the endpoint silently ignored it and used its own 4,096 default. No parse errors, nothing looked broken — all I saw was problems being marked wrong at higher effort. Only when I dug in did I find 78 responses cut at exactly 4,096. That burn is why I started pulling billing receipts on every call — and the receipts then caught the opposite failure on another route, which billed 2.75 times past the cap I requested. Each failure upgraded the checks."

**1 — The bug:** **78** responses at exactly **4,096** · parameter ignored, endpoint default · no length flag, zero parse failures (grader fallback grabbed last number) · fake "declines with effort" curve · invalidated, not repaired.

**2 — The pilot** (30 AIME, Inkling/Together, 20k cap): medium **25/30 = 83.3%**, **4** wall-hits · max **21/30 = 70.0%**, **9** wall-hits · **gap 13.3 pts** · all **13** wall-hits unanswered, scored wrong · thinking ~**6,700** vs ~**12,500** tokens · one rescue finished correct at **38,603** → why big wall = 49,152.

**3 — The audit** (4 routes, 2k probes, receipts): **3** cap-inclusive + honest · Grok/xAI cap-exclusive: **54,969** billed on a 20,000 request = **2.75×**, no length flag · Inkling's behavior documented nowhere, known only by measurement · cost ≈ **2 cents**.

**4 — The design** (prereg July 22, commit bc941bf, $0 spent): Inkling medium/max × **20k/49,152** (120) · GLM high/xhigh × **4,096/32k** (120; 4,096 recreates the bug) · +3 smoke = **243 calls**, **$27** ceiling · seed **20260722**, hashed order, Wilson + 10,000-draw item-clustered bootstrap · 1 dated amendment · still owed: grader fix, budget amendment (**$0.58 → $1.40**/M), passthrough check, near-cap probes.

## Other numbers (glance, don't memorize)

78 responses cut at exactly 4,096 · Grok billed **2.75×** its requested cap · pilot: medium 25/30, max 21/30, all 13 length-stops unanswered · next ARR: **Oct 12 → NAACL/COLING 2027**; ACL = January cycle (my app crunch)

## Quick answers — likely questions, one breath each

- **"What was my note solving?"** → "Real logs come from shared prompt+answer windows, so long answers get chopped and the log records where the wall was, not the real length — counting from logs systematically undercounts long answers."
- **"Why chop a copy?"** → "Real chopped logs have no answer key — the truth is destroyed at the chop. You chopped a copy of data where the truth was kept, so every method's guess could be graded. It earns the method trust before it's used where truth doesn't exist."
- **"Why no mean/median?"** → "Longest observation was capped, so the curve never reaches zero — the tail area is unknowable (no mean) and the curve stalls at 0.547, never crossing 0.5 (no median). Fix: restricted mean, area up to a pre-chosen horizon."
- **"Why not KM on accuracy?"** (THE SEAM) → "A cut response has a true hidden length — 'at least this long' is real information. It has no true hidden answer — never written, nothing to count. Length gets repaired by honest counting; correctness can only be retested with a bigger wall, and that's a new draw, not a continuation."
- **"Just one buggy endpoint?"** (3 LAYERS) → "The 4,096 default was one endpoint. But the audit shows the class is systemic: four routes, two cap behaviors, one billing 2.75× past the request, none documented — switching models re-rolls the dice. And the mechanism — walls delete answers, graders count deletions as wrong, effort hits walls more — is universal. Anecdote, variance, mechanism."
- **"Roles?"** → "You're the statistician and supervisor — censoring framework, Helpfulness, the boundary of the formalism. I'm the experimentalist and first author — harness, audit, runs, empirical sections. The paper is the merger: your framework, my intervention, one wall."
- **"Does independence hold in my Helpfulness data?"** → "Questionable — cap is 512 minus prompt, so if long prompts pair with long answers, being cut is informative, and your KM undershooting truth on both splits leans that way. The fix I understand is stratify by prompt length and average, but I can't derive the conditional estimators — walk me through it?"
- **"One generation per cell isn't an experiment."** → "It's not enough for run-to-run noise and I don't claim it is — it buys a narrow audited pass under $27, reported as an effect size with an interval, never a verdict. If you think the paper needs replicates, I'd rather amend and top up than defend a thin design."

## If he goes over my head (use verbatim)

- "I verified that numerically, but I can't derive it — can you walk me through it?"
- "I know the picture, not the proof. Is the picture enough for this decision?"
- "I don't know that one — I'll write it down and send you an answer tomorrow."

## Close (last 5 min)

Read decisions back out loud → who does what, by when → "Would a 30-minute call every other week work?" → "Thanks for taking this on — I'll keep everything in a state where you can check any number."
