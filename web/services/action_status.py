"""Small observable status records for Streamlit actions.

The UI can render these with ``st.caption`` after a button callback, while the
state shape stays testable outside Streamlit.
"""

from __future__ import annotations

from datetime import datetime
from typing import MutableMapping

_ROOT_KEY = "_action_status"


def _root(state: MutableMapping) -> dict:
    existing = state.get(_ROOT_KEY)
    if not isinstance(existing, dict):
        existing = {}
        state[_ROOT_KEY] = existing
    return existing


def record_action_status(
    state: MutableMapping,
    key: str,
    status: str,
    message: str = "",
    *,
    when: datetime | None = None,
) -> dict:
    """Record a button/action status with a visible timestamp."""
    ts = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "last_time": ts,
        "status": str(status or "unknown"),
        "message": str(message or ""),
    }
    _root(state)[key] = payload
    return payload


def get_action_status(state: MutableMapping, key: str) -> dict | None:
    """Return the action status payload if present."""
    payload = _root(state).get(key)
    return payload if isinstance(payload, dict) else None


def get_all_action_status(state: MutableMapping) -> dict:
    """Return a sorted copy of the full ``_action_status`` mapping."""
    return {key: dict(value) for key, value in sorted(_root(state).items()) if isinstance(value, dict)}


def format_action_status_caption(state: MutableMapping, key: str) -> str:
    """Format status as a compact ``last_time + status`` caption."""
    payload = get_action_status(state, key)
    if not payload:
        return ""
    last_time = payload.get("last_time") or "-"
    status = payload.get("status") or "-"
    message = payload.get("message") or ""
    caption = f"last_time: {last_time} · status: {status}"
    if message:
        caption += f" · {message}"
    return caption
