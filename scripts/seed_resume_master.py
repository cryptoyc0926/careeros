"""
seed_resume_master.py — 建表 + 灌入主简历示例数据
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
执行后：
  1. 创建 resume_master / resume_versions 表（幂等）
  2. 从 data/resume_master.example.json 读入示例主简历
  3. 可选：调用 resume_renderer 生成测试 PDF 到 /tmp/resume_seed_test.pdf

新用户首次使用推荐通过 UI「主简历」页面直接填写；此脚本用于：
  - 快速体验（先看看效果）
  - CI / 测试数据准备

用法：
    python scripts/seed_resume_master.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "career_os.db"
EXAMPLE_PATH = ROOT / "data" / "resume_master.example.json"


# ── 建表 SQL ─────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS resume_master (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    basics_json     TEXT NOT NULL,
    profile_json    TEXT NOT NULL,   -- {pool:[{id,tags,text}], default:"id"}
    projects_json   TEXT NOT NULL,
    internships_json TEXT NOT NULL,
    skills_json     TEXT NOT NULL,
    education_json  TEXT NOT NULL,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL,
    job_pool_id     INTEGER,
    target_role     TEXT,
    version_name    TEXT,
    content_json    TEXT NOT NULL,   -- 定制后完整 data dict
    match_score     INTEGER,
    pdf_path        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (master_id) REFERENCES resume_master(id),
    FOREIGN KEY (job_pool_id) REFERENCES jobs_pool(id)
);

CREATE INDEX IF NOT EXISTS idx_resume_versions_job
    ON resume_versions(job_pool_id);
"""


def _load_example() -> dict:
    """从 resume_master.example.json 读入示例数据，把扁平 profile 适配为 pool 结构。"""
    if not EXAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"找不到示例文件 {EXAMPLE_PATH}。\n"
            "请确认 data/resume_master.example.json 存在，或在 UI「主简历」页直接填写。"
        )
    raw = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    # 兼容简化 example（profile 是字符串）→ pool 结构
    profile_raw = raw.get("profile", "")
    if isinstance(profile_raw, str):
        profile = {
            "pool": [{"id": "default", "tags": [], "text": profile_raw}],
            "default": "default",
        }
    else:
        profile = profile_raw
    return {
        "basics": raw.get("basics", {}),
        "profile": profile,
        "projects": raw.get("projects", []),
        "internships": raw.get("internships", []),
        "skills": raw.get("skills", []),
        "education": raw.get("education", []),
    }


def build_render_data(master_row: dict) -> dict:
    """把 resume_master 行转成 renderer 需要的扁平 data dict。"""
    basics = json.loads(master_row["basics_json"])
    profile_pool = json.loads(master_row["profile_json"])
    default_id = profile_pool.get("default")
    profile_text = next(
        (p["text"] for p in profile_pool["pool"] if p["id"] == default_id),
        profile_pool["pool"][0]["text"],
    )
    return {
        "basics": basics,
        "profile": profile_text,
        "projects": json.loads(master_row["projects_json"]),
        "internships": json.loads(master_row["internships_json"]),
        "skills": json.loads(master_row["skills_json"]),
        "education": json.loads(master_row["education_json"]),
    }


def main() -> None:
    master_data = _load_example()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 建表
    cur.executescript(SCHEMA_SQL)

    # 2. 若已有数据，先清空（seed 是幂等的）
    cur.execute("DELETE FROM resume_master WHERE id = 1")

    cur.execute(
        """
        INSERT INTO resume_master
            (id, basics_json, profile_json, projects_json,
             internships_json, skills_json, education_json)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        """,
        (
            json.dumps(master_data["basics"], ensure_ascii=False),
            json.dumps(master_data["profile"], ensure_ascii=False),
            json.dumps(master_data["projects"], ensure_ascii=False),
            json.dumps(master_data["internships"], ensure_ascii=False),
            json.dumps(master_data["skills"], ensure_ascii=False),
            json.dumps(master_data["education"], ensure_ascii=False),
        ),
    )
    conn.commit()

    row = dict(cur.execute("SELECT * FROM resume_master WHERE id = 1").fetchone())
    conn.close()

    print(f"[OK] resume_master 已写入（来源：{EXAMPLE_PATH.name}）")
    print("[提示] 请到「主简历」页面替换为你自己的信息。")

    # 可选：渲染一份测试 PDF（失败不阻塞 seed）
    try:
        from web.services.resume_renderer import render_pdf

        out = render_pdf(build_render_data(row), output_path="/tmp/resume_seed_test.pdf")
        print(f"[OK] 测试 PDF: {out}")
    except Exception as e:
        print(f"[WARN] 测试 PDF 渲染失败（可忽略）：{e}")


if __name__ == "__main__":
    main()
