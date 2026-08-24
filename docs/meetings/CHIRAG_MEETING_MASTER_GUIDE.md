# Chirag meeting master guide

**Updated:** 2026-08-23

Use the [live meeting runner](chirag_meeting_master.html) during the call. This Markdown file is the printable backup.

## The meeting goal

Chirag asked for a table of benchmarks that provide:

- correctness for every question;
- token information for every response;
- a way to tell when a response exhausted its output allowance;
- a source link; and
- the number of problems.

Leave the meeting with:

1. confirmation that the table answers his assignment;
2. agreement on what the public archives can support;
3. confirmation of the adjusted versus unadjusted censoring comparison; and
4. one next deliverable, owner, and due date.

## The 30-minute path

| Time | Stage | Outcome |
|---|---|---|
| 0 to 3 minutes | Frame the meeting | Chirag understands what you completed. |
| 3 to 10 minutes | Show the table | He sees what MathArena and HELM provide. |
| 10 to 15 minutes | Answer the assignment | You give a clear yes and a qualified partly. |
| 15 to 23 minutes | Explain censoring | You confirm the comparison he intended. |
| 23 to 27 minutes | Agree on next work | One artifact gets an owner and date. |
| 27 to 30 minutes | Read it back | No open question is recorded as a decision. |

## 0 to 3 minutes: frame the meeting

Say:

> I made the benchmark table you asked for and checked the public files at the question level. I can show which archives give us correctness, token use, and a usable sign that a response reached its limit. After that, I want to make sure I understand the censoring comparison you had in mind and agree on the next thing I should build.

Use this one-sentence research question:

> When two models reach similar accuracy on the same questions, how many output tokens does each need, and how does accounting for cut-off responses change that comparison?

Move on once Chirag understands that you completed the table and want his feedback on it.

## 3 to 10 minutes: show the table

Open [the benchmark table](benchmark_table_for_chirag.html).

### MathArena

- 123 competition-math questions across HMMT 2025, HMMT 2026, AIME 2026, and BRUMO 2025.
- Per-question source-native grades are available.
- Output-token counts are available.
- Requested caps and finish reasons are absent, so censoring is inferred.

### HELM GPQA

- 446 science questions per reviewed model run.
- Per-question source-native grades are available.
- Every reviewed run requested 14,096 output tokens.
- Only Gemini has usable finish labels: 42 length and 404 stop.
- Token fields are not proved comparable across providers.

Brief clarification:

> HELM here means Stanford's Holistic Evaluation of Language Models, specifically its GPQA evaluation. It is not Humanity's Last Exam.

Conclude with:

> Both archives support question-level accuracy. MathArena has broader model coverage but inferred censoring. HELM Gemini gives us one cleaner observed censoring example. Neither archive alone proves that raising the cap would have made a wrong answer correct.

## 10 to 15 minutes: answer the assignment

### Can we see whether each model got each question right?

Yes. MathArena and the reviewed HELM files contain a source-native grade for each archived model-question response.

### Can we tell whether token exhaustion caused a wrong answer?

Only partly. HELM Gemini shows that a response was wrong and length-stopped. That does not prove the cap caused the error. MathArena does not publish a finish reason.

### What the table means

Say:

> From the public archives, we can recover per-question correctness and output amount. Most archives do not record whether the output limit stopped a response. The Gemini GPQA run is the one exception, with 42 length stops. We can use these archives to select questions and describe the relationship between correctness and output amount, but we cannot use them to prove that a token limit caused an error. In our experiment, we will reuse suitable questions, assign different output limits, and record the limit, token use, stopping reason, and correctness for every attempt. We can then test whether more room reduces cutoffs and improves answer completion and accuracy.

If Chirag asks how you checked, say:

> I built one sanitized row for every expected benchmark, model, and question combination. Missing rows stay visible instead of disappearing from the denominator. HMMT 2025, HMMT 2026, and HELM are covered now. AIME and BRUMO still need the same exact-source check.

The audit contains:

- 1,920 HMMT 2025 rows;
- 990 expected HMMT 2026 rows, including 11 visible gaps;
- 1,338 HELM GPQA rows; and
- 4,248 question-by-model cells in total.

## 15 to 23 minutes: explain censoring

Use this simple structure:

1. For a completed response, we observe the full output length and score.
2. For a response cut off at cap C, we know only that its natural length would exceed C.
3. A censoring estimator uses that lower bound. It does not invent the missing answer.

Say:

> The performance axis should stay as observed accuracy. The unadjusted efficiency curve would use the raw observed token summary. The adjusted curve would use a censoring-aware length summary. Because HELM uses one common 14,096-token cap, the public archive cannot tell us how far the 42 cut-off responses would have continued without an added tail model or data from other caps.

Ask one main question:

> Is that the adjusted-versus-unadjusted comparison you meant?

Only if Chirag wants to settle the statistical method during this call, ask:

- Should the adjusted result stop at a range supported by the data, or use a model that extrapolates beyond 14,096 tokens?
- Does "same performance" mean matching the models' overall accuracy across settings?
- What minimum number of shared questions and length stops would he consider credible?

## 23 to 27 minutes: agree on next work

Recommend:

> I think I should finish the exact-source audit for AIME and BRUMO so the full MathArena table is defensible. After that, I can draft the data schema for a controlled Model A versus Model B comparison.

Ask:

> Does this table answer what you wanted? If it does, should I finish the remaining source audit next, or would the controlled data schema be more useful for our next meeting?

If Chirag wants an analysis example first, offer a HELM Gemini identification check. It would compare completed-only and capped-at-limit summaries, then show what remains unknown beyond the common cap.

Write down:

- Next deliverable: ________________________________________________
- Owner: __________________________________________________________
- Due date: _______________________________________________________

Do not promise paid or confirmatory collection. The design and execution gates remain unfinished.

## 27 to 30 minutes: read it back

Say:

> Let me read back what I wrote so I do not turn an open question into a decision later. We agreed that [read the table and censoring decision]. My next deliverable is [read it] by [date]. Is that accurate, and when should we review it?

Before leaving, confirm:

- the free Slack workspace and table sharing;
- your parents have Chirag's email;
- the next deliverable, owner, and date; and
- the next meeting time.

## Backup facts

Use these only if Chirag asks.

| Number | Meaning |
|---:|---|
| 123 | MathArena questions across four competitions |
| 446 | HELM GPQA questions per reviewed model run |
| 42 of 446 | Gemini responses labeled length; all scored wrong |
| 4,248 | Question-by-model cells in the current audit |
| 427 | MathArena generations at or near an apparent cap in the separate observational study |
| 15 of 17 | Selected observational groups with zero accuracy among inferred cap rows or observed length stops |

Additional boundaries:

- Chirag already approved including HMMT-2026 items 31 to 33 for the current scope.
- HMMT-2026 question 25 has two archived text versions.
- AIME and BRUMO still need the same exact-source audit.
- The four MathArena competitions should not be pooled automatically.
- Save model selection, providers, caps, repeats, power, runner work, and preregistration for a later design discussion unless Chirag asks.

## Before the call

1. Open the live runner and benchmark table.
2. Test your microphone and screen sharing.
3. Read the opening and censoring script aloud once.
4. Remember 123, 446, 42 of 446, and 4,248.
5. Create the free Slack workspace and share Chirag's email with your parents.
