from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.job_pool_render import normalize_action_text, short_action_text  # noqa: E402


class JobPoolRenderTest(unittest.TestCase):
    def test_normalize_action_text_handles_nan_as_empty(self):
        self.assertEqual(normalize_action_text(float("nan")), "")

    def test_normalize_action_text_handles_none_as_empty(self):
        self.assertEqual(normalize_action_text(None), "")

    def test_normalize_action_text_coerces_non_string_values(self):
        self.assertEqual(normalize_action_text(123), "123")
        self.assertEqual(normalize_action_text(12.5), "12.5")

    def test_short_action_text_truncates_long_text(self):
        value = "a" * 31

        self.assertEqual(short_action_text(value), "a" * 30 + "…")

    def test_short_action_text_does_not_render_nan(self):
        self.assertFalse(short_action_text(math.nan))


if __name__ == "__main__":
    unittest.main()
