# Linux context-bundle build receipt

**Built:** 2026-09-03
**Tool:** Repomix 1.14.0
**Result:** 111 tracked files, 314,157 estimated tokens, 1,282,574 bytes
**SHA-256:** `d1a653b9b0f14c6182973538ac5c626d02e42844fe7bea590b8c2f51d25379cf`

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
