from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_chat_session import (  # noqa: E402
    append_chat_message,
    clear_resume_chat_state,
    ensure_resume_chat_state,
)


def test_ensure_resume_chat_state_exposes_rt_chat_history_alias():
    state: dict = {}

    ensure_resume_chat_state(state)

    assert state["rt_chat_history"] is state["tailor_chat"]["messages"]
    assert state["tailor_chat"]["pending"] is None


def test_append_chat_message_keeps_legacy_tailor_chat_in_sync():
    state: dict = {}
    ensure_resume_chat_state(state)

    append_chat_message(state, "user", "帮我整体重写")

    assert state["rt_chat_history"] == [{"role": "user", "content": "帮我整体重写"}]
    assert state["tailor_chat"]["messages"] is state["rt_chat_history"]


def test_clear_resume_chat_state_resets_history_and_pending():
    state: dict = {}
    ensure_resume_chat_state(state)
    append_chat_message(state, "assistant", "准备修改", meta={"intent": "patch_ops"})
    state["tailor_chat"]["pending"] = {"patch": []}

    clear_resume_chat_state(state)

    assert state["rt_chat_history"] == []
    assert state["tailor_chat"]["messages"] is state["rt_chat_history"]
    assert state["tailor_chat"]["pending"] is None
