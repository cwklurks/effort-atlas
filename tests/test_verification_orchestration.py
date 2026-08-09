import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class VerificationOrchestrationTests(unittest.TestCase):
    @staticmethod
    def _fake_python(path, prefix, log):
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                if [ "$1" = "-c" ]; then
                  case "$2" in
                    *sys.prefix*) printf '%s\\n' '{prefix}' ;;
                  esac
                  exit 0
                fi
                printf '%s\\n' "$*" >> '{log}'
                """
            )
        )
        path.chmod(0o755)

    def test_canonical_verifier_requires_both_structurally_separate_suites(self):
        script = Path("scripts/verify_offline.sh").read_text()

        self.assertIn('"$PYTHON_BIN" -m unittest discover -s tests -p \'test_*.py\' -v', script)
        self.assertIn('TINKER_PYTHON="${TINKER_PYTHON:-.venv/tinker-probe/bin/python}"', script)
        self.assertIn('if [ ! -x "$TINKER_PYTHON" ]', script)
        self.assertIn('project and Tinker interpreters must be distinct', script)
        self.assertIn(
            '"$TINKER_PYTHON" -m unittest discover -s tests '
            '-p \'tinker_probe_suite.py\' -v',
            script,
        )

    def test_exact_lock_suite_cannot_match_ordinary_discovery_pattern(self):
        self.assertTrue(Path("tests/tinker_probe_suite.py").is_file())
        self.assertFalse(Path("tests/test_tinker_probe.py").exists())

    def test_canonical_verifier_invokes_both_mandatory_lanes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "calls.log"
            project = root / "project-python"
            tinker = root / "tinker-python"
            self._fake_python(project, root / "project-prefix", log)
            self._fake_python(tinker, root / "tinker-prefix", log)

            result = subprocess.run(
                ["sh", "scripts/verify_offline.sh"],
                env={
                    **os.environ,
                    "PYTHON_BIN": str(project),
                    "TINKER_PYTHON": str(tinker),
                },
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = log.read_text().splitlines()
            self.assertIn(
                "-m unittest discover -s tests -p test_*.py -v", calls
            )
            self.assertIn(
                "-m unittest discover -s tests -p tinker_probe_suite.py -v", calls
            )

    def test_canonical_verifier_fails_when_exact_lane_is_missing_or_not_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "calls.log"
            project = root / "project-python"
            tinker = root / "tinker-python"
            shared_prefix = root / "shared-prefix"
            self._fake_python(project, shared_prefix, log)

            missing = subprocess.run(
                ["sh", "scripts/verify_offline.sh"],
                env={
                    **os.environ,
                    "PYTHON_BIN": str(project),
                    "TINKER_PYTHON": str(tinker),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("missing or not executable", missing.stderr)

            self._fake_python(tinker, shared_prefix, log)
            same = subprocess.run(
                ["sh", "scripts/verify_offline.sh"],
                env={
                    **os.environ,
                    "PYTHON_BIN": str(project),
                    "TINKER_PYTHON": str(tinker),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(same.returncode, 0)
            self.assertIn("must be distinct", same.stderr)


if __name__ == "__main__":
    unittest.main()
