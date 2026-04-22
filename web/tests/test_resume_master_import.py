from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_master_import import build_master_from_parsed, should_persist_parsed_resume  # noqa: E402


FULL_EXISTING_MASTER = {
    "id": 1,
    "basics": {"name": "杨超"},
    "profile": {"pool": [{"id": "default", "tags": [], "text": "完整个人总结，包含 AI 增长运营经验。"}], "default": "default"},
    "projects": [{"company": "X @Cady_btc", "role": "独立运营", "date": "2024.03 - 至今", "bullets": ["增长到 9000+"]}],
    "internships": [{"company": "Fancy Tech", "role": "运营", "date": "2024.06 - 2024.09", "bullets": ["做内容"]}],
    "skills": [{"label": "AI 工具", "text": "Claude"}],
    "education": [{"school": "浙江工商大学", "major": "应用统计", "date": "2022.09 - 2026.07"}],
}


def test_build_master_from_parsed_wraps_profile_pool_and_preserves_id():
    parsed = {
        "basics": {"name": "杨超"},
        "profile": "新的个人总结",
        "projects": [],
        "internships": [],
        "skills": [],
        "education": [],
    }

    master = build_master_from_parsed(parsed, existing_master=FULL_EXISTING_MASTER)

    assert master["id"] == 1
    assert master["profile"]["pool"][0]["text"] == "新的个人总结"


def test_should_not_persist_low_quality_parse_over_full_existing_master():
    parsed_master = build_master_from_parsed(
        {
            "basics": {"name": "杨超"},
            "profile": "",
            "projects": [],
            "internships": [{"company": "Fancy Tech", "role": "运营", "date": "2024.06 - 2024.09", "bullets": ["做内容"]}],
            "skills": [],
            "education": [{"school": "浙江工商大学", "major": "应用统计", "date": "2022.09 - 2026.07"}],
        },
        existing_master=FULL_EXISTING_MASTER,
    )

    decision = should_persist_parsed_resume(parsed_master, existing_master=FULL_EXISTING_MASTER, explicit_overwrite=False)

    assert not decision.persist
    assert "个人总结为空" in decision.reason
    assert "项目经历为空" in decision.reason


def test_explicit_overwrite_can_persist_low_quality_parse():
    parsed_master = build_master_from_parsed(
        {
            "basics": {"name": "杨超"},
            "profile": "",
            "projects": [],
            "internships": [],
            "skills": [],
            "education": [],
        },
        existing_master={"id": 1},
    )

    decision = should_persist_parsed_resume(parsed_master, existing_master=FULL_EXISTING_MASTER, explicit_overwrite=True)

    assert decision.persist
    assert decision.low_quality
