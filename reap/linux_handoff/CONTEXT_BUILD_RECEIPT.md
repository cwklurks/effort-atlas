# Linux context-bundle build receipt

**Built:** 2026-08-19  
**Tool:** Repomix 1.14.0  
**Result:** 109 tracked files, 311,030 estimated tokens, 1,266,104 bytes  
**SHA-256:** `4346a117747d93395ddf397ca7b8dffe359ba16b06ca4f7b7ba4cf00ad22fe92`

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
