import copy
import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas import ROOT, load_config
from effort_atlas.pilot_contract import configuration_failures, live_gate_failures


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config(ROOT / "config_pilot_inkling.yaml")
        self.cfg["pilot"]["input_token_allowance"] = 65536
        self.cfg["pilot"]["request_input_byte_limit"] = 60000
        self.cfg["pricing"]["completion_includes_reasoning"] = True

    def test_valid_offline_config_has_no_structural_failures(self):
        self.assertEqual(configuration_failures(self.cfg), [])

    def test_malformed_money_boolean_pins_and_dates_fail_closed(self):
        for section, key, value in (
            ("pilot", "enabled", "false"), ("pilot", "cap", True),
            ("budget", "total_ceiling_usd", float("nan")),
            ("budget", "balance_verified_usd", float("inf")),
            ("pricing", "input_per_mtok", -1),
            ("provider", "max_retries", True),
            ("pilot", "request_seed", None),
        ):
            cfg = copy.deepcopy(self.cfg)
            cfg[section][key] = value
            with self.subTest(section=section, key=key):
                self.assertTrue(configuration_failures(cfg))
        cfg = copy.deepcopy(self.cfg)
        cfg["provider"]["request_extra_body"]["provider"]["require_parameters"] = False
        self.assertTrue(configuration_failures(cfg))
        cfg = copy.deepcopy(self.cfg)
        cfg["budget"].update(balance_verified_on="yesterday", preflight_approved_by="  ")
        self.assertTrue(live_gate_failures(cfg, env={}))

    def test_populating_old_gate_fields_does_not_approve_a_run(self):
        self.cfg["pilot"]["enabled"] = True
        self.cfg["budget"].update(balance_verified_usd=100,
                                  balance_verified_on="2026-09-03",
                                  preflight_approved_by="reviewer")
        failures = live_gate_failures(self.cfg, env={
            "EFFORT_ATLAS_PILOT_LIVE_ACK": "I_HAVE_READ_THE_APPROVED_PREFLIGHT"})
        self.assertTrue(any("approved_run_sha256" in f for f in failures))
        self.assertTrue(any("evidence" in f for f in failures))

    def test_credentials_and_unknown_config_cannot_enter_a_manifest(self):
        self.cfg["provider"]["default_headers"] = {"Authorization": "Bearer SYNTHETIC_SECRET"}
        self.assertTrue(configuration_failures(self.cfg))
        self.cfg["provider"].pop("default_headers")
        self.cfg["provider"]["api_key"] = "SYNTHETIC_SECRET"
        self.assertTrue(configuration_failures(self.cfg))


if __name__ == "__main__":
    unittest.main()
