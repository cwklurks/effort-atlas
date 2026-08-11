from __future__ import annotations

import hashlib
import inspect
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

from effort_atlas import matharena_grading
from effort_atlas.graders import extract_final_answer
from effort_atlas.matharena_grading import (
    MathArenaImportFailed,
    MathArenaPin,
    grade_with_matharena,
)


class FakeMathArena:
    def __init__(self, directory: str) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.source = Path(directory) / "parser.py"
        self.source.write_text(
            """def parse_answer(value):
    CALLS.append(("parse_answer", value))
    return NORMALIZED.get(value), "fake-warning"

def check_answers(left, right):
    CALLS.append(("check_answers", left, right))
    return left is not None and left == right

def forbidden(*args, **kwargs):
    CALLS.append(("forbidden",))
    raise AssertionError("forbidden upstream path was invoked")
"""
        )
        self.module = ModuleType("matharena.parser")
        self.module.__file__ = str(self.source)
        self.module.CALLS = self.calls
        self.module.NORMALIZED = {
            "0.75": ("fraction", 3, 4),
            r"\frac{3}{4}": ("fraction", 3, 4),
            "3/4": ("fraction", 3, 4),
            "4": ("integer", 4),
            r"\sqrt{17}-1": ("radical", 17, -1),
            "√17 − 1": ("radical", 17, -1),
            r"74^{\circ}": ("degrees", 74),
            "74°": ("degrees", 74),
            r"-\frac{1}{21}": ("fraction", -1, 21),
            "-1/21": ("fraction", -1, 21),
        }
        exec(  # noqa: S102 - execute only the fixed local fake-module fixture
            compile(self.source.read_text(), str(self.source), "exec"),
            self.module.__dict__,
        )
        self.module.extract_answer = self.module.forbidden
        self.module.extract_boxed_answer = self.module.forbidden
        self.module.extract_and_grade = self.module.forbidden
        self.module.llm_judge = self.module.forbidden

    def pin(self, **overrides: str) -> MathArenaPin:
        values = {
            "module_name": "matharena.parser",
            "distribution_version": "caller-pinned-version",
            "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
        }
        values.update(overrides)
        return MathArenaPin(**values)

    def grade(
        self,
        extracted_answer: str | None,
        gold: str,
        *,
        pin: MathArenaPin | None = None,
        observed_version: str | None = "caller-pinned-version",
    ) -> dict[str, object]:
        return grade_with_matharena(
            self.module,
            observed_version=observed_version,
            pin=pin or self.pin(),
            extracted_answer=extracted_answer,
            gold=gold,
        )


class MathArenaBoundaryTests(unittest.TestCase):
    def test_unanswered_grader_v2_result_never_invokes_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            extracted = extract_final_answer("Reasoning mentions 3/4 and 4 but is cut")

            result = fake.grade(extracted, "4")

            self.assertEqual(
                result,
                {
                    "correct": False,
                    "extracted_answer_present": False,
                    "extracted_answer": None,
                    "grader_status": "unanswered",
                },
            )
            self.assertEqual(fake.calls, [])

    def test_only_extracted_field_and_gold_reach_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            full_response = (
                "PRIVATE REASONING SENTINEL with stray 4\nFinal answer: 3/4\nlater text"
            )
            extracted = extract_final_answer(full_response)

            result = fake.grade(extracted, r"\frac{3}{4}")

            self.assertTrue(result["correct"])
            self.assertEqual(
                fake.calls[:2],
                [
                    ("parse_answer", "3/4"),
                    ("parse_answer", r"\frac{3}{4}"),
                ],
            )
            self.assertNotIn(full_response, repr(fake.calls))
            self.assertNotIn("PRIVATE REASONING SENTINEL", repr(fake.calls))
            self.assertEqual(
                tuple(inspect.signature(grade_with_matharena).parameters),
                ("module", "observed_version", "pin", "extracted_answer", "gold"),
            )

    def test_fraction_does_not_fall_back_to_last_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            result = fake.grade("3/4", "4")

            self.assertFalse(result["correct"])
            self.assertEqual(
                fake.calls[-1],
                ("check_answers", ("fraction", 3, 4), ("integer", 4)),
            )

    def test_symbolic_formats_are_passed_verbatim_to_pinned_parser(self) -> None:
        cases = (
            ("√17 − 1", r"\sqrt{17}-1"),
            ("74°", r"74^{\circ}"),
            ("-1/21", r"-\frac{1}{21}"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for extracted, gold in cases:
                with self.subTest(extracted=extracted, gold=gold):
                    fake = FakeMathArena(directory)
                    result = fake.grade(extracted, gold)

                    self.assertTrue(result["correct"])
                    self.assertEqual(
                        fake.calls[:2],
                        [("parse_answer", extracted), ("parse_answer", gold)],
                    )

    def test_no_exact_string_fallback_when_upstream_cannot_parse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            result = fake.grade("same-unparseable", "same-unparseable")

            self.assertFalse(result["correct"])
            self.assertEqual(fake.calls[-1], ("check_answers", None, None))

    def test_forbidden_upstream_helpers_are_never_invoked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            result = fake.grade("0.75", r"\frac{3}{4}")

            self.assertTrue(result["correct"])
            self.assertNotIn(("forbidden",), fake.calls)

    def test_malformed_extracted_field_fails_before_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            for extracted in ("", "  ", 4, True):
                with self.subTest(extracted=extracted), self.assertRaises(ValueError):
                    fake.grade(extracted, "4")  # type: ignore[arg-type]
            self.assertEqual(fake.calls, [])


class MathArenaPinTests(unittest.TestCase):
    def test_missing_or_malformed_pin_reports_import_failed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            with self.assertRaises(MathArenaImportFailed) as missing_pin:
                grade_with_matharena(
                    fake.module,
                    observed_version="caller-pinned-version",
                    pin=None,
                    extracted_answer="4",
                    gold="4",
                )
            self.assertEqual(missing_pin.exception.reason, "pin_missing")

            with self.assertRaises(MathArenaImportFailed) as missing_version:
                grade_with_matharena(
                    fake.module,
                    observed_version=None,
                    pin=fake.pin(),
                    extracted_answer="4",
                    gold="4",
                )
            self.assertEqual(missing_version.exception.reason, "version_missing")

            with self.assertRaises(MathArenaImportFailed) as invalid_hash:
                fake.pin(source_sha256="not-a-sha256")
            self.assertEqual(invalid_hash.exception.reason, "pin_invalid")
            self.assertEqual(fake.calls, [])

    def test_no_public_constructor_can_bypass_per_call_verification(self) -> None:
        self.assertFalse(hasattr(matharena_grading, "PinnedMathArenaScorer"))
        self.assertFalse(hasattr(matharena_grading, "bind_matharena_scorer"))

    def test_imported_private_binding_token_cannot_authorize_fake_scorer(self) -> None:
        self.assertFalse(hasattr(matharena_grading, "_VALIDATED_BINDING"))
        self.assertFalse(hasattr(matharena_grading, "PinnedMathArenaScorer"))

    def test_missing_module_reports_import_failed_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)

            with self.assertRaises(MathArenaImportFailed) as raised:
                grade_with_matharena(
                    None,
                    observed_version="caller-pinned-version",
                    pin=fake.pin(),
                    extracted_answer="4",
                    gold="4",
                )

            self.assertEqual(raised.exception.status, "import_failed")
            self.assertEqual(raised.exception.reason, "module_missing")
            self.assertEqual(fake.calls, [])

    def test_module_version_and_hash_mismatches_fail_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            cases = (
                (
                    "module_name_mismatch",
                    fake.module,
                    "caller-pinned-version",
                    fake.pin(module_name="different.parser"),
                ),
                (
                    "version_mismatch",
                    fake.module,
                    "different-version",
                    fake.pin(),
                ),
                (
                    "source_hash_mismatch",
                    fake.module,
                    "caller-pinned-version",
                    fake.pin(source_sha256="0" * 64),
                ),
            )

            for reason, module, observed_version, pin in cases:
                with (
                    self.subTest(reason=reason),
                    self.assertRaises(MathArenaImportFailed) as raised,
                ):
                    grade_with_matharena(
                        module,
                        observed_version=observed_version,
                        pin=pin,
                        extracted_answer="4",
                        gold="4",
                    )
                self.assertEqual(raised.exception.status, "import_failed")
                self.assertEqual(raised.exception.reason, reason)
            self.assertEqual(fake.calls, [])

    def test_missing_source_or_allowed_callable_reports_import_failed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)
            pin = fake.pin()
            fake.source.unlink()
            with self.assertRaises(MathArenaImportFailed) as missing_source:
                fake.grade("4", "4", pin=pin)
            self.assertEqual(missing_source.exception.reason, "source_unavailable")

            second = FakeMathArena(directory)
            del second.module.check_answers
            with self.assertRaises(MathArenaImportFailed) as missing_callable:
                second.grade("4", "4")
            self.assertEqual(missing_callable.exception.reason, "callable_missing")
            self.assertEqual(second.calls, [])

    def test_substituted_callable_fails_provenance_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeMathArena(directory)

            def parse_answer(value: str) -> tuple[object, object]:
                fake.calls.append(("substitute", value))
                return value, None

            fake.module.parse_answer = parse_answer
            with self.assertRaises(MathArenaImportFailed) as raised:
                fake.grade("4", "4")

            self.assertEqual(raised.exception.reason, "callable_provenance_mismatch")
            self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
