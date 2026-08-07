import unittest

from trunccheck import Fixture, run_check


def truncated(identifier, text="work", gold="7", stratum="real_truncated"):
    return Fixture(identifier, "truncated", stratum, text, gold, True)


def control(identifier, text="Final answer: 7", gold="7"):
    return Fixture(identifier, "control_correct", "finished_control", text, gold, False)


class RunnerTests(unittest.TestCase):
    def test_empty_text_is_in_denominator(self):
        report = run_check(lambda text: "" if not text else "9", [truncated("empty", ""), truncated("full")])
        metric = report.metric("answer_returned_after_truncation_pct")
        self.assertEqual((metric.numerator, metric.denominator, metric.percent), (1, 2, 50.0))
        self.assertEqual(report.metric("fabrication_pct"), metric.__class__("fabrication_pct", 1, 2, 50.0))

    def test_escaped_exceptions_are_separate_and_hooked(self):
        observed = []
        def extractor(text):
            raise LookupError("no closing delimiter")
        report = run_check(
            extractor,
            [truncated("boom")],
            escaped_exception_hook=lambda fixture, exception: observed.append((fixture.fixture_id, exception)),
        )
        result = report.results[0]
        self.assertEqual(result.escaped_exception_class, "LookupError")
        self.assertEqual(result.escaped_exception_message, "no closing delimiter")
        self.assertFalse(result.answer_returned)
        self.assertEqual(report.metric("crash_pct").percent, 100.0)
        self.assertEqual(observed[0][0], "boom")
        self.assertIsInstance(observed[0][1], LookupError)

    def test_swallowed_error_instrumentation(self):
        fixtures = [truncated("fallback", "bad"), truncated("normal", "good")]
        report = run_check(
            lambda text: "42" if text == "bad" else "7",
            fixtures,
            swallowed_error_hook=lambda fixture, answer: fixture.fixture_id == "fallback",
        )
        self.assertEqual([r.swallowed_error for r in report.results], [True, False])
        self.assertEqual(report.metric("swallowed_error_pct").percent, 50.0)
        self.assertEqual(report.metric("crash_pct").percent, 0.0)

    def test_swallowed_error_is_not_inferred(self):
        report = run_check(lambda text: "fallback sentinel", [truncated("fallback")])
        metric = report.metric("swallowed_error_pct")
        self.assertEqual(metric.status, "not_measured")
        self.assertIsNone(report.results[0].swallowed_error)

    def test_controls_and_harness_native_scorer(self):
        def extract(text):
            return text.rsplit(" ", 1)[-1]
        score = lambda answer, gold: answer == gold
        report = run_check(extract, [truncated("t", "guess 8"), control("c")], scorer=score)
        self.assertEqual(report.metric("accidental_correct_pct").percent, 0.0)
        self.assertEqual(report.metric("control_pass_pct").percent, 100.0)
        self.assertEqual(report.status, "ok")

    def test_failed_control_disqualifies(self):
        report = run_check(lambda text: "wrong", [truncated("t"), control("c")], scorer=lambda a, g: a == g)
        self.assertEqual(report.status, "control_disqualified")
        self.assertEqual(report.metric("control_pass_pct").percent, 0.0)

    def test_no_scorer_means_correctness_not_measured(self):
        report = run_check(lambda text: "7", [truncated("t"), control("c")])
        self.assertEqual(report.metric("accidental_correct_pct").status, "not_measured")
        self.assertEqual(report.metric("control_pass_pct").status, "not_measured")
        self.assertEqual(report.metric("control_answer_returned_pct").percent, 100.0)

    def test_scoring_exceptions_are_not_extraction_crashes(self):
        report = run_check(lambda text: "7", [control("c")], scorer=lambda a, g: 1 / 0)
        result = report.results[0]
        self.assertFalse(result.crashed)
        self.assertEqual(result.scoring_exception_class, "ZeroDivisionError")
        self.assertEqual(report.status, "control_disqualified")

    def test_duplicate_fixture_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            run_check(lambda text: None, [truncated("same"), truncated("same")])

    def test_real_and_synthetic_strata_are_separate(self):
        fixtures = [truncated("real", stratum="real_truncated"), truncated("syn", stratum="synthetic_truncated")]
        report = run_check(lambda text: "1", fixtures)
        self.assertEqual(report.metric("fabrication_pct_real_truncated").denominator, 1)
        self.assertEqual(report.metric("fabrication_pct_synthetic_truncated").denominator, 1)
