# REAP phase status

`phase_status.json` is the single editable source for the project dashboard.
`index.html` is generated and must not be edited by hand.

At each phase checkpoint:

1. Update the phase, workstream, verification, activity, and decision records in
   `phase_status.json`.
2. Keep all safety counters literal and evidence-backed. A zero must never be
   inferred from missing data.
3. Render the page with `python scripts/render_phase_status.py`.
4. Run `./scripts/verify_offline.sh`; it checks that `index.html` is current before
   running the offline test suite.
5. Commit the JSON source and generated HTML together.

The page is self-contained and can be opened directly in a browser. It is a
reporting artifact only and cannot authorize live, paid, smoke, or confirmatory
execution.
