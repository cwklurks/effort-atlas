# Linux context-bundle build receipt

**Built:** 2026-08-19
**Tool:** Repomix 1.14.0
**Result:** 109 tracked files, 311,364 estimated tokens, 1,267,217 bytes
**SHA-256:** `6a5b8ede12c5f57a85f5f7004b3e9d4ddd707c29903e684f541e8e06e5cfe43b`

Repomix's default security scan reported no suspicious files. A second build from
the same worktree produced the same SHA-256. The builder deliberately excludes raw
benchmark archives, restricted GPQA content, the full 4,248-row derived table,
generated HTML, fixtures, review transcripts, credentials, and this receipt itself.

Rebuild with:

```sh
./scripts/build_linux_context_pack.sh
```

Then inspect the security result and update this receipt and
`reap/linux_handoff/COPY_MANIFEST.json` if the intentional source context changed.
