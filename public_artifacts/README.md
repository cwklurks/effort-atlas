# Public evidence artifacts

This directory contains publication-safe, metadata-only derivatives of private
raw evaluation files. Each bundle is produced by
`python -m effort_atlas.public_artifacts` using an explicit field allowlist.

The exporter preserves source order, duplicates, missing values, route IDs,
usage accounting, finish reasons, and billing metadata. It does not copy
prompts, benchmark labels, extracted answers, visible model responses,
reasoning traces, or unstructured error messages. Every private source is
identified by its repository-relative path, byte count, line count, and
SHA-256 digest in the bundle manifest.

The repository's MIT license applies to project code. It does not assert a
license over benchmark content or model outputs, which is why those fields are
not included here.

