# Linux context-bundle build receipt

**Built:** 2026-08-19
**Tool:** Repomix 1.14.0
**Result:** 109 tracked files, 310,632 estimated tokens, 1,266,746 bytes
**SHA-256:** `0c9945a0662251a912ae927257ef4989d11dc1b8da3cec2f2a4fd6a775781573`

Repomix's default security scan reported no suspicious files. The deterministic
pack excludes volatile Git history and Git change-frequency sorting. A second
build from the same tracked inputs produced the same SHA-256. The builder excludes raw
benchmark archives, restricted GPQA content, the full 4,248-row derived table,
generated HTML, fixtures, review transcripts, credentials, and this receipt itself.

Rebuild with:

```sh
./scripts/build_linux_context_pack.sh
```

Then inspect the security result and update this receipt and
`reap/linux_handoff/COPY_MANIFEST.json` if the intentional source context changed.
