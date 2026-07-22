# Confirmatory artifacts

This directory contains immutable, prompt-free execution schedules and their
provenance manifests. Schedule artifacts are generated offline from
`config_confirmatory.yaml` and the audited dataset item identifiers. They do
not contain prompts, gold labels, responses, or reasoning traces.

Generating a schedule does not authorize or initiate paid API work.

`preflight-2026-07-22/` preserves the first frozen artifact. The later
`preflight-2026-07-22-amended/` artifact is the execution source of truth after the
pre-data scoring amendment. The request order is unchanged; the later manifest adds
the amendment hash and corrected analyzer provenance.
