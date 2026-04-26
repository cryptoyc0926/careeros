from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_parser import _repair_parsed_schema  # noqa: E402


def test_repair_parsed_schema_infers_profile_from_first_content_paragraph():
    raw_text = """
李默
138-0000-0000 | demo@example.com

个人陈述
应用统计背景，熟悉内容增长、数据分析和 AI 工具协作，能把复杂信息整理成可执行动作。

教育背景
示例大学 | 示例专业 | 2022.09 - 2026.07
""".strip()

    repaired = _repair_parsed_schema(
        raw_text,
        {
            "basics": {"name": "李默", "phone": "", "email": "", "target_role": "", "city": "", "availability": "", "photo": ""},
            "profile": "",
            "projects": [],
            "internships": [],
            "skills": [],
            "education": [{"school": "示例大学", "major": "示例专业", "date": "2022.09 - 2026.07", "bullets": []}],
        },
    )

    assert "应用统计背景" in repaired["profile"]


def test_repair_parsed_schema_moves_project_like_items_out_of_internships():
    raw_text = "CareerOS 求职系统 产品与自动化实践 2026.04 - 至今"
    repaired = _repair_parsed_schema(
        raw_text,
        {
            "basics": {"name": "李默", "phone": "", "email": "", "target_role": "", "city": "", "availability": "", "photo": ""},
            "profile": "已有总结",
            "projects": [],
            "internships": [
                {"company": "CareerOS 求职系统", "role": "产品与自动化实践", "date": "2026.04 - 至今", "bullets": ["搭建工作流"]},
                {"company": "Fancy Tech", "role": "海外产品运营实习生", "date": "2024.06 - 2024.09", "bullets": ["负责内容增长"]},
            ],
            "skills": [],
            "education": [],
        },
    )

    assert len(repaired["projects"]) == 1
    assert repaired["projects"][0]["company"] == "CareerOS 求职系统"
    assert len(repaired["internships"]) == 1
    assert repaired["internships"][0]["company"] == "Fancy Tech"
