import contextlib
import csv
import gzip
import io
from pathlib import Path
import tempfile
import unittest

from trunccheck import Fixture, fixtures_to_jsonl, generate_synthetic_fixtures, report_to_markdown, results_to_csv, run_check
from trunccheck.cli import import_callable, main
from trunccheck.schemas import Metric, Result


class SchemaTests(unittest.TestCase):
    def test_fixture_schema_validation(self):
        with self.assertRaises(ValueError):
            Fixture("", "truncated", "real_truncated", "", None, True)
        with self.assertRaises(ValueError):
            Fixture("x", "truncated", "finished_control", "", None, True)
        with self.assertRaises(TypeError):
            Fixture("x", "truncated", "real_truncated", None, None, True)
        data = generate_synthetic_fixtures()[0].to_dict()
        data["unknown"] = 1
        with self.assertRaisesRegex(ValueError, "unknown fixture fields"):
            Fixture.from_dict(data)

    def test_result_and_metric_schema_validation(self):
        with self.assertRaises(ValueError):
            Result("x", "truncated", "real_truncated", "answer", True, "Error", "message")
        with self.assertRaises(ValueError):
            Metric("bad", 2, 1, 200.0)
        with self.assertRaises(ValueError):
            Metric("bad", 1, 2, 40.0)


class ReportTests(unittest.TestCase):
    def test_csv_and_markdown_are_deterministic_and_escaped(self):
        fixture = Fixture("quoted", "truncated", "real_truncated", "x", "7", True)
        report = run_check(lambda text: 'answer,"line"\nnext', [fixture], pipeline="dummy")
        csv_one = results_to_csv(report)
        csv_two = results_to_csv(report)
        markdown_one = report_to_markdown(report)
        self.assertEqual(csv_one, csv_two)
        self.assertEqual(markdown_one, report_to_markdown(report))
        row = next(csv.DictReader(io.StringIO(csv_one)))
        self.assertEqual(row["extracted_answer"], 'answer,"line"\nnext')
        self.assertIn("1 | 1 | 100.000000%", markdown_one)
        self.assertTrue(csv_one.endswith("\n"))
        self.assertTrue(markdown_one.endswith("\n"))


class CliTests(unittest.TestCase):
    def test_import_path_requires_callable(self):
        self.assertTrue(callable(import_callable("dummy_callables:extract_last")))
        with self.assertRaises(ValueError):
            import_callable("dummy_callables.extract_last")

    def test_cli_reads_gzip_and_writes_both_reports(self):
        corpus = (
            b'{"kind":"truncated","text":""}\n'
            b'{"kind":"control_correct","text":"Final answer: 7","gold_answer":"7"}\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixtures.jsonl.gz"
            source.write_bytes(gzip.compress(corpus, mtime=0))
            csv_path = Path(directory) / "out.csv"
            md_path = Path(directory) / "out.md"
            result = main([
                "--callable", "dummy_callables:extract_last",
                "--score-callable", "dummy_callables:score_equal",
                "--corpus", str(source),
                "--expected-count", "2",
                "--expected-kind-count", "truncated=1",
                "--expected-kind-count", "control_correct=1",
                "--csv", str(csv_path),
                "--markdown", str(md_path),
            ])
            self.assertEqual(result, 0)
            with csv_path.open(encoding="utf-8", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 2)
            self.assertIn("control_pass_pct", md_path.read_text())

    def test_cli_stdout_is_offline_local_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixtures.jsonl"
            source.write_text('{"kind":"truncated","text":"Final answer: 7","gold_answer":"7"}\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--callable", "dummy_callables:extract_last", "--corpus", str(source)])
            self.assertEqual(result, 0)
            self.assertIn("# trunccheck report", output.getvalue())
