# Next-chapter report build receipt

**Built:** 2026-08-19  
**Status:** Portable package and structural verification passed. Browser interaction
verification was unavailable in this environment and is not claimed.

## Command

```sh
node /Users/connork/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599/skills/build-report/scripts/deliver_portable_artifact.mjs \
  --input reap/next_chapter/artifact.json \
  --output reap/next_chapter/index.html
```

## Result

- validation: `passed`
- package: `passed`
- verification: `structural_only`
- blocks: 15
- charts: 1
- tables: 3
- external assets: none

The builder could not find an installed Chromium headless-shell executable. An
attempt to point it at the desktop Chrome binary was not usable in the sandbox, so
the report does not claim viewport, interaction, or source-dialog browser checks.

## SHA-256

- `artifact.json`: `5f2449ae2f0997b4fbe8b599ed51b1a4ce86226ceecac86da2b51284a4300b42`
- `index.html`: `d97eb32d24796a0db0ab6dca9dac64b455d76f2f42e7a6442b4a9982485a1174`
- capability table: `b40c4ca819dfbc2c3afc4c7e35251cdb9f3019e7e48add7bc626e84221213f34`
- capability summary: `14ecd31855bc594b24f1ded8efca2fd0b1e1bbdefee3b7c3d2ca67986b96a82d`
