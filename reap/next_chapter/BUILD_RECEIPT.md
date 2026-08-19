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

- `artifact.json`: `76d64cfa0177a1f47b973d1fee3dd9f4f466c8dbd1eaf0380eb4f533efe240b6`
- `index.html`: `8efe03b9e25c763832f4bf939f11e2efe2c4e528feb04beba6d7106b711d9a0f`
- capability table: `b40c4ca819dfbc2c3afc4c7e35251cdb9f3019e7e48add7bc626e84221213f34`
- capability summary: `f16f8dd3c84210763c5bba816da6cdd609db3294d29757dcea4a33a5a7169156`

