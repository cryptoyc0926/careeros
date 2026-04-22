"""Render-safe helpers for the job pool page."""

from __future__ import annotations

import math
from typing import Any


def normalize_action_text(value: Any) -> str:
    """Return a string safe for slicing/rendering action text."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def short_action_text(value: Any, *, limit: int = 30) -> str:
    """Normalize and truncate job-pool action text."""
    text = normalize_action_text(value)
    if len(text) > limit:
        return text[:limit] + "…"
    return text
