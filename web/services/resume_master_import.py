from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.resume_quality import sanitize_master, summarize_resume_quality


@dataclass
class ImportDecision:
    persist: bool
    low_quality: bool
    reason: str


def build_master_from_parsed(
    parsed: dict[str, Any],
    *,
    existing_master: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = existing_master or {}
    master = {
        "id": existing.get("id"),
        "basics": parsed["basics"],
        "profile": {
            "pool": [{"id": "default", "tags": [], "text": parsed.get("profile") or ""}],
            "default": "default",
        },
        "projects": parsed.get("projects") or [],
        "internships": parsed.get("internships") or [],
        "skills": parsed.get("skills") or [],
        "education": parsed.get("education") or [],
        "original_docx_blob": existing.get("original_docx_blob"),
        "original_docx_filename": existing.get("original_docx_filename"),
    }
    return sanitize_master(master)


def should_persist_parsed_resume(
    parsed_master: dict[str, Any],
    *,
    existing_master: dict[str, Any] | None,
    explicit_overwrite: bool = False,
) -> ImportDecision:
    parsed_quality = summarize_resume_quality(parsed_master)
    existing_quality = summarize_resume_quality(existing_master or {})

    if explicit_overwrite:
        return ImportDecision(True, parsed_quality.low_quality, "用户显式覆盖")

    if parsed_quality.low_quality and not existing_quality.low_quality:
        return ImportDecision(False, True, "；".join(parsed_quality.reasons))

    return ImportDecision(True, parsed_quality.low_quality, "解析质量可接受")
