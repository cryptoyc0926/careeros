from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from services import resume_validator  # noqa: E402
from services.resume_validator import ValidationIssue  # noqa: E402


def test_format_validation_issue_markdown_accepts_dataclass_issue():
    issue = ValidationIssue(
        severity="hard",
        rule="company_changed",
        location="projects[0].company",
        message="公司名被修改",
        expected="AI Trading 社区搭建",
        actual="AI Trading Co",
    )

    formatter = getattr(resume_validator, "format_validation_issue_markdown", None)

    assert formatter is not None
    rendered = formatter(issue)

    assert "[company_changed]" in rendered
    assert "`projects[0].company`" in rendered
    assert "公司名被修改" in rendered
    assert "期望：`AI Trading 社区搭建`" in rendered
    assert "实际：`AI Trading Co`" in rendered


def test_format_validation_issue_markdown_accepts_dict_issue_for_legacy_state():
    issue = {
        "severity": "warn",
        "rule": "profile_length",
        "location": "profile",
        "message": "个人总结字数偏长",
        "expected": "70-130",
        "actual": "160",
    }

    formatter = getattr(resume_validator, "format_validation_issue_markdown", None)

    assert formatter is not None
    rendered = formatter(issue)

    assert "[profile_length]" in rendered
    assert "`profile`" in rendered
    assert "个人总结字数偏长" in rendered
