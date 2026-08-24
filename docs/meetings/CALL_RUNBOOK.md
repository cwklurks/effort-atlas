# Call runbook — Chirag, Monday 11:00 AM

## How to use this

Do NOT read from this on the call. Tonight: read it twice, then rehearse the five explanations in §6 out loud until they come without looking. Tomorrow: keep only §2 (agenda) and §3's "opening lines" visible on a second screen or printed page, and glance, never read. Everything else is preparation, not performance. You drive the agenda; he drives the math.

Before the call, open these tabs in order: (1) the Google Doc outline, (2) PREREGISTRATION.md on GitHub at commit bc941bf, (3) the amendment file, (4) the schedule manifest, (5) the visual explainer (only shared if math comes up). Test screen sharing five minutes early.

One blank you must fill in yourself tonight: your real hours-per-week for the fall (Q16 in §7). Pick the number you can actually hit.

## 1. Live facts verified Sunday

- GLM 5.2 / Together input price is still $1.40/M (vs the prereg's $0.583/M planning rate). Worst-case exposure ≈ $26.95 against the $27.00 ceiling. The budget amendment is needed no matter what.
- ARR calendar: next cycle closes October 12, 2026 and commits to NAACL 2027 / COLING 2027 (commitment Dec 20). ACL 2027 requires the January 2027 cycle — the middle of your application crunch. Chirag said "EMNLP or ACL," so ask directly whether NAACL/COLING via the October cycle is acceptable to him; if he wants ACL specifically, the writing collides with your November–January and the workload split has to reflect that.

## 2. Agenda (60 min)

| # | Min | Item | Who leads |
|---|---|---|---|
| 1 | 0–5 | Open. Who you are, how you got here, thank him for the note. No agenda-reading. | both |
| 2 | 5–13 | His manuscript additions — let him show the math he's adding. Listen, take notes, ask two questions max. | Chirag |
| 3 | 13–20 | The experiment in five minutes, screen-shared (outline → prereg → amendment → manifest). This is the input he said he needs to decide format. | you |
| 4 | 20–27 | Decision 1: short vs long, and which ARR cycle. | Chirag |
| 5 | 27–33 | Decision 2: replicates + the budget amendment. | you |
| 6 | 33–38 | Decision 3: his note (subsume / post first / parallel) + Meta review + author order. | you ask |
| 7 | 38–44 | Decision 4: KM's role in the live study; Helpfulness extension choice; the bridge-subsection ask. | Chirag |
| 8 | 44–50 | Decision 5: title and claim language; new related work. | joint |
| 9 | 50–55 | Decision 6: the AI-writing workflow. | you propose |
| 10 | 55–60 | Close: recap outcomes, owners and dates, cadence, one-sentence thanks. | you |

If the call is 45 min: cut item 3 to three minutes (outline + manifest only), merge items 5 and 6, move Decision 5 to email with a proposed contribution sentence. Never cut item 2 or item 9.

## 3. The six decisions

### Decision 1 — Format and cycle

Opening line: "Before you decide short or long, the honest status is that zero paid calls have run and the whole critical path right now is offline code and amendments, so I'd rather you pick the format after seeing that."

Recommend: ARR short (~4pp), October 12 cycle. Rationale: October lands fully before applications eat November–January, and short matches what can honestly be finished — the semi-synthetic validation plus one 243-call 2×2. One wrinkle to raise: October commits to NAACL/COLING 2027, not ACL — ask if that's acceptable, since ACL means the January cycle in the middle of your crunch.

Pushback he may raise: "Four pages can't hold a survival framework and a factorial." Response: "Then the experiment carries the main text and your formalism goes deep in the appendix — or we go long and you draft the censoring sections while I run the study."

Fallback: long paper at the January cycle with an explicit split — Chirag drafts §§3–4 during Nov–Jan, you write the empirical half over winter break.

Write down: venue cycle = ___; format = ___; back-planned dates for amendments, probes, run, draft, freeze.

### Decision 2 — Replicates and the budget amendment

Opening line: "The GLM input price on Together moved from $0.583 per million when I preregistered to $1.40 now, which pushes my worst case to about $26.95 against a $27.00 ceiling — so I need a dated budget amendment no matter what, and the replicates question rides along with it."

Recommend: keep one generation per cell; one dated amendment that records the price drift, allocates probe margin explicitly, and records the replicates decision. Pushback: "One sample per condition isn't an experiment." Response: "Fair — I report the interaction as an effect size with an interval, never a verdict, and name repeats as the follow-up; if there's ~$30 more available I'll run two."

Fallback: two replicates ≈ $53.50 worst case, needs balance ≈ $56.56 + the amendment (the preflight code refuses replicates without both).

Write down: replicates = 1/2 (funded by ___); amendment dated ___ with new ceiling, probe margin, restated rates; re-freeze of schedule artifacts after amendments land.

### Decision 3 — His manuscript: subsume, post first, or parallel

Opening line: "Your note is already up on your site, so I'd rather ask straight out than guess — do we fold it into the combined paper, post it on its own first and cite it, or keep them separate?"

Recommend: subsume; you first author, him senior (he already offered this — confirm, don't renegotiate). Ask in the same breath: does Meta/MSL require internal review before submission, how long does it take, and what should the affiliation line say?

Pushback: "It's already public — dual submission?" Response: "A PDF on a personal page isn't an archival publication, but let's write down how we describe it and check it against your internal rules before submitting."

Write down: note = ___; author order = ___; Meta review = required?/filed by whom, when; affiliation = ___.

### Decision 4 — KM's role, and the Helpfulness extensions

Opening line: "In my live experiment every response in a cell has the same cap, and below a constant cap Kaplan-Meier gives exactly the same numbers as just counting — so I'd use it as a descriptive summary there, not as the main analysis."

Recommend: live study = KM secondary descriptive only (length distributions below cap, restricted mean at a prespecified horizon, censoring fractions); add the two-regime subsection; add the cap-invariance KS test on common support as a cheap prespecified secondary. Then hand him the Helpfulness choice — stratify+recombine / independent-arm positive control / Peterson bounds / B≥500 resampling — and ask him to write the "scope of the formalism" bridge subsection (competing risks, cure fraction, non-absorbing correctness, cap-conditioned policy).

Pushback: "The censoring estimator should be the paper's method, including live." Response: "It is the method — in your section, where the cap varies; on my rows it would be doing arithmetic it doesn't need, and I'd rather say that than have a reviewer say it."

Write down: live KM = secondary descriptive, horizon τ = ___; KS test yes/no; Helpfulness extension = ___; bridge subsection = Chirag, by ___.

### Decision 5 — Claim language and positioning

Opening line: "I want to retitle from 'genuine overthinking' to 'completed negative scaling,' and cut the contribution list from five things down to two we can actually defend."

Recommend: retitle now via dated amendment (the frozen taxonomy uses the old phrase). Two load-bearing legs: the effort×allowance crossing, and censoring-aware accounting. Position Kaiser et al. (arXiv:2602.09805) as "their completion-rate measure is a censored quantity estimated naively — we refine it." Three papers to absorb: arXiv:2607.21433 (converged 90.3% vs non-converged 6.6% on AIME), arXiv:2604.21083 (GateScope, gateway truncation/billing audits), arXiv:2605.16938 (effort parameter as a ceiling, not a dial). Route verification demoted to methodology.

Pushback: "2605.16938 means your 2×2 crosses a cap with a cap." Response: "That's why I'm checking whether the effort setting reaches Together as a native enum or as a share of max_tokens before spending anything — if it's a share, I report the factorial as conditional and say so."

Write down: title = ___; contribution paragraph agreed (no "first"); who reads/slots the three new papers, by when.

### Decision 6 — The AI-writing workflow

Opening line: "You said the paper can't read as AI-generated, and I agree — so here's what I'd propose: you and I type every sentence of prose ourselves in Overleaf, and I keep the tools on checking rather than writing."

Recommend four rules, written into the README on the call: (1) all prose typed by the two of you in Overleaf; (2) tools confined to literature search, math/code verification, and adversarial review of drafts you already wrote; (3) a disclosure statement in the paper per ACL policy; (4) every number traceable to a repo artifact at a pinned commit.

Pushback: "How do I know a paragraph wasn't generated?" Response: "Overleaf keeps full history — paragraphs get typed, not pasted, and I'll rewrite any section live on a call if you ever want to watch."

Fallback: hard section ownership — he writes §§3–4 end to end, you write §§5–6, abstract/intro drafted live together.

Write down: prose = humans only in Overleaf; tools = search/checking/red-team; disclosure drafted by ___; traceability rule adopted.

## 4. Screen-share choreography

1. Google Doc outline — "This is the structure I'm proposing; thirty seconds per section, stop me wherever you want to argue."
2. PREREGISTRATION.md at commit bc941bf — "Committed before any paid call: the four hypotheses, the 2×2, the $27 ceiling, and the rule that nothing changes after the first valid response."
3. The amendment file — "This is what an amendment looks like: dated, reason stated, written before any data. The window is still open, which is why I want the statistics settled now."
4. schedule_manifest.json — "Seed 20260722, SHA-256 over the prereg, config, datasets, grader code, and both panels' schedules — the call order was fixed before anything ran and you can re-derive it."
5. The visual explainer — only if the math comes up: step through the checkpoints live. "(7/8)(5/6)(3/4) = 0.547, so F = 0.453, and the tie convention alone moves it by 0.20."

## 5. Five things you must not say

1. Any "first" or "nobody has done this." Say: "to our knowledge, we haven't found anyone who does this."
2. "The interaction decomposes the effect" or "measures how much of the decline is starvation." Say: "the measured slope moves when we change the allowance, and the movement tracks responses that stopped with no answer."
3. Any pretense of deriving statistics you can't. The escape hatch: "I verified that numerically, but I can't derive it — can you walk me through it?"
4. Any promise about when the run starts. Eight offline blockers precede the first paid call. Say: "I'll send you the dated checklist; the run starts when it's clear."
5. Overpromised availability for Nov–Jan. Give the real weekly number and where the gaps are.

## 6. Rehearse these five out loud tonight (30 seconds each)

1. The 0.453 walkthrough (Q1 below).
2. Why KM never touches correctness (Q2).
3. Why the mean isn't identified / restricted mean (Q3).
4. What preregistration protects against, in one breath (Q10).
5. The hidden-cap bug story with the fallback-extraction twist (Q11).

## 7. Q&A bank

### Math understanding-checks

**Q1. "Walk me through 0.453."**
"Eight responses. At 128, one finishes out of eight still running, so 7/8 keep going; at 192 it's 5/6; at 256 it's 3/4. Multiply those and 0.547 are still going, so 0.453 have finished by 256." If he pushes: "The one judgment call is that responses capped exactly at 256 still count as at-risk at 256. That alone moves the answer by about 0.20, which is why it has to be stated in the text."

**Q2. "Why not apply Kaplan-Meier to accuracy?"**
"A cut-off response still has a real length I just didn't see. It doesn't have a real answer sitting underneath waiting to be uncovered. Running it again with a bigger cap gives me a new draw, not the rest of that one — so length is censored, correctness is just absent."

**Q3. "Why can't you report the mean length?"**
"The longest thing I observed got cut off, so the curve never reaches zero and I don't know the tail. The mean is the area under that curve, and the part past the end is unknowable — in your toy it's either infinite or about 300 depending on convention. So I'd report the area up to a horizon we pick in advance."

**Q4. "Does independence hold in my Helpfulness setup?"**
"Your cut-off is 512 minus prompt length, so long prompts get cut early — and if long prompts also have long answers, being cut tells you something about the length you're estimating. Your numbers lean that way: KM undershoots the truth on both splits. The fix I understand is estimating inside prompt-length groups and averaging, but I can't derive the conditional estimators — can you walk me through it?"

### Design challenges

**Q5. "One generation per cell — why is that enough?"**
"It isn't enough to measure run-to-run noise, and I don't claim it is. It buys one audited pass over a fixed benchmark, nothing about variability. That's a $27 budget, not a statistical argument. Two draws needs about $56 and an amendment, and I'd do it if you think the paper needs it."

**Q6. "What if 49,152 still truncates?"**
"Then the large-cap arm isn't clean and I say so — I picked 49,152 off one exploratory run that needed 38,603 tokens, so n=1. I report length stops at the big cap right next to the interaction. GLM has the opposite risk: 4,096 may be so tight both small-cap cells bottom out and the comparison dies by construction."

**Q7. "Why medium vs max, not adjacent levels?"**
"That's the contrast where I saw the effect, so it's what I preregistered — but it's also the widest gap, easiest to detect and hardest to interpret. Inkling's default is high and I skip over it. If you think adjacent levels are cleaner, I'd rather change it now than defend it to a referee."

**Q8. "The interaction doesn't tell you how much of the drop was truncation, does it?"**
"No, and I've cut that framing. What I can say: the measured gap moves when I change the allowance, and the movement tracks responses that stopped before answering. And there's a check I owe before spending anything — whether 'max' reaches Together as a real setting or as a percentage of max_tokens. If it's a percentage, my two knobs aren't separate factors."

**Q9. "Is KM doing any work in your live experiment?"**
"Barely, and I want to be upfront about that. With a constant cap nothing is censored below it, so KM is just the plain empirical curve, and the tail above the cap is unobservable. It earns its keep in your setup, where the cut-off moves with the prompt. In mine it's descriptive only."

### Practical

**Q10. "What is preregistration protecting against, plainly?"**
"Me. I already have pilot numbers I like, so if I could pick the grader or the cap after seeing results, I'd find the answer I want and believe it. Writing everything down first, with dated amendments, means anyone can check what was decided before the data existed."

**Q11. "Tell me about the truncation bug."**
"I sent the output limit under the newer parameter name, and the endpoint silently ignored it and fell back to its own 4,096 default. 78 responses got chopped at exactly 4,096 with no length flag, and my grader's fallback grabbed the last number on the page, so there were zero parse failures — nothing looked broken. It produced a clean 'accuracy declines with effort' curve that was entirely an artifact. That's why this project exists."

**Q12. "What did the cap-semantics audit find?"**
"Four routes, receipts on every call. Three kept everything inside the requested cap. The Grok route billed 54,969 completion tokens on a 20,000-token request — 2.75 times what I asked, with no length stop reported. So I stopped treating max_tokens as a spending limit and started gating on receipts."

**Q13. "What did the AI tools do, and what did you do?"**
"I write the protocol, choose the design, decide what counts as evidence, and I own every number. I use models for code, literature search, and adversarial reviews of my own documents — one of those reviews caught my grader bug. If something has my name on it I can explain it out loud, and where I can't, I'll say so instead of bluffing."

### Getting to know you

**Q14. "What do you want out of this?"**
"Mostly to watch how someone who does this professionally decides what's actually claimable — I can't get that from reading papers. And one real paper where I didn't hand-wave anything. If you want to tear into what I've written, that's what I'm here for."

**Q15. "What's your math background?"**
"I'm a high school student. I've done calculus and taught myself the survival material for this project — I can follow the intuition, check things numerically, and catch inconsistencies. I can't derive Greenwood's formula or bootstrap theory, and I'd rather say that now than get caught later. Tell me what to learn and I'll learn it."

**Q16. "How much time can you give this in the fall?"**
"Realistically [YOUR REAL NUMBER] hours a week, more on weekends, with November through January as my application crunch. I'd rather commit low and hit it than overpromise in August. Tell me which pieces are mine and I'll back-plan from the deadline we pick."

## 8. Six questions you ask him

1. "What math are you adding to the draft right now?" — before pitching your edit list; some may already be done.
2. "Does Meta require internal review before we submit, and how long does that take? And how should your affiliation read?" — plus confirm author order explicitly.
3. "Would you write the scope-of-the-formalism subsection — where the length formalism stops and why correctness can't be treated as a survival time?" — the bridge between the halves, in his voice.
4. "How do you want to run the writing — your Overleaf or mine, and who holds the compile?"
5. "For Helpfulness: stratify-and-recombine, an independent censoring arm as a control, or Peterson bounds — which is the simplest version you'd consider sound? And do you know the correlation between prompt length and response length in that corpus?"
6. "If we go short, what gets cut — and is NAACL/COLING via the October cycle acceptable, or do you specifically want ACL, which means the January cycle?"

## 9. Recovery lines (verbatim)

1. "I verified that numerically, but I can't derive it — can you walk me through it?"
2. "I know the picture for that, not the proof. Is the picture enough for the decision we're making right now?"
3. "I don't know that one. Let me write it down and send you an answer tomorrow instead of guessing now."
4. "Can you say that again in slower words? I don't want to nod along to something I can't defend later."

## 10. Closing the call (last 5 minutes)

Read the six "write down" lines back out loud, filled in — ten seconds each; if one is blank, say so and assign who decides it by when. Then owners and dates: yours (grader amendment, budget amendment, effort-passthrough check, runner + gate, frozen analysis, re-freeze, checklist emailed within 24 hours), his (manuscript corrections, Helpfulness choice, bridge subsection, Meta answer, and the Helpfulness facts you need — n per split, censoring rate, tokenizer, how Figure 2's bands were computed). Propose cadence concretely: "Would a thirty-minute call every other week work, with email between, and my notes within a day of each call?" Close with one sentence: "Thanks for taking this on — I'll keep the work in a state where you can check any number in it."
