# REAP Linux handoff

This handoff moves the **committed project state**, not a copy of a Mac working
directory. It contains no API key, `.env` file, raw benchmark cache, GPQA question
text, provider response, or paid-study data.

## 1. Transfer the committed branch

On the Mac, first make sure the intended checkpoint is committed and pushed. Do not
put a key in Git or in a chat transcript.

```sh
git status --short
git push origin codex/benchmark-provenance-linux
```

On Linux, clone that exact branch into a new directory:

```sh
git clone --branch codex/benchmark-provenance-linux --single-branch \
  https://github.com/cwklurks/effort-atlas.git effort-atlas
cd effort-atlas
git status --short
git log -1 --oneline
python3 scripts/verify_linux_handoff.py
```

The last command must say that it verified every critical file. If it fails, stop:
do not patch around a hash mismatch. Re-clone or determine which committed change
was intended, then regenerate and commit `COPY_MANIFEST.json` on the source branch.

If a network clone is unavailable, create a Git bundle on the Mac and transfer that
single file by a method you trust:

```sh
git bundle create ../effort-atlas.bundle --all
```

Then on Linux:

```sh
git clone ../effort-atlas.bundle effort-atlas
cd effort-atlas
git switch codex/benchmark-provenance-linux
python3 scripts/verify_linux_handoff.py
```

### Reaching Linux through Tailscale

Tailscale is the secure transport, while Git remains the source of truth. On the
Mac, start the Tailscale app and verify the target before transferring anything:

```sh
tailscale status
tailscale ping <linux-tailnet-hostname>
```

If Tailscale SSH is enabled on the Linux peer, connect with the Linux account name:

```sh
tailscale ssh <linux-user>@<linux-tailnet-hostname>
```

Otherwise use ordinary SSH over the tailnet address:

```sh
ssh <linux-user>@<linux-tailnet-hostname>
```

If the Linux host can reach GitHub, clone the branch there using the command above.
If it cannot, create the Git bundle on the Mac and copy only that bundle over the
tailnet:

```sh
scp ../effort-atlas.bundle <linux-user>@<linux-tailnet-hostname>:~/
```

Do not copy the Mac working directory, `.env` files, shell history, raw benchmark
caches, or credentials. The machine name and Linux username are intentionally left
as placeholders until the peer is positively identified.

## 2. Create the Python environment

The project needs Python 3.12 or later. The examples below suit Ubuntu/Debian, but
they do not assume `apt`, `sudo`, or a specific package manager. Install Python 3.12
and `uv` through your machine's approved method before continuing; this document
does not install either automatically.

```sh
python3 --version
uv --version
uv sync --python 3.12.8 --extra observational
./scripts/verify_offline.sh
```

The last command is offline with respect to model providers. It must pass before
any implementation claim is made. If `uv` cannot obtain exactly 3.12.8 on your
distribution, use another supported 3.12 interpreter and record that difference in
the work log; do not use the legacy Python 3.9 environment as evidence.

## 3. Reacquire public benchmark caches only when needed

Benchmark source files are intentionally not carried in this handoff. They are
public data caches, not committed research artifacts, and GPQA's source text must
not be copied into a general transfer bundle.

Once the benchmark-provenance checkpoint is present on the branch, use its
verification-first downloader from the repository root:

```sh
.venv/bin/python scripts/acquire_benchmark_sources.py --download --root benchmark_sources
.venv/bin/python scripts/acquire_benchmark_sources.py --check --root benchmark_sources
```

That downloader is expected to use only revision-pinned public sources, verify
SHA-256 before accepting a file, and make no provider call. If the script is not
present yet, the provenance checkpoint has not been transferred: do not substitute
ad-hoc downloads or a browser-exported cache.

## 4. Start a new coding session safely

Copy the prompt in [`START_HERE_PROMPT.md`](START_HERE_PROMPT.md) into the new
session. The session must summarize `reap/CODEX_BRIEFING.md` correctly before it is
given a task. `REPO_CONTEXT.xml` is a searchable convenience bundle of tracked,
non-sensitive project context; canonical repository files win if anything ever
differs. Keep secrets outside the repository, use environment variables only
when a later human-approved workflow genuinely needs them, and never run a paid
model or probe call from setup.

## Refresh rule

`COPY_MANIFEST.json` intentionally covers the handoff context, not every source
file in the repository. When a new, committed benchmark-provenance or phase artifact
becomes essential to starting on Linux, add it to the policy in
`scripts/verify_linux_handoff.py`, run the explicit refresh below, inspect the diff,
and commit the policy and refreshed manifest together:

```sh
python3 scripts/verify_linux_handoff.py --write
python3 scripts/verify_linux_handoff.py
git diff -- reap/linux_handoff/COPY_MANIFEST.json scripts/verify_linux_handoff.py
```
