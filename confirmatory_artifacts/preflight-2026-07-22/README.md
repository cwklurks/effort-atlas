# Thinking Cut Short confirmatory schedule

This directory freezes the pre-data execution order for the preregistered
confirmatory study.

- Exporter code commit: `c3849ba0ca7119e572f8bcfd4add633ec22f7f5b`
- Original preregistration commit:
  `bc941bf118516cddafc671fcb9acc4607fd7ea33`
- Schedule seed: `20260722`
- Inkling/Together main jobs: 120, comprising 30 items, two requested effort
  levels, two caps, and one response per cell.
- GLM 5.2/Together main jobs: 120 under the same 30-item 2x2 structure.
- Operational smoke jobs: one for Inkling/Together and two for GLM
  5.2/Together. Smoke rows are distinct from confirmatory accuracy rows.

`schedule_manifest.json` records the configuration, dataset, preregistration,
and relevant source-file hashes. It also distinguishes each schedule's
canonical internal digest from the SHA-256 of the emitted file bytes.

All 240 main `job_id` values are unique. The files contain item identifiers and
request conditions only. They contain no benchmark text or answers and make no
API requests.

