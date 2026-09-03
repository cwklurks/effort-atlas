from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_linux_handoff.py"
MANIFEST = ROOT / "reap" / "linux_handoff" / "COPY_MANIFEST.json"
CONTEXT = ROOT / "reap" / "linux_handoff" / "REPO_CONTEXT.xml"
CONTEXT_RECEIPT = ROOT / "reap" / "linux_handoff" / "CONTEXT_BUILD_RECEIPT.md"
CONTEXT_BUILDER = ROOT / "scripts" / "build_linux_context_pack.sh"


class LinuxHandoffTests(unittest.TestCase):
    def run_verifier(
        self, *args: str, root: Path = ROOT
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_checked_in_manifest_verifies_exact_critical_files(self) -> None:
        completed = self.run_verifier()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("verified", completed.stdout)

    def test_verifier_fails_closed_when_a_critical_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reap" / "linux_handoff").mkdir(parents=True)
            target = root / "AGENTS.md"
            target.write_text("original\n")
            manifest = {
                "schema_version": 1,
                "critical_files": [
                    {
                        "path": "AGENTS.md",
                        "sha256": hashlib.sha256(b"original\n").hexdigest(),
                        "bytes": len(b"original\n"),
                        "purpose": "test",
                    }
                ],
            }
            (root / "reap" / "linux_handoff" / "COPY_MANIFEST.json").write_text(
                json.dumps(manifest)
            )
            target.write_text("changed\n")

            completed = self.run_verifier(root=root)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("mismatch for AGENTS.md", completed.stderr)

    def test_manifest_is_sorted_and_contains_only_tracked_regular_files(self) -> None:
        manifest = json.loads(MANIFEST.read_text())
        paths = [entry["path"] for entry in manifest["critical_files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)
            tracked = subprocess.run(
                ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", path],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(tracked.returncode, 0, path)

    def test_verifier_rejects_a_path_that_escapes_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reap" / "linux_handoff").mkdir(parents=True)
            manifest = {
                "schema_version": 1,
                "critical_files": [
                    {
                        "path": "../outside.txt",
                        "sha256": "0" * 64,
                        "bytes": 0,
                        "purpose": "test",
                    }
                ],
            }
            (root / "reap" / "linux_handoff" / "COPY_MANIFEST.json").write_text(
                json.dumps(manifest)
            )

            completed = self.run_verifier(root=root)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsafe manifest path", completed.stderr)

    def test_context_bundle_is_tracked_scanned_and_excludes_large_or_raw_artifacts(
        self,
    ) -> None:
        context = CONTEXT.read_text(encoding="utf-8")
        builder = CONTEXT_BUILDER.read_text(encoding="utf-8")
        self.assertIn("REAP Linux orientation bundle", context)
        self.assertIn("reap/CODEX_BRIEFING.md", context)
        self.assertIn("reap/22_BENCHMARK_PROVENANCE", context)
        self.assertIn("reap/23_BENCHMARK_SCOPE_DECISION", context)
        self.assertNotIn("--no-security-check", builder)
        self.assertNotIn("--include-logs", builder)
        self.assertIn("--no-git-sort-by-changes", builder)
        self.assertNotIn(
            '<file path="observational/benchmark_question_capabilities.jsonl">',
            context,
        )
        self.assertNotIn('<file path="reap/next_chapter/index.html">', context)
        self.assertNotRegex(context, r"sk-or-v1-[A-Za-z0-9_-]{20,}")
        digest = hashlib.sha256(CONTEXT.read_bytes()).hexdigest()
        receipt = CONTEXT_RECEIPT.read_text(encoding="utf-8")
        self.assertIn(digest, receipt)
        self.assertIn("no suspicious files", receipt.lower())

    def test_bootstrap_targets_the_review_branch_over_tailscale_without_secrets(
        self,
    ) -> None:
        bootstrap = (ROOT / "reap" / "linux_handoff" / "BOOTSTRAP_LINUX.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("codex/benchmark-provenance-linux", bootstrap)
        self.assertIn("tailscale ping <linux-tailnet-hostname>", bootstrap)
        self.assertIn("tailscale ssh <linux-user>@<linux-tailnet-hostname>", bootstrap)
        self.assertIn("ssh <linux-user>@<linux-tailnet-hostname>", bootstrap)
        self.assertIn(
            "git bundle create ../effort-atlas.bundle \\\n  refs/heads/codex/benchmark-provenance-linux",
            bootstrap,
        )
        self.assertNotIn("git bundle create ../effort-atlas.bundle --all", bootstrap)
        self.assertIn(
            "uv sync --frozen --python 3.12.8 --extra observational", bootstrap
        )
        self.assertIn(
            "uv venv --no-project --python 3.12.8 .venv/tinker-probe",
            bootstrap,
        )
        self.assertIn(
            "--require-hashes --strict scripts/tinker_probe_requirements.lock",
            bootstrap,
        )
        self.assertIn(
            ".venv/bin/python scripts/acquire_benchmark_sources.py --root benchmark_sources",
            bootstrap,
        )
        self.assertNotIn("acquire_benchmark_sources.py --check", bootstrap)
        self.assertNotIn("codex/reap-governance", bootstrap)
        self.assertNotIn("OPENROUTER_API_KEY", bootstrap)

    def test_fallback_bundle_contains_only_the_review_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "effort-atlas.bundle"
            created = subprocess.run(
                [
                    "git",
                    "-C",
                    str(ROOT),
                    "bundle",
                    "create",
                    str(bundle),
                    "refs/heads/codex/benchmark-provenance-linux",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            listed = subprocess.run(
                ["git", "bundle", "list-heads", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            refs = [line.split(maxsplit=1)[1] for line in listed.stdout.splitlines()]

        self.assertEqual(
            refs,
            ["refs/heads/codex/benchmark-provenance-linux"],
        )


if __name__ == "__main__":
    unittest.main()
