from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.init_db import init_database  # noqa: E402


PAGE = str(ROOT / "pages" / "home.py")


def _render_home(monkeypatch, db_path: Path) -> AppTest:
    monkeypatch.setenv("DB_PATH", str(db_path))
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    return at


def _markdown_blob(at: AppTest) -> str:
    return "\n".join(markdown.value for markdown in at.markdown)


def _insert_master_resume(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO resume_master (
                basics_json,
                profile_json,
                projects_json,
                internships_json,
                skills_json,
                education_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                json.dumps({"name": "Demo User", "target_role": "AI PM"}, ensure_ascii=False),
                json.dumps("一份主简历总结", ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_job(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            'INSERT INTO jobs_pool (公司, 岗位名称, 等级, 匹配分, status) VALUES (?, ?, ?, ?, ?)',
            ("Demo Corp", "AI Product Manager", "P0", 91, "NEW"),
        )
        conn.commit()
    finally:
        conn.close()


def test_home_shows_onboarding_cards_for_empty_db(monkeypatch, tmp_path):
    db_path = tmp_path / "home_empty.db"
    init_database(db_path)

    at = _render_home(monkeypatch, db_path)
    blob = _markdown_blob(at)

    assert "新手三步" in blob
    assert blob.index("新手三步") < blob.index("今天的进度")
    assert "1. 填主简历" in blob
    assert "2. 录第一个 JD" in blob
    assert "3. 定制简历" in blob
    assert "/master_resume?app=1" in blob
    assert "/jd_input?app=1" in blob
    assert "/resume_tailor?app=1" in blob
    assert "（先完成第 1 步）" in blob


def test_home_updates_onboarding_copy_when_master_resume_exists(monkeypatch, tmp_path):
    db_path = tmp_path / "home_master_only.db"
    init_database(db_path)
    _insert_master_resume(db_path)

    at = _render_home(monkeypatch, db_path)
    blob = _markdown_blob(at)

    assert "新手三步" in blob
    assert "✓ 已完成" in blob
    assert "（先完成第 1 步）" not in blob


def test_home_hides_onboarding_when_jobs_exist(monkeypatch, tmp_path):
    db_path = tmp_path / "home_with_jobs.db"
    init_database(db_path)
    _insert_job(db_path)

    at = _render_home(monkeypatch, db_path)
    blob = _markdown_blob(at)

    assert "新手三步" not in blob
