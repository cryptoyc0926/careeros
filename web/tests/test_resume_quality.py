from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_quality import (  # noqa: E402
    ResumeQuality,
    clean_experience_items,
    is_blank_experience_item,
    sanitize_master,
    summarize_resume_quality,
)


def test_blank_experience_item_detection():
    assert is_blank_experience_item({"company": "", "role": "", "date": "", "bullets": []})
    assert is_blank_experience_item({"company": "  ", "role": "", "date": "", "bullets": [""]})
    assert not is_blank_experience_item({"company": "Fancy Tech", "role": "", "date": "", "bullets": []})
    assert not is_blank_experience_item({"company": "", "role": "", "date": "", "bullets": ["did work"]})


def test_clean_experience_items_removes_only_blank_items():
    items = [
        {"company": "", "role": "", "date": "", "bullets": []},
        {"company": "X @Cady_btc", "role": "独立运营", "date": "2024.03 - 至今", "bullets": ["增长到 9000+"]},
    ]

    assert clean_experience_items(items) == [items[1]]


def test_summarize_resume_quality_marks_empty_profile_and_projects_low_quality():
    master = {
        "basics": {"name": "杨超"},
        "profile": {"pool": [{"id": "default", "tags": [], "text": ""}], "default": "default"},
        "projects": [{"company": "", "role": "", "date": "", "bullets": []}],
        "internships": [{"company": "Fancy Tech", "role": "运营", "date": "2024.06 - 2024.09", "bullets": ["做内容"]}],
        "skills": [],
        "education": [{"school": "浙江工商大学", "major": "应用统计", "date": "2022.09 - 2026.07"}],
    }

    quality = summarize_resume_quality(master)

    assert isinstance(quality, ResumeQuality)
    assert quality.low_quality
    assert "个人总结为空" in quality.reasons
    assert "项目经历为空" in quality.reasons


def test_summarize_resume_quality_accepts_full_master():
    master = {
        "basics": {"name": "杨超"},
        "profile": {"pool": [{"id": "default", "tags": [], "text": "有 AI 增长运营经验，做过 9000+ 粉账号。"}], "default": "default"},
        "projects": [{"company": "X @Cady_btc", "role": "独立运营", "date": "2024.03 - 至今", "bullets": ["增长到 9000+"]}],
        "internships": [{"company": "Fancy Tech", "role": "运营", "date": "2024.06 - 2024.09", "bullets": ["做内容"]}],
        "skills": [{"label": "AI 工具", "text": "Claude Code"}],
        "education": [{"school": "浙江工商大学", "major": "应用统计", "date": "2022.09 - 2026.07"}],
    }

    quality = summarize_resume_quality(master)

    assert not quality.low_quality
    assert quality.profile_chars > 10
    assert quality.projects_count == 1


def test_sanitize_master_removes_blank_project_before_persistence():
    master = {
        "basics": {"name": "杨超"},
        "profile": {"pool": [{"id": "default", "tags": [], "text": "完整总结"}], "default": "default"},
        "projects": [{"company": "", "role": "", "date": "", "bullets": []}],
        "internships": [{"company": "Fancy Tech", "role": "运营", "date": "2024.06 - 2024.09", "bullets": ["做内容"]}],
        "skills": [{"label": "", "text": ""}],
        "education": [{"school": "", "major": "", "date": "", "bullets": []}],
    }

    sanitized = sanitize_master(master)

    assert sanitized["projects"] == []
    assert sanitized["skills"] == []
    assert sanitized["education"] == []
    assert sanitized["internships"]
