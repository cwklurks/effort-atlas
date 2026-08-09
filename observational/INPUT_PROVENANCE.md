# Observational input provenance status

The checked-in observational report, summary parquets, figures, pipeline, and state
manifest preserve the verified 2026-08-07 outputs. The SHA-256 of `pipeline.py`
matches `state_manifest.json`.

The raw MathArena and HELM inputs are not vendored, and a clean checkout does not
yet have an executable acquisition manifest that verifies every downloaded input
byte. Dataset revisions and HELM run identifiers are recorded in
`state_manifest.json`, but that is provenance metadata rather than proof that a
future download has identical bytes.

Before claiming a clean-checkout rerun, add a separate acquisition/input verifier
that records source identifiers, revisions, local paths, sizes, and SHA-256 digests.
Do not change the protected statistical logic in `pipeline.py` to paper over that
missing acquisition layer.
