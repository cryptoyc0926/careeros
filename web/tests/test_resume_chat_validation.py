from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import resume_chat  # noqa: E402
from services.resume_validator import ValidationError, ValidationIssue, ValidationReport  # noqa: E402


def test_full_rewrite_validation_error_returns_reviewable_draft(monkeypatch):
    report = ValidationReport(
        ok=False,
        hard_errors=[
            ValidationIssue(
                severity="hard",
                rule="company_changed",
                location="internships[0].company",
                message="公司名被修改",
                expected="Fancy Tech",
                actual="Fancy Tech Co",
            )
        ],
    )
    draft = {"profile": "AI 已返回但未自动应用的草稿"}

    def fake_tailor_resume(_master, _jd_text):
        raise ValidationError(report, draft=draft, raw={"profile": draft["profile"]})

    monkeypatch.setattr(resume_chat, "tailor_resume", fake_tailor_resume)

    resp = resume_chat.handle_user_message(
        user_msg="根据 JD 整体重写",
        tailor_data={"profile": "旧版"},
        master={"profile": "主简历"},
        jd_text="JD 原文",
    )

    assert resp["intent"] == "validation_draft"
    assert resp["draft"] == draft
    assert resp["validation"]["hard_errors"][0]["rule"] == "company_changed"
    assert resp["error"] is None
