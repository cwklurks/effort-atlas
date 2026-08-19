# Linux context-bundle build receipt

**Built:** 2026-08-19
**Tool:** Repomix 1.14.0
**Result:** 109 tracked files, 310,626 estimated tokens, 1,266,730 bytes
**SHA-256:** `01a5748a9cb90b552b50bc2a5dba5eb82e83c51196b4c9ac3557499829aeaf8e`

Repomix's default security scan reported no suspicious files. The deterministic
pack excludes volatile Git history, and a second build from the same tracked
inputs produced the same SHA-256. The builder deliberately excludes raw
benchmark archives, restricted GPQA content, the full 4,248-row derived table,
generated HTML, fixtures, review transcripts, credentials, and this receipt itself.

Rebuild with:

```sh
./scripts/build_linux_context_pack.sh
```

Then inspect the security result and update this receipt and
`reap/linux_handoff/COPY_MANIFEST.json` if the intentional source context changed.
