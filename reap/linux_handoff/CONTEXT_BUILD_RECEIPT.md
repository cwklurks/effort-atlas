# Linux context-bundle build receipt

**Built:** 2026-08-19
**Tool:** Repomix 1.14.0
**Result:** 109 tracked files, 311,448 estimated tokens, 1,267,523 bytes
**SHA-256:** `90efeb1713e959160e3b47f396719b83f11382bce3249ec6c3c888eb89554150`

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
