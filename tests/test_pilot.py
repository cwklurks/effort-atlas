"""Offline tests for the exploratory Inkling length pilot harness.

Nothing here touches the network. Synthetic rows stand in for the
capabilities/ JSONLs so the suite is green on a clean checkout.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas import ROOT
from effort_atlas.client import Completion
from effort_atlas.pilot import (
    EXIT_CEILING_HALT,
    CeilingGuard,
    CeilingHalt,
    PilotClient,
    live_gate_failures,
    load_selected_items,
    run,
)
from effort_atlas.pilot_select import (
    build_selection,
    largest_remainder,
    select_first_n,
    select_stratified,
)
from effort_atlas.wrapper import LETTERS, Rendered, render, strict_terminator_present


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _row(dataset, i, kind="gold_choice", split="test", category=None, restricted=False, **extra):
    text = None if restricted else f"question {dataset} {i}?"
    row = {
        "schema_version": "source-item-v1", "dataset": dataset, "split": split,
        "source_url": "u", "source_revision": "r" * 40, "source_row_index": i,
        "source_item_id": f"{dataset}-{i}", "prompt_text": text,
        "prompt_sha256": _sha(f"question {dataset} {i}?"),
        "choices": None, "grading": {"kind": kind},
        "license_policy": "restricted_no_plaintext" if restricted else "open_commit_ok",
        "meta": {"category": category or ["a", "b", "c"][i % 3]},
    }
    if kind == "gold_choice":
        row["choices"] = None if restricted else ["c0", "c1", "c2", "c3"]
        row["grading"].update({"gold": None if restricted else "A", "gold_index": None if restricted else 0})
    row.update(extra)
    row["full_row_sha256"] = _sha(json.dumps(row, sort_keys=True))
    return row


def _cfg(tmp: Path, *, per_ds=30.0, total=60.0, cap=32000, levels=("medium",)):
    return {
        "provider": {
            "name": "test_route", "model": "test/model", "max_completion_tokens": cap,
            "max_retries": 0,
            "request_extra_body": {"provider": {"only": ["together"], "allow_fallbacks": False}},
        },
        "effort": {"mode": "openrouter_reasoning", "param_name": "reasoning",
                   "levels": list(levels), "ordinal": {"medium": 1}},
        "pilot": {"enabled": False, "label": "test_pilot", "datasets": ["ds_a", "ds_b"],
                  "wrapper_seed": 7, "request_seed": 7, "cap": cap,
                  "report_caps": [4096, 14096], "circuit_breaker_consecutive_errors": 5},
        "pricing": {"input_per_mtok": 1.0, "output_per_mtok": 4.0,
                    "expected_input_tokens": 100, "expected_output_tokens": {"medium": 1000},
                    "cap_bounds_billable_tokens": True},
        "budget": {"per_dataset_ceiling_usd": per_ds, "total_ceiling_usd": total,
                   "reserve_margin_usd": 0.0, "balance_verified_usd": None,
                   "balance_verified_on": None, "preflight_approved_by": None},
        "paths": {"data": "capabilities", "results": str(tmp / "results"), "cache": str(tmp / "cache")},
    }


class FixedClient:
    """Returns a completion whose length is always `tokens`; counts calls."""

    def __init__(self, tokens: int, finish: str = "stop"):
        self.tokens, self.finish, self.calls = tokens, finish, 0

    def complete(self, prompt, effort, item_id, max_tokens=None, seed=None, messages=None):
        self.calls += 1
        return Completion(text="x\nFinal answer: A", completion_tokens=self.tokens,
                          prompt_tokens=100, latency_s=0.1, finish_reason=self.finish,
                          provider="fake", generation_id=f"g{self.calls}")


class SelectionTests(unittest.TestCase):
    def test_largest_remainder_sums_exactly_and_is_deterministic(self):
        counts = {"x": 1356, "y": 1304, "z": 21, "w": 606}
        alloc = largest_remainder(counts, 200)
        self.assertEqual(sum(alloc.values()), 200)
        self.assertEqual(alloc, largest_remainder(dict(reversed(list(counts.items()))), 200))
        with self.assertRaises(ValueError):
            largest_remainder({"x": 5}, 10)

    def test_first_n_orders_by_source_row_index(self):
        rows = [_row("d", i) for i in (5, 3, 9, 1, 7)] + [_row("d", 0, split="validation")]
        picked = select_first_n(rows, "test", 3)
        self.assertEqual([e["source_row_index"] for e in picked], [1, 3, 5])
        with self.assertRaises(ValueError):
            select_first_n(rows, "test", 10)

    def test_stratified_is_seeded_proportional_and_exact(self):
        rows = [_row("d", i, category="big" if i < 90 else "small") for i in range(100)]
        items, alloc = select_stratified(rows, "test", 10, 1, "d", lambda r: r["meta"]["category"])
        self.assertEqual(alloc, {"big": 9, "small": 1})
        self.assertEqual(len(items), 10)
        again, _ = select_stratified(rows, "test", 10, 1, "d", lambda r: r["meta"]["category"])
        self.assertEqual(items, again)
        other, _ = select_stratified(rows, "test", 10, 2, "d", lambda r: r["meta"]["category"])
        self.assertNotEqual(items, other)
        self.assertEqual([e["source_row_index"] for e in items], sorted(e["source_row_index"] for e in items))

    def test_committed_selection_files_are_intact_and_show_the_first200_problem(self):
        sel_dir = ROOT / "capabilities" / "selections"
        for name in ("selection_first200_v1.json", "selection_stratified200_seed20260830_v1.json"):
            sel = json.loads((sel_dir / name).read_text())
            claimed = sel.pop("selection_sha256")
            recomputed = hashlib.sha256(
                json.dumps(sel, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(claimed, recomputed, name)
            for ds, d in sel["datasets"].items():
                self.assertEqual(d["n"], 200, f"{name}:{ds}")
                self.assertEqual(len({e["source_item_id"] for e in d["items"]}), 200)
                for e in d["items"]:
                    self.assertNotIn("prompt_text", e)
        first = json.loads((sel_dir / "selection_first200_v1.json").read_text())
        self.assertEqual(first["datasets"]["mmlu_pro"]["strata_counts"], {"business": 200})
        strat = json.loads((sel_dir / "selection_stratified200_seed20260830_v1.json").read_text())
        self.assertGreater(len(strat["datasets"]["mmlu_pro"]["strata_counts"]), 10)

    def test_build_selection_refuses_unpinned_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap = Path(tmp)
            (cap / "d.jsonl").write_text("\n".join(json.dumps(_row("d", i)) for i in range(5)) + "\n")
            (cap / "sources_manifest.json").write_text(json.dumps({"outputs": [{"path": "d.jsonl", "sha256": "0" * 64}]}))
            spec = {"d": {"file": "d.jsonl", "split": "test", "stratum_key": None, "stratum": None}}
            with self.assertRaises(ValueError):
                build_selection("first200", n=3, cap_dir=cap, datasets=spec)


class WrapperTests(unittest.TestCase):
    def test_gold_choice_identity_permutation_and_gold_letter(self):
        row = _row("mmlu_pro", 0)
        row["choices"] = [f"opt{i}" for i in range(9)]
        row["grading"].update({"gold": "I", "gold_index": 8})
        r = render(row, seed=1)
        self.assertEqual(r.choice_permutation, list(range(9)))
        self.assertEqual(r.gold_letter, "I")
        self.assertTrue(r.terminator_required)
        self.assertIn("I. opt8", r.prompt)
        self.assertTrue(r.prompt.rstrip().endswith("Final answer: <letter>"))
        self.assertNotIn("prompt", r.manifest_row())

    def test_gpqa_shuffle_is_seeded_recorded_and_invertible(self):
        row = _row("gpqa_main", 3)
        row["choices"] = ["correct", "w1", "w2", "w3"]
        row["grading"].update({"gold": "correct", "gold_index": 0})
        a, b, c = render(row, seed=5), render(row, seed=5), render(row, seed=6)
        self.assertEqual(a.choice_permutation, b.choice_permutation)
        self.assertNotEqual(a.choice_permutation, c.choice_permutation)
        self.assertEqual(a.gold_letter, LETTERS[a.choice_permutation.index(0)])
        self.assertIn(f"{a.gold_letter}. correct", a.prompt)

    def test_restricted_row_without_text_is_refused(self):
        with self.assertRaises(ValueError):
            render(_row("gpqa_main", 0, restricted=True), seed=1)

    def test_ifeval_verbatim_no_terminator(self):
        row = _row("ifeval", 0, kind="verifiable_instructions")
        row["grading"].update({"instruction_id_list": ["punctuation:no_comma"], "kwargs": [{}]})
        r = render(row, seed=1)
        self.assertEqual(r.prompt, row["prompt_text"])
        self.assertFalse(r.terminator_required)

    def test_wildbench_turns_become_messages(self):
        row = _row("wildbench_v2", 0, kind="judge_checklist",
                   conversation_input=[{"role": "user", "content": "hi"},
                                       {"role": "assistant", "content": "hello"},
                                       {"role": "user", "content": "more"}])
        row["prompt_text"] = None
        r = render(row, seed=1)
        self.assertIsNone(r.prompt)
        self.assertEqual([m["role"] for m in r.messages], ["user", "assistant", "user"])
        self.assertFalse(r.terminator_required)
        self.assertNotIn("messages", r.manifest_row())

    def test_strict_terminator_is_last_line_only(self):
        self.assertTrue(strict_terminator_present("think\nFinal answer: B\n\n"))
        self.assertFalse(strict_terminator_present("Final answer: B\nbut actually C"))
        self.assertFalse(strict_terminator_present("the answer is 42"))
        self.assertFalse(strict_terminator_present("Final answer:   "))
        self.assertFalse(strict_terminator_present(""))


class CeilingTests(unittest.TestCase):
    def test_guard_halts_before_the_call_that_would_cross(self):
        g = CeilingGuard(per_dataset_ceiling=1.0, total_ceiling=1.5)
        g.check_before_call("a", 0.4); g.record("a", 0.4)
        g.check_before_call("a", 0.4); g.record("a", 0.4)
        with self.assertRaises(CeilingHalt):
            g.check_before_call("a", 0.4)          # 0.8 + 0.4 > 1.0 per-dataset
        g.check_before_call("b", 0.4); g.record("b", 0.4)
        with self.assertRaises(CeilingHalt):
            g.check_before_call("b", 0.4)          # 1.2 + 0.4 > 1.5 total

    def test_run_halts_on_simulated_overrun_and_ledger_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cap = 32000
            # worst case per call = (est_in*1 + 32000*4)/1e6 ~= $0.128; each real call
            # bills 32000 tokens = $0.128. Ceiling $0.40 -> 3 calls fit, the 4th halts.
            cfg = _cfg(tmp, per_ds=0.40, total=100.0, cap=cap)
            rendered = [render(_row("ds_a", i), seed=1) for i in range(10)]
            client = FixedClient(tokens=cap, finish="length")
            summary, code = run(cfg, rendered, mock=True, out_dir=tmp / "out", client=client)
            self.assertEqual(code, EXIT_CEILING_HALT)
            self.assertEqual(client.calls, 3)
            self.assertIn("ceiling_halt", summary["halt"])
            self.assertTrue(summary["ledger_verified"])
            ledger_rows = [json.loads(l) for l in (tmp / "out").glob("ledger_*.jsonl").__next__().read_text().splitlines()]
            self.assertEqual(len(ledger_rows), 3)
            self.assertEqual({r["finish_reason"] for r in ledger_rows}, {"length"})
            self.assertEqual(summary["datasets"]["ds_a"]["length_stops"], 3)
            self.assertIsNone(summary["datasets"]["ds_a"]["median_completion_tokens"])
            self.assertEqual(summary["datasets"]["ds_a"]["p_length_ge"]["14096"], 1.0)

    def test_ledger_and_manifest_are_content_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg = _cfg(tmp)
            secret = "THE QUESTION TEXT MUST NOT LEAK"
            row = _row("ds_a", 0)
            row["prompt_text"] = secret
            rendered = [render(row, seed=1)]
            run(cfg, rendered, mock=True, out_dir=tmp / "out", client=FixedClient(tokens=10))
            ledger = next((tmp / "out").glob("ledger_*.jsonl")).read_text()
            self.assertNotIn(secret, ledger)
            self.assertNotIn("Final answer", ledger)
            self.assertNotIn(secret, json.dumps(rendered[0].manifest_row()))


class GateTests(unittest.TestCase):
    def test_shipped_config_refuses_live(self):
        from effort_atlas import load_config
        cfg = load_config(ROOT / "config_pilot_inkling.yaml")
        fails = live_gate_failures(cfg, env={})
        self.assertTrue(any("pilot.enabled" in f for f in fails))
        self.assertTrue(any("balance" in f for f in fails))
        self.assertTrue(any("preflight_approved_by" in f for f in fails))
        self.assertEqual(cfg["provider"]["max_retries"], 0)
        self.assertEqual(cfg["pilot"]["cap"], 32000)
        self.assertEqual(cfg["provider"]["max_completion_tokens"], 32000)

    def test_gate_opens_only_when_every_field_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(Path(tmp))
            cfg["pilot"]["enabled"] = True
            cfg["budget"].update({"balance_verified_usd": 100.0, "balance_verified_on": "2026-08-30",
                                  "preflight_approved_by": "Chirag, 2026-08-30", "reserve_margin_usd": 10.0})
            self.assertEqual(live_gate_failures(cfg, env={"EFFORT_ATLAS_PILOT_LIVE_ACK": "I_HAVE_READ_THE_APPROVED_PREFLIGHT"}), [])
            cfg["budget"]["total_ceiling_usd"] = 95.0   # > balance - reserve
            self.assertTrue(live_gate_failures(cfg, env={"EFFORT_ATLAS_PILOT_LIVE_ACK": "I_HAVE_READ_THE_APPROVED_PREFLIGHT"}))

    def test_mock_client_marks_length_at_cap_and_never_networks(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(Path(tmp), cap=100)
            client = PilotClient(cfg, Path(tmp), mock=True)
            hits = 0
            for i in range(40):
                comp = client.complete("p", "medium", f"omni_math:{i}", max_tokens=100)
                self.assertLessEqual(comp.completion_tokens, 100)
                if comp.finish_reason == "length":
                    hits += 1
                    self.assertEqual(comp.completion_tokens, 100)
            self.assertGreater(hits, 0)
            again = client.complete("p", "medium", "omni_math:0", max_tokens=100)
            self.assertTrue(again.cached)


class LoadTests(unittest.TestCase):
    def test_selected_items_verified_against_selection_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap = Path(tmp)
            rows = [_row("ds_a", i) for i in range(3)]
            (cap / "a.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            sel = {"datasets": {"ds_a": {"file": "a.jsonl", "items": [
                {"split": "test", "source_row_index": 1, "source_item_id": "ds_a-1", "prompt_sha256": rows[1]["prompt_sha256"]}]}}}
            cfg = _cfg(cap); cfg["pilot"]["datasets"] = ["ds_a"]
            items = load_selected_items(cfg, sel, cap_dir=cap)
            self.assertEqual([i["source_item_id"] for i in items], ["ds_a-1"])
            sel["datasets"]["ds_a"]["items"][0]["prompt_sha256"] = "0" * 64
            with self.assertRaises(SystemExit):
                load_selected_items(cfg, sel, cap_dir=cap)


class MultiModelConfigTests(unittest.TestCase):
    """Phase-2 candidate configs (reap/28) must satisfy every Inkling invariant.

    Same gates, same cap, same pin discipline; only model, ladder, prices and
    ceilings may differ. The selection stays in lockstep across configs until
    Chirag decision 2 flips all of them together.
    """

    CONFIGS = [
        "config_pilot_inkling.yaml",
        "config_pilot_glm53flash.yaml",
        "config_pilot_qwen38_27b.yaml",
    ]

    def test_shipped_configs_refuse_live_and_share_invariants(self):
        from effort_atlas import load_config
        selections = set()
        for name in self.CONFIGS:
            cfg = load_config(ROOT / name)
            with self.subTest(config=name):
                fails = live_gate_failures(cfg, env={})
                self.assertTrue(any("pilot.enabled" in f for f in fails))
                self.assertTrue(any("balance" in f for f in fails))
                self.assertTrue(any("preflight_approved_by" in f for f in fails))
                self.assertEqual(cfg["provider"]["max_retries"], 0)
                self.assertEqual(cfg["pilot"]["cap"], 32000)
                self.assertEqual(cfg["provider"]["max_completion_tokens"], 32000)
                extra = cfg["provider"]["request_extra_body"]["provider"]
                self.assertIs(extra["allow_fallbacks"], False)
                self.assertTrue(extra["only"])
                self.assertEqual(cfg["effort"]["mode"], "openrouter_reasoning")
                levels = cfg["effort"]["levels"]
                self.assertTrue(levels)
                self.assertEqual(set(cfg["effort"]["ordinal"]), set(levels))
                self.assertEqual(set(cfg["pricing"]["expected_output_tokens"]), set(levels))
                # budget math and the request-level price pin must agree
                self.assertEqual(extra["max_price"]["prompt"], cfg["pricing"]["input_per_mtok"])
                self.assertEqual(extra["max_price"]["completion"], cfg["pricing"]["output_per_mtok"])
                selections.add(cfg["pilot"]["selection"])
        self.assertEqual(len(selections), 1, "configs disagree on the selection file")

    def test_ladder_runs_every_level_and_ledgers_the_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg = _cfg(tmp)
            cfg["effort"]["levels"] = ["low", "high", "max"]
            cfg["effort"]["ordinal"] = {"low": 1, "high": 2, "max": 3}
            cfg["pricing"]["expected_output_tokens"] = {"low": 500, "high": 1000, "max": 2000}
            rendered = [render(_row("ds_a", i), seed=1) for i in range(2)]
            client = FixedClient(tokens=10)
            summary, code = run(cfg, rendered, mock=True, out_dir=tmp / "out", client=client)
            self.assertEqual(code, 0)
            self.assertEqual(client.calls, 6)   # 2 items x 3 levels
            ledger_rows = [json.loads(l) for l in
                           next((tmp / "out").glob("ledger_*.jsonl")).read_text().splitlines()]
            self.assertEqual([r["effort"] for r in ledger_rows],
                             ["low", "high", "max", "low", "high", "max"])
            self.assertEqual(summary["datasets"]["ds_a"]["attempts"], 6)

    def test_mock_lengths_scale_with_ordinal_rank(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(Path(tmp), cap=200000)
            cfg["effort"]["levels"] = ["low", "xhigh"]
            cfg["effort"]["ordinal"] = {"low": 1, "xhigh": 3}
            cfg["pricing"]["expected_output_tokens"] = {"low": 500, "xhigh": 2000}
            client = PilotClient(cfg, Path(tmp), mock=True)
            # distinct prompts so the mock cache does not collapse items
            # (the cache keys on prompt text); deterministic per-item seeds,
            # and means over 200 items are safely ordered by the 2.2x rank-3
            # scaling even with the mock's heavy lognormal tail
            lows = [client.complete(f"p{i}", "low", f"omni_math:{i}", max_tokens=200000).completion_tokens
                    for i in range(200)]
            highs = [client.complete(f"p{i}", "xhigh", f"omni_math:{i}", max_tokens=200000).completion_tokens
                     for i in range(200)]
            self.assertGreater(sum(highs) / len(highs), sum(lows) / len(lows))


if __name__ == "__main__":
    unittest.main()
