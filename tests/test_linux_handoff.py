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


class LinuxHandoffTests(unittest.TestCase):
    def run_verifier(self, *args: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
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


if __name__ == "__main__":
    unittest.main()
