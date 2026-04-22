"""Session-state helpers for Resume Tailor chat.

``rt_chat_history`` is the canonical history key requested by CX-03. The
existing ``tailor_chat`` structure remains as a compatibility wrapper because
it also owns the pending patch state.
"""

from __future__ import annotations

from typing import Any, MutableMapping


def ensure_resume_chat_state(state: MutableMapping) -> dict[str, Any]:
    legacy = state.get("tailor_chat")
    if not isinstance(legacy, dict):
        legacy = {}

    history = state.get("rt_chat_history")
    if not isinstance(history, list):
        legacy_messages = legacy.get("messages")
        history = legacy_messages if isinstance(legacy_messages, list) else []

    pending = legacy.get("pending") if isinstance(legacy.get("pending"), dict) else None
    state["rt_chat_history"] = history
    state["tailor_chat"] = {
        "messages": history,
        "pending": pending,
    }
    return state["tailor_chat"]


def append_chat_message(
    state: MutableMapping,
    role: str,
    content: str,
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chat = ensure_resume_chat_state(state)
    msg: dict[str, Any] = {"role": role, "content": content}
    if meta:
        msg["_meta"] = meta
    chat["messages"].append(msg)
    state["rt_chat_history"] = chat["messages"]
    return msg


def set_pending_patch(state: MutableMapping, explanation: str, patch: list[dict]) -> None:
    chat = ensure_resume_chat_state(state)
    chat["pending"] = {"explanation": explanation, "patch": patch}


def clear_pending_patch(state: MutableMapping) -> None:
    chat = ensure_resume_chat_state(state)
    chat["pending"] = None


def replace_chat_history(state: MutableMapping, messages: list[dict[str, Any]] | None) -> None:
    history = list(messages or [])
    state["rt_chat_history"] = history
    legacy = state.get("tailor_chat") if isinstance(state.get("tailor_chat"), dict) else {}
    state["tailor_chat"] = {
        "messages": history,
        "pending": legacy.get("pending") if isinstance(legacy.get("pending"), dict) else None,
    }


def clear_resume_chat_state(state: MutableMapping) -> None:
    state["rt_chat_history"] = []
    state["tailor_chat"] = {"messages": state["rt_chat_history"], "pending": None}
