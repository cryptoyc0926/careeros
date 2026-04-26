from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResumeQuality:
    low_quality: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    profile_chars: int = 0
    projects_count: int = 0
    internships_count: int = 0
    skills_count: int = 0
    education_count: int = 0

    def label(self) -> str:
        return (
            f"{self.projects_count} 个项目 · {self.internships_count} 段实习 · "
            f"{self.skills_count} 类技能 · {self.education_count} 段教育"
        )


def _text(value: object) -> str:
    return str(value or "").strip()


def profile_text(profile: object) -> str:
    if isinstance(profile, dict) and isinstance(profile.get("pool"), list):
        pool = profile.get("pool") or []
        if not pool:
            return ""
        default_id = profile.get("default")
        default_item = next((p for p in pool if p.get("id") == default_id), pool[0])
        return _text(default_item.get("text"))
    return _text(profile)


def is_blank_experience_item(item: dict[str, Any]) -> bool:
    bullets = [_text(b) for b in item.get("bullets") or []]
    return not any(
        [
            _text(item.get("company")),
            _text(item.get("role")),
            _text(item.get("date")),
            any(bullets),
        ]
    )


def clean_experience_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [item for item in (items or []) if not is_blank_experience_item(item)]


def clean_skill_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [item for item in (items or []) if _text(item.get("label")) or _text(item.get("text"))]


def clean_education_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    cleaned = []
    for item in items or []:
        has_content = (
            _text(item.get("school"))
            or _text(item.get("major"))
            or _text(item.get("date"))
            or any(_text(b) for b in item.get("bullets") or [])
        )
        if has_content:
            cleaned.append(item)
    return cleaned


def sanitize_master(master: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(master)
    sanitized["projects"] = clean_experience_items(sanitized.get("projects"))
    sanitized["internships"] = clean_experience_items(sanitized.get("internships"))
    sanitized["skills"] = clean_skill_items(sanitized.get("skills"))
    sanitized["education"] = clean_education_items(sanitized.get("education"))
    return sanitized


def summarize_resume_quality(master: dict[str, Any]) -> ResumeQuality:
    sanitized = sanitize_master(master)
    profile = profile_text(sanitized.get("profile"))
    projects = sanitized.get("projects") or []
    internships = sanitized.get("internships") or []
    skills = sanitized.get("skills") or []
    education = sanitized.get("education") or []
    basics = sanitized.get("basics") or {}

    reasons: list[str] = []
    warnings: list[str] = []
    if not _text(basics.get("name")):
        reasons.append("姓名为空")
    if len(profile) < 20:
        warnings.append("个人总结为空")
    if not projects:
        reasons.append("项目经历为空")
    if not internships:
        reasons.append("实习经历为空")
    if not education:
        reasons.append("教育背景为空")

    return ResumeQuality(
        low_quality=bool(reasons),
        reasons=reasons,
        warnings=warnings,
        profile_chars=len(profile),
        projects_count=len(projects),
        internships_count=len(internships),
        skills_count=len(skills),
        education_count=len(education),
    )
