from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import resume_tailor  # noqa: E402
from services.resume_validator import ValidationError  # noqa: E402


MASTER = {
    "basics": {"name": "杨超", "target_role": "AI 增长运营"},
    "profile": {"pool": [{"id": "default", "tags": [], "text": "完整个人总结。"}], "default": "default"},
    "projects": [],
    "internships": [
        {
            "company": "Fancy Tech",
            "role": "海外产品运营实习生",
            "date": "2024.06 - 2024.09",
            "bullets": ["做到 10000+ 曝光"],
        }
    ],
    "skills": [],
    "education": [],
}


def test_tailor_validation_error_carries_draft(monkeypatch):
    bad_result = {
        "basics": {"target_role": "AI 增长运营"},
        "profile": "针对 JD 的新总结。",
        "projects": [],
        "internships": [
            {
                "company": "Fancy Tech Co",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": ["做到 10000+ 曝光"],
            }
        ],
        "skills": [],
        "match_score": 70,
        "change_notes": "测试",
    }

    monkeypatch.setattr(resume_tailor, "extract_jd_intent", lambda jd: {"target_role": "AI 增长运营", "top_keywords": []})
    monkeypatch.setattr(resume_tailor, "_call_claude", lambda **kwargs: json.dumps(bad_result, ensure_ascii=False))

    with pytest.raises(ValidationError) as exc:
        resume_tailor.tailor_resume(MASTER, "JD")

    assert exc.value.draft is not None
    assert exc.value.draft["profile"] == "针对 JD 的新总结。"
    assert exc.value.report.hard_errors


def test_tailor_succeeds_when_only_formatting_warnings_exist(monkeypatch):
    result = {
        "basics": {"target_role": "AI 增长运营"},
        "profile": "针对 JD 的新总结，保留 10000+ 曝光经验。",
        "projects": [],
        "internships": [
            {
                "company": "Fancy Tech",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": ["做到 10000+ 曝光"],
            }
        ],
        "skills": [],
        "match_score": 80,
        "change_notes": "测试",
    }

    monkeypatch.setattr(resume_tailor, "extract_jd_intent", lambda jd: {"target_role": "AI 增长运营", "top_keywords": []})
    monkeypatch.setattr(resume_tailor, "_call_claude", lambda **kwargs: json.dumps(result, ensure_ascii=False))

    tailored = resume_tailor.tailor_resume(MASTER, "JD")

    assert tailored["profile"].startswith("针对 JD")
    assert tailored["_meta"]["validation"]["warnings"]
    assert tailored["_meta"]["match_score"] == 80


def test_tailor_sets_target_role_from_jd_intent_when_model_omits_it(monkeypatch):
    result = {
        "basics": {},
        "profile": "针对 JD 的新总结，保留 10000+ 曝光经验。",
        "projects": [],
        "internships": [
            {
                "company": "Fancy Tech",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": ["做到 10000+ 曝光"],
            }
        ],
        "skills": [],
        "match_score": 82,
        "change_notes": "测试",
    }

    monkeypatch.setattr(
        resume_tailor,
        "extract_jd_intent",
        lambda jd: {"target_role": "海外增长运营", "top_keywords": []},
    )
    monkeypatch.setattr(resume_tailor, "_call_claude", lambda **kwargs: json.dumps(result, ensure_ascii=False))

    tailored = resume_tailor.tailor_resume(MASTER, "JD")

    assert tailored["basics"]["target_role"] == "海外增长运营"
    assert tailored["_meta"]["target_position"] == "海外增长运营"
