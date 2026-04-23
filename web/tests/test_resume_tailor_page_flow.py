from __future__ import annotations

import copy
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import resume_tailor  # noqa: E402
from services.ai_engine import AIError  # noqa: E402
from services.resume_validator import ValidationError, ValidationIssue, ValidationReport  # noqa: E402


PAGE = str(ROOT / "pages" / "resume_tailor.py")


def _button(at: AppTest, label: str):
    return next(button for button in at.button if button.label == label)


def _master_like(master: dict, *, profile: str, target_role: str | None = None, match_score: int = 0, change_notes: str = "") -> dict:
    basics = copy.deepcopy(master["basics"])
    if target_role:
        basics["target_role"] = target_role
    return {
        "basics": basics,
        "profile": profile,
        "projects": copy.deepcopy(master["projects"]),
        "internships": copy.deepcopy(master["internships"]),
        "skills": copy.deepcopy(master["skills"]),
        "education": copy.deepcopy(master["education"]),
        "_meta": {
            "match_score": match_score,
            "change_notes": change_notes,
            "jd_intent": {"target_role": target_role} if target_role else {},
        },
    }


def test_page_generate_success_updates_canvas_target_role(monkeypatch):
    def fake_tailor(master: dict, jd_text: str) -> dict:
        assert jd_text == "JD sample"
        return _master_like(
            master,
            profile="成功后的总结",
            target_role="海外增长运营",
            match_score=91,
            change_notes="success",
        )

    monkeypatch.setattr(resume_tailor, "tailor_resume", fake_tailor)

    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    at.text_area[0].set_value("JD sample").run()
    _button(at, "生成定制版").click().run()

    state = at.session_state.filtered_state
    assert state["tailor_data"]["profile"] == "成功后的总结"
    assert state["tailor_data"]["basics"]["target_role"] == "海外增长运营"
    assert state["tailor_meta"]["target_position"] == "海外增长运营"


def test_page_validation_draft_renders_canvas_and_can_rollback(monkeypatch):
    def fake_tailor(master: dict, jd_text: str) -> dict:
        draft = _master_like(
            master,
            profile="校验失败草稿",
            target_role="AI 内容运营",
            match_score=73,
            change_notes="draft",
        )
        report = ValidationReport(
            ok=False,
            hard_errors=[ValidationIssue("hard", "profile_rule", "profile", "too short")],
            warnings=[],
        )
        raise ValidationError(report, draft=draft, raw={"bad": True})

    monkeypatch.setattr(resume_tailor, "tailor_resume", fake_tailor)

    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    original_profile = at.session_state.filtered_state["tailor_data"]["profile"]
    at.text_area[0].set_value("JD sample").run()
    _button(at, "生成定制版").click().run()

    state = at.session_state.filtered_state
    assert state["tailor_data"]["profile"] == "校验失败草稿"
    assert state["tailor_meta"]["target_position"] == "AI 内容运营"
    assert "tailor_validation_error" in state
    assert any("草稿已渲染未保存" in caption.value for caption in at.caption)
    assert {button.label for button in at.button if button.label in {"忽略保存", "回退旧版"}} == {"忽略保存", "回退旧版"}

    _button(at, "回退旧版").click().run()

    rolled_back = at.session_state.filtered_state
    assert rolled_back["tailor_data"]["profile"] == original_profile
    assert "tailor_validation_error" not in rolled_back


def test_page_validation_draft_can_be_ignored_for_followup_save(monkeypatch):
    def fake_tailor(master: dict, jd_text: str) -> dict:
        draft = _master_like(
            master,
            profile="忽略保存草稿",
            target_role="AI 内容运营",
            match_score=68,
            change_notes="draft",
        )
        report = ValidationReport(
            ok=False,
            hard_errors=[ValidationIssue("hard", "profile_rule", "profile", "too short")],
            warnings=[],
        )
        raise ValidationError(report, draft=draft, raw={"bad": True})

    monkeypatch.setattr(resume_tailor, "tailor_resume", fake_tailor)

    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    at.text_area[0].set_value("JD sample").run()
    _button(at, "生成定制版").click().run()
    _button(at, "忽略保存").click().run()

    state = at.session_state.filtered_state
    assert "tailor_validation_error" not in state
    assert state["tailor_meta"]["validation_ignored"] is True
    assert state["tailor_data"]["profile"] == "忽略保存草稿"


def test_page_ai_error_uses_friendly_caption(monkeypatch):
    def fake_tailor(master: dict, jd_text: str) -> dict:
        raise AIError("HTTP 503 from upstream")

    monkeypatch.setattr(resume_tailor, "tailor_resume", fake_tailor)

    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    at.text_area[0].set_value("JD sample").run()
    _button(at, "生成定制版").click().run()

    captions = [caption.value for caption in at.caption]
    assert any("AI 服务暂不可用，请稍后重试" in caption for caption in captions)
    assert all("HTTP 503" not in caption for caption in captions)
