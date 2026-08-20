# Next-chapter report source

`artifact.json` is the canonical, source-backed report input. `index.html` is the
generated, self-contained reader and should not be edited by hand.

Generate and verify the HTML from the repository root with:

```sh
node /Users/connork/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599/skills/build-report/scripts/deliver_portable_artifact.mjs \
  --input reap/next_chapter/artifact.json \
  --output reap/next_chapter/index.html
```

The reader-facing structure maps to the stakeholder-report contract as follows:

1. title;
2. visible Executive Summary;
3. findings with a grouped coverage chart and exact capability tables;
4. recommended next steps;
5. open decisions;
6. caveats and assumptions.

## Chart contract

- **Question:** How complete is question-ID coverage in each pinned archive?
- **Takeaway:** Both HMMT archives contain every source ID; HELM evaluates a
  deliberate 446-row GPQA test split from 448 source rows.
- **Chart family:** Grouped bar chart.
- **Dimensions:** benchmark and coverage series.
- **Measure:** question IDs.
- **Important caveat:** ID coverage does not prove identical prompt bytes,
  identical question text, or comparable token accounting. The adjacent
  narrative and exceptions table carry those qualifications.

No raw benchmark prompt, response, question, answer, or gold text belongs in this
report source.
