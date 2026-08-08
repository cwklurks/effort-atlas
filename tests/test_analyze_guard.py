import unittest

from effort_atlas.analyze import ConfirmatoryRowsUnsupportedError, reject_confirmatory_rows


class AnalyzeGuardTests(unittest.TestCase):
    def test_guard_raises_before_cap_omitting_dedup_can_run(self):
        rows = [
            {"domain": "math", "item_id": "item-a", "effort": "low", "cap": 4096},
            {"domain": "math", "item_id": "item-a", "effort": "low", "cap": 16384},
        ]

        with self.assertRaisesRegex(ConfirmatoryRowsUnsupportedError, "cap"):
            reject_confirmatory_rows(rows)

    def test_guard_allows_legacy_exploratory_rows_without_cap_dimension(self):
        reject_confirmatory_rows(
            [{"domain": "math", "item_id": "item-a", "effort": "low", "max_tokens": 4096}]
        )


if __name__ == "__main__":
    unittest.main()
