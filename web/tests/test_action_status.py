from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.action_status import format_action_status_caption, get_all_action_status, record_action_status  # noqa: E402


def test_record_action_status_stores_last_time_status_and_message():
    state: dict = {}

    record_action_status(
        state,
        "provider_ping",
        "success",
        "Claude ping ok",
        when=datetime(2026, 4, 22, 9, 30, 5),
    )

    status = state["_action_status"]["provider_ping"]
    assert status["last_time"] == "2026-04-22 09:30:05"
    assert status["status"] == "success"
    assert status["message"] == "Claude ping ok"


def test_format_action_status_caption_contains_observable_fields():
    state = {
        "_action_status": {
            "generate_tailor": {
                "last_time": "2026-04-22 09:31:00",
                "status": "error",
                "message": "Validation failed",
            }
        }
    }

    caption = format_action_status_caption(state, "generate_tailor")

    assert "last_time: 2026-04-22 09:31:00" in caption
    assert "status: error" in caption
    assert "Validation failed" in caption


def test_get_all_action_status_returns_sorted_copy():
    state = {}
    record_action_status(state, "z_action", "success", when=datetime(2026, 4, 22, 9, 30, 5))
    record_action_status(state, "a_action", "error", when=datetime(2026, 4, 22, 9, 31, 5))

    all_status = get_all_action_status(state)

    assert list(all_status) == ["a_action", "z_action"]
    assert all_status["a_action"]["status"] == "error"
    all_status["a_action"]["status"] = "mutated"
    assert state["_action_status"]["a_action"]["status"] == "error"
