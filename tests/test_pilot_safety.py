"""Run the real pilot orchestration with synthetic files and fake completions."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from effort_atlas import pilot, sweep
from effort_atlas.client import Completion, RequestFailure
from effort_atlas.pilot_accounting import BudgetJournal, AccountingHalt
from effort_atlas.pilot_contract import EVIDENCE_CHECKS, LIVE_ACK_ENV, LIVE_ACK_VALUE, run_manifest
from effort_atlas.pilot_select import build_selection
from effort_atlas.wrapper import render
from test_pilot import _cfg, _row, FixedClient
from test_pilot_integrity import _canonical, _row as source_row


class RunnerSafetyTests(unittest.TestCase):
    def test_legacy_cli_defaults_to_dry_and_paid_python_entry_refuses(self):
        with patch("sys.argv", ["sweep"]), patch.object(sweep, "load_config", return_value={
            "paths": {"data": "unused"}, "sweep": {"domains": [], "items_per_domain": 1}}), \
            patch.object(sweep, "load_items", return_value=[]), patch.object(sweep, "dry_run") as dry, \
            patch.object(sweep, "InklingClient") as ctor:
            sweep.main()
            dry.assert_called_once()
            ctor.assert_not_called()
        with patch.object(sweep, "InklingClient") as ctor, self.assertRaises(SystemExit):
            sweep.run(mock=False)
        ctor.assert_not_called()

    def test_even_median_and_inclusive_reasoning_cost(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            rows = [{"dataset": "a", "completion_tokens": n, "finish_reason": "stop",
                     "terminator_present": True, "terminator_required": True, "cost_usd": 0}
                    for n in (100, 200, 300, 400)]
            result = pilot._summary(cfg, rows, pilot.CeilingGuard(1, 1), None)
            self.assertEqual(result["datasets"]["a"]["median_completion_tokens"], 250)
            comp = Completion("", 100, 10, 0, reasoning_tokens=80)
            self.assertAlmostEqual(pilot.actual_call_usd(cfg, comp), 0.000410)
            comp.cached = True
            comp.reported_cost_usd = 123
            self.assertEqual(pilot.actual_call_usd(cfg, comp), 0)

    def test_summary_keeps_effort_cells_and_error_denominators_separate(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td), levels=("medium", "max"))
            cfg["pilot"]["report_caps"] = [1000]
            rows = [{"dataset": "a", "effort": effort, "completion_tokens": tokens,
                     "finish_reason": finish, "terminator_present": True,
                     "terminator_required": True, "cost_usd": 0}
                    for effort, tokens, finish in (("medium", 100, "stop"), ("max", 32000, "length"))]
            rows.append({"dataset": "a", "effort": "max", "error": "request_error"})
            result = pilot._summary(cfg, rows, pilot.CeilingGuard(1, 1), None)
            cells = result["dataset_effort_cells"]["a"]
            self.assertEqual(cells["medium"]["median_completion_tokens"], 100)
            self.assertIsNone(cells["max"]["median_completion_tokens"])
            self.assertEqual(cells["medium"]["p_length_ge"]["1000"], 0)
            self.assertEqual(cells["max"]["p_length_ge"]["1000"], 1)
            self.assertEqual(cells["max"]["attempts"], 2)
            self.assertEqual(cells["max"]["responses"], 1)
            self.assertEqual(cells["max"]["errors"], 1)
            self.assertEqual(cells["max"]["length_stop_rate"], 1)
            self.assertEqual(result["dataset_summary_scope"], "pooled_across_efforts")

    def test_length_stop_below_cap_is_not_used_as_an_uncensored_length(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            summary, code = pilot.run(_cfg(root), [render(_row("ds_a", 0), seed=1)],
                                      mock=True, out_dir=root / "out", client=FixedClient(100, "length"))
            self.assertEqual(code, pilot.EXIT_CIRCUIT_BREAKER)
            self.assertEqual(summary["datasets"]["ds_a"]["errors"], 1)

    def test_repeated_invocation_cannot_rebill_or_duplicate_measurements(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg, client = _cfg(root), FixedClient(100)
            rendered = [render(_row("ds_a", 0), seed=1)]
            first, code = pilot.run(cfg, rendered, mock=True, out_dir=root / "out", client=client)
            second, code2 = pilot.run(cfg, rendered, mock=True, out_dir=root / "out", client=client)
            self.assertEqual((code, code2, client.calls), (0, 0, 1))
            self.assertEqual(second["already_completed_jobs"], 1)
            self.assertEqual(first["spent_total"], second["spent_total"])
            self.assertEqual(second["datasets"], {})

    def test_uncertain_request_stops_and_sanitizes_without_retry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            class Failing:
                calls = 0
                def complete(self, *args, **kwargs):
                    self.calls += 1
                    raise RequestFailure("request_error", submitted=True,
                                         metadata={"generation_id": "gen-partial", "completion_tokens": 5})
            client = Failing()
            rendered = [render(_row("ds_a", i), seed=1) for i in range(2)]
            result, code = pilot.run(cfg, rendered, mock=True, out_dir=root / "out", client=client)
            self.assertEqual(code, pilot.EXIT_CIRCUIT_BREAKER)
            self.assertEqual(client.calls, 1)
            self.assertGreater(result["exposure_total"], 0)
            self.assertEqual(result["spent_total"], 0)
            self.assertIn("gen-partial", Path(result["ledger"]).read_text())
            pilot.run(cfg, rendered, mock=True, out_dir=root / "out", client=client)
            self.assertEqual(client.calls, 1)

    def test_raw_exception_and_interrupt_are_ledgered_without_their_text(self):
        for exception in (RuntimeError, SystemExit, KeyboardInterrupt):
            with self.subTest(exception=exception), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                secret = "SYNTHETIC_PRIVATE_PROMPT_MUST_NOT_APPEAR"
                class Failing:
                    def complete(self, *a, **k):
                        raise exception(secret)
                out = io.StringIO()
                with redirect_stdout(out):
                    summary, code = pilot.run(_cfg(root), [render(_row("ds_a", 0), seed=1)],
                                              mock=True, out_dir=root / "out", client=Failing())
                self.assertEqual(code, pilot.EXIT_CIRCUIT_BREAKER)
                self.assertNotIn(secret, out.getvalue() + Path(summary["ledger"]).read_text())
                self.assertEqual(summary["unresolved_jobs"], 1)

    def test_reservation_transaction_is_serialized_across_contenders(self):
        with tempfile.TemporaryDirectory() as td:
            def reserve(job):
                journal = BudgetJournal(Path(td) / "ledger.jsonl", model="model",
                                        total_ceiling=0.1, per_dataset_ceiling=0.1, pool_ceiling=0.1)
                try:
                    journal.reserve({"job_id": job, "model": "model", "domain": "a"}, 0.1)
                    return "reserved"
                except AccountingHalt:
                    return "blocked"
            with ThreadPoolExecutor(max_workers=2) as executor:
                self.assertCountEqual(executor.map(reserve, ["a", "b"]), ["reserved", "blocked"])


class LiveOrchestrationWithoutNetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cap = self.root / "capabilities"
        cap.mkdir()
        source = [_canonical(source_row("ds_a", i)) for i in range(2)]
        blob = ("\n".join(source) + "\n").encode()
        (cap / "a.jsonl").write_bytes(blob)
        (cap / "sources_manifest.json").write_text(json.dumps({
            "schema_version": "capabilities-source-manifest-v1", "outputs": [{
                "path": "a.jsonl", "bytes": len(blob), "rows": 2,
                "sha256": hashlib.sha256(blob).hexdigest()}]}))
        self.selection = build_selection("first200", n=2, cap_dir=cap, datasets={"ds_a": {
            "file": "a.jsonl", "split": "test", "stratum_key": None, "stratum": None}})
        (cap / "selection.json").write_text(json.dumps(self.selection))
        self.cfg = _cfg(self.root)
        self.cfg["paths"].update(results="results_pilot/test", cache=".cache_pilot/test")
        self.cfg["pilot"].update(enabled=True, datasets=["ds_a"], selection="capabilities/selection.json")
        self.cfg["provider"].update(default_base_url="https://openrouter.ai/api/v1", base_url_env="TEST_BASE_URL")
        self.cfg["budget"].update(balance_verified_usd=100, balance_verified_on="2026-09-03",
                                  preflight_approved_by="synthetic test reviewer")
        self.cfg["pricing"]["verified_on"] = "2026-09-03"
        self.rendered = pilot.render_all(self.cfg, pilot.load_selected_items(self.cfg, self.selection, cap_dir=cap))
        self.approve()
        self.addCleanup(patch.stopall)
        patch.object(pilot, "ROOT", self.root).start()
        patch.object(pilot, "ACCOUNT_LEDGER_PATH", self.root / "accounting/openrouter.jsonl").start()
        patch.dict("os.environ", {LIVE_ACK_ENV: LIVE_ACK_VALUE}, clear=True).start()

    def approve(self):
        digest = run_manifest(self.cfg, self.rendered, self.selection["selection_sha256"])["run_sha256"]
        folder = self.root / "reap"
        folder.mkdir(exist_ok=True)
        artifact = folder / "synthetic-evidence.txt"
        artifact.write_text("SYNTHETIC TEST EVIDENCE ONLY; NEVER A REAL APPROVAL")
        spec = {"path": "reap/synthetic-evidence.txt", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
        evidence = {"run_sha256": digest, "approved_by": self.cfg["budget"]["preflight_approved_by"],
                    "approved_on": "2026-09-03", "checks": {key: True for key in EVIDENCE_CHECKS},
                    "artifacts": {key: spec for key in EVIDENCE_CHECKS}}
        path = folder / "approval.json"
        path.write_text(json.dumps(evidence))
        self.cfg["budget"].update(approved_run_sha256=digest, approval_evidence={
            "path": "reap/approval.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    def execute(self, client, fetch):
        with patch.object(pilot, "PilotClient") as constructor:
            result = pilot.run(self.cfg, self.rendered, mock=False,
                               out_dir=self.root / "results_pilot/test", client=client, receipt_fetcher=fetch)
            constructor.assert_not_called()
            return result

    def completion(self, n):
        return Completion("Final answer: A", 100, 100, .1, reasoning_tokens=80,
                          finish_reason="stop", provider="Together", generation_id=f"gen-{n}",
                          reported_cost_usd=.0005)

    def receipt(self, cfg, generation_id):
        return {"data": {"id": generation_id, "provider_name": "Together", "total_cost": .0005,
                         "native_tokens_prompt": 100, "native_tokens_completion": 100,
                         "native_tokens_reasoning": 80, "finish_reason": "stop"}}

    def client(self):
        owner = self
        class Fake:
            calls = 0
            def complete(self, *a, **k):
                self.calls += 1
                return owner.completion(self.calls)
        return Fake()

    def test_valid_approval_reconciles_every_call_before_next_request(self):
        client = self.client()
        fetches = []
        def fetch(cfg, generation_id):
            self.assertEqual(client.calls, len(fetches) + 1)
            fetches.append(generation_id)
            return self.receipt(cfg, generation_id)
        result, code = self.execute(client, fetch)
        self.assertEqual((code, client.calls, len(fetches)), (0, 2, 2))
        self.assertAlmostEqual(result["spent_total"], .001)
        self.assertTrue(result["ledger_verified"])
        self.assertEqual(result["unresolved_jobs"], 0)

    def test_receipt_above_reservation_halts_before_second_request(self):
        self.cfg["pilot"].update(cap=100, input_token_allowance=100)
        self.cfg["provider"]["max_completion_tokens"] = 100
        self.cfg["budget"].update(total_ceiling_usd=.0005, per_dataset_ceiling_usd=.0005)
        self.approve()
        owner = self
        class Overcharged:
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                comp = owner.completion(self.calls)
                comp.reported_cost_usd = .00055
                return comp
        client = Overcharged()
        def receipt(cfg, generation_id):
            result = self.receipt(cfg, generation_id)
            result["data"]["total_cost"] = .00055
            return result
        result, code = self.execute(client, receipt)
        self.assertEqual(code, pilot.EXIT_CIRCUIT_BREAKER)
        self.assertEqual(client.calls, 1)
        self.assertEqual(result["unresolved_jobs"], 1)
        self.assertEqual(result["spent_total"], 0)
        self.assertAlmostEqual(result["pool_exposure"], .00055)

    def test_stale_approval_and_modified_rendered_bytes_prevent_any_call(self):
        client = self.client()
        self.cfg["pilot"]["request_seed"] += 1
        self.assertEqual(self.execute(client, self.receipt)[1], pilot.EXIT_GATE_REFUSED)
        self.cfg["pilot"]["request_seed"] -= 1
        self.rendered[0].prompt += "tampered"
        self.assertEqual(self.execute(client, self.receipt)[1], pilot.EXIT_GATE_REFUSED)
        self.assertEqual(client.calls, 0)

    def test_empty_but_correctly_hashed_evidence_does_not_open_gate(self):
        client = self.client()
        artifact = self.root / "reap/synthetic-evidence.txt"
        artifact.write_text(" \n")
        path = self.root / "reap/approval.json"
        evidence = json.loads(path.read_text())
        for spec in evidence["artifacts"].values():
            spec["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        path.write_text(json.dumps(evidence))
        self.cfg["budget"]["approval_evidence"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(self.execute(client, self.receipt)[1], pilot.EXIT_GATE_REFUSED)
        self.assertEqual(client.calls, 0)

    def test_route_case_change_with_new_approval_cannot_recollect(self):
        client = self.client()
        self.assertEqual(self.execute(client, self.receipt)[1], 0)
        self.cfg["provider"]["request_extra_body"]["provider"]["only"] = ["Together"]
        self.approve()
        result, code = self.execute(client, self.receipt)
        self.assertEqual((code, client.calls, result["already_completed_jobs"]), (0, 2, 2))

    def test_authorization_header_refuses_before_manifest_or_call(self):
        client = self.client()
        self.cfg["provider"]["default_headers"] = {"Authorization": "Bearer SYNTHETIC_SECRET"}
        result, code = self.execute(client, self.receipt)
        self.assertEqual((code, client.calls), (pilot.EXIT_GATE_REFUSED, 0))
        self.assertFalse((self.root / "results_pilot/test").exists())

    def test_wrong_receipt_or_missing_receipt_halts_with_full_reservation(self):
        client = self.client()
        def bad_receipt(cfg, generation_id):
            value = self.receipt(cfg, generation_id)
            value["data"]["total_cost"] = .001
            return value
        result, code = self.execute(client, bad_receipt)
        self.assertEqual((code, client.calls), (pilot.EXIT_CIRCUIT_BREAKER, 1))
        self.assertGreater(result["exposure_total"], .001)
        self.assertEqual(result["spent_total"], 0)
        self.execute(client, self.receipt)
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
