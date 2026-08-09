import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter

from trunccheck import (
    CorpusValidationError,
    REAL_CORPUS_SHA256,
    SYNTHETIC_SHAPES,
    Fixture,
    fixtures_to_jsonl,
    generate_synthetic_fixtures,
    load_jsonl_fixtures,
    load_real_fixtures,
)


class SyntheticFixtureTests(unittest.TestCase):
    def test_exactly_100_balanced_seeded_fixtures(self):
        fixtures = generate_synthetic_fixtures(1729)
        self.assertEqual(len(fixtures), 100)
        self.assertEqual(Counter(f.shape for f in fixtures), {shape: 20 for shape in SYNTHETIC_SHAPES})
        self.assertTrue(all(f.seed == 1729 and f.truncated for f in fixtures))
        self.assertEqual(len({f.fixture_id for f in fixtures}), 100)

    def test_byte_for_byte_determinism(self):
        first = fixtures_to_jsonl(generate_synthetic_fixtures())
        second = fixtures_to_jsonl(generate_synthetic_fixtures())
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            "80329fcd2cbc3cf0056c813b931e4b20ee1e222649c52058fc9b66b875c5e834",
        )
        self.assertNotEqual(first, fixtures_to_jsonl(generate_synthetic_fixtures(1730)))

    def test_mid_box_is_incomplete(self):
        fixture = next(f for f in generate_synthetic_fixtures() if f.shape == "mid_box")
        self.assertIn(r"\boxed{", fixture.text)
        self.assertFalse(fixture.text.endswith("}"))
        self.assertEqual(fixture.truncation_marker, "cut_mid_box")

    def test_post_final_answer_precedes_cut(self):
        fixture = next(f for f in generate_synthetic_fixtures() if f.shape == "post_final_answer")
        self.assertIn(f"Final answer: {fixture.gold_answer}", fixture.text)
        self.assertTrue(fixture.generation_parameters["final_answer_precedes_cut"])
        self.assertTrue(fixture.text.endswith(" into"))

    def test_seed_validation(self):
        for bad in (-1, 1.5, "1729", True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                generate_synthetic_fixtures(bad)


class LoaderTests(unittest.TestCase):
    def make_corpus(self, data):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "fixtures.jsonl.gz"
        path.write_bytes(gzip.compress(data, mtime=0))
        return directory, path

    def test_gzip_hash_count_empty_text_and_duplicates(self):
        duplicate = b'{"kind":"truncated","text":"","gold_answer":"1"}'
        data = duplicate + b"\n" + duplicate + b'\n{"kind":"control_correct","text":"Final answer: 7","gold_answer":"7"}\n'
        directory, path = self.make_corpus(data)
        self.addCleanup(directory.cleanup)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        fixtures = load_jsonl_fixtures(
            path,
            expected_sha256=digest,
            expected_count=3,
            expected_kind_counts={"truncated": 2, "control_correct": 1},
        )
        self.assertEqual(len(fixtures), 3)
        self.assertEqual(fixtures[0].text, "")
        self.assertNotEqual(fixtures[0].fixture_id, fixtures[1].fixture_id)
        self.assertTrue(fixtures[0].fixture_id.endswith("-001"))
        self.assertTrue(fixtures[1].fixture_id.endswith("-002"))

    def test_gzip_validation_failures(self):
        directory, path = self.make_corpus(b'{"kind":"truncated","text":"x"}\n')
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(CorpusValidationError, "SHA-256 mismatch"):
            load_jsonl_fixtures(path, expected_sha256="0" * 64)
        with self.assertRaisesRegex(CorpusValidationError, "row count mismatch"):
            load_jsonl_fixtures(path, expected_count=2)
        with self.assertRaisesRegex(CorpusValidationError, "kind counts mismatch"):
            load_jsonl_fixtures(path, expected_kind_counts={"truncated": 2})

    def test_corrupt_gzip_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            corrupt = Path(directory) / "bad.jsonl.gz"
            corrupt.write_bytes(b"not gzip")
            with self.assertRaisesRegex(CorpusValidationError, "invalid gzip"):
                load_jsonl_fixtures(corrupt)
            plain = Path(directory) / "bad.jsonl"
            plain.write_text("[]\n")
            with self.assertRaisesRegex(CorpusValidationError, "must be an object"):
                load_jsonl_fixtures(plain)

    def test_native_schema_round_trip(self):
        originals = generate_synthetic_fixtures()[:2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixtures.jsonl"
            path.write_bytes(fixtures_to_jsonl(originals))
            loaded = load_jsonl_fixtures(path)
        self.assertEqual(loaded, originals)

    def test_fixed_real_corpus_when_repository_input_is_present(self):
        corpus = Path(__file__).resolve().parents[2] / "observational" / "real_truncated_fixtures.jsonl.gz"
        if not corpus.exists():
            self.skipTest("repository real corpus is not part of installed package")
        fixtures = load_real_fixtures(corpus)
        self.assertEqual(len(fixtures), 195)
        self.assertEqual(Counter(f.kind for f in fixtures), {"truncated": 131, "control_correct": 64})
        self.assertEqual(sum(f.text == "" for f in fixtures if f.truncated), 12)
        self.assertEqual(hashlib.sha256(corpus.read_bytes()).hexdigest(), REAL_CORPUS_SHA256)
