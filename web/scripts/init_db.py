#!/usr/bin/env python3
"""
Career OS — Database Initialisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Creates the SQLite database and all tables/views.
Safe to run multiple times (uses IF NOT EXISTS).

Usage:
    python scripts/init_db.py          # from project root
    python scripts/init_db.py --reset  # drop everything and recreate
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Allow running from project root or scripts/ dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings


# ═══════════════════════════════════════════════════════════════
# Schema Definition
# ═══════════════════════════════════════════════════════════════

TABLES_SQL = """
-- ──────────────────────────────────────────────
-- Job Descriptions: parsed and categorised JDs
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_descriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company         TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    location        TEXT,
    location_type   TEXT    CHECK(location_type IN ('remote', 'hybrid', 'onsite')),
    salary_min      INTEGER,
    salary_max      INTEGER,
    experience_min  INTEGER,
    experience_max  INTEGER,
    raw_text        TEXT    NOT NULL,
    parsed_json     TEXT,
    skills_required TEXT,
    skills_preferred TEXT,
    fit_score       REAL,
    source_url      TEXT,
    status          TEXT    DEFAULT 'bookmarked'
                    CHECK(status IN (
                        'bookmarked', 'resume_generated', 'applied',
                        'follow_up', 'interview', 'offer',
                        'rejected', 'withdrawn'
                    )),
    notes           TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- Generated Resumes: tailored output per JD
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generated_resumes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id             INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    resume_md         TEXT,
    resume_pdf_path   TEXT,
    cover_letter_md   TEXT,
    achievements_used TEXT,
    model_used        TEXT,
    prompt_hash       TEXT,
    version           INTEGER DEFAULT 1,
    created_at        TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- Applications: pipeline tracking
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id           INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    resume_id       INTEGER REFERENCES generated_resumes(id),
    applied_via     TEXT,
    applied_at      TEXT,
    follow_ups      TEXT,
    response        TEXT    CHECK(response IN ('none', 'rejected', 'interview', 'offer')),
    notes           TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- Interview Prep: generated materials
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interview_prep (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id           INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    questions_json  TEXT,
    cheatsheet_md   TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- Email Queue: outreach tracking
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER REFERENCES applications(id),
    recipient       TEXT    NOT NULL,
    subject         TEXT    NOT NULL,
    body_html       TEXT    NOT NULL,
    template_id     TEXT,
    scheduled_at    TEXT,
    sent_at         TEXT,
    status          TEXT    DEFAULT 'draft'
                    CHECK(status IN ('draft', 'queued', 'sent', 'failed')),
    sequence_step   INTEGER DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- Schema Migrations: track applied migrations
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS _migrations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    applied_at      TEXT    DEFAULT (datetime('now'))
);

-- ══════════════════════════════════════════════════════════════
-- 扩展业务表（历史遗留使用中文字段，保持不变以兼容代码 SQL）
-- ══════════════════════════════════════════════════════════════

-- 岗位池（核心表：所有页面依赖）
CREATE TABLE IF NOT EXISTS jobs_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    序号 INTEGER,
    公司 TEXT NOT NULL,
    岗位名称 TEXT NOT NULL,
    城市 TEXT,
    方向分类 TEXT,
    等级 TEXT,
    匹配分 REAL,
    技能匹配 REAL,
    经历相关 REAL,
    面试概率 REAL,
    成长价值 REAL,
    投递档位 TEXT,
    发布时间 TEXT,
    时间等级 TEXT,
    来源平台 TEXT,
    链接 TEXT,
    核心匹配点 TEXT,
    短板 TEXT,
    招聘类型 TEXT,
    今日行动 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'NEW',
    link_type TEXT DEFAULT '门户入口',
    applied_date TEXT,
    apply_channel TEXT,
    last_followup TEXT,
    followup_count INTEGER DEFAULT 0,
    credibility TEXT DEFAULT '中',
    jd_fetch_mode TEXT DEFAULT 'auto',
    jd_status TEXT DEFAULT 'pending',
    jd_last_error TEXT,
    jd_fetched_at TEXT
);

-- 主简历
CREATE TABLE IF NOT EXISTS resume_master (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    basics_json     TEXT NOT NULL,
    profile_json    TEXT NOT NULL,
    projects_json   TEXT NOT NULL,
    internships_json TEXT NOT NULL,
    skills_json     TEXT NOT NULL,
    education_json  TEXT NOT NULL,
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 定制简历版本
CREATE TABLE IF NOT EXISTS resume_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id       INTEGER NOT NULL,
    job_pool_id     INTEGER,
    target_role     TEXT,
    version_name    TEXT,
    content_json    TEXT NOT NULL,
    match_score     INTEGER,
    pdf_path        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (master_id) REFERENCES resume_master(id),
    FOREIGN KEY (job_pool_id) REFERENCES jobs_pool(id)
);

-- STAR 素材池
CREATE TABLE IF NOT EXISTS star_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bullet_text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_company TEXT,
    source_index INTEGER,
    direction_tags TEXT,
    outcome_tags TEXT,
    impact TEXT DEFAULT 'mid',
    approved INTEGER DEFAULT 0,
    used_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- STAR 故事库
CREATE TABLE IF NOT EXISTS star_stories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    situation TEXT,
    task TEXT,
    action TEXT,
    result TEXT,
    tags TEXT,
    used_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- JD 深度评估结果
CREATE TABLE IF NOT EXISTS jd_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_pool_id INTEGER,
    resume_version_id INTEGER,
    jd_hash TEXT,
    target_role TEXT,
    overall_score INTEGER,
    eval_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id)
);

-- 面试题库
CREATE TABLE IF NOT EXISTS interview_qa (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    source_jd TEXT,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 联系人
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    role TEXT DEFAULT '',
    contact_type TEXT DEFAULT 'HR',
    linkedin_url TEXT DEFAULT '',
    maimai_id TEXT DEFAULT '',
    email TEXT DEFAULT '',
    priority TEXT DEFAULT 'P2',
    status TEXT DEFAULT '待触达',
    last_action TEXT DEFAULT '',
    last_action_date TEXT DEFAULT '',
    message_template TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    verified_method TEXT DEFAULT 'WebSearch',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(name, company)
);

-- LinkedIn 线索（可选）
CREATE TABLE IF NOT EXISTS linkedin_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    first_name TEXT,
    profile_url TEXT NOT NULL UNIQUE,
    company TEXT,
    title TEXT,
    city TEXT,
    persona TEXT,
    priority INTEGER DEFAULT 2,
    source TEXT,
    status TEXT DEFAULT 'NEW',
    greeting_lang TEXT,
    greeting_rendered TEXT,
    discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_jd_status       ON job_descriptions(status);
CREATE INDEX IF NOT EXISTS idx_jd_company      ON job_descriptions(company);
CREATE INDEX IF NOT EXISTS idx_jd_fit_score    ON job_descriptions(fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_jd_created      ON job_descriptions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_resumes_jd      ON generated_resumes(jd_id);
CREATE INDEX IF NOT EXISTS idx_apps_jd         ON applications(jd_id);
CREATE INDEX IF NOT EXISTS idx_email_status    ON email_queue(status);
CREATE INDEX IF NOT EXISTS idx_email_scheduled ON email_queue(scheduled_at);
"""

VIEWS_SQL = """
-- Application funnel metrics
CREATE VIEW IF NOT EXISTS v_application_funnel AS
SELECT
    status,
    COUNT(*)                                                           AS count,
    ROUND(COUNT(*) * 100.0 / MAX((SELECT COUNT(*) FROM job_descriptions), 1), 1) AS pct
FROM job_descriptions
GROUP BY status
ORDER BY CASE status
    WHEN 'bookmarked'        THEN 1
    WHEN 'resume_generated'  THEN 2
    WHEN 'applied'           THEN 3
    WHEN 'follow_up'         THEN 4
    WHEN 'interview'         THEN 5
    WHEN 'offer'             THEN 6
    WHEN 'rejected'          THEN 7
    WHEN 'withdrawn'         THEN 8
END;

-- Skill demand frequency (across all JDs)
CREATE VIEW IF NOT EXISTS v_skill_demand AS
SELECT
    value                  AS skill,
    COUNT(*)               AS demand_count
FROM job_descriptions, json_each(job_descriptions.skills_required)
WHERE skills_required IS NOT NULL
GROUP BY value
ORDER BY demand_count DESC;

-- Recent activity timeline
CREATE VIEW IF NOT EXISTS v_recent_activity AS
SELECT
    'jd_added'    AS event_type,
    company || ' — ' || title AS description,
    created_at    AS event_time
FROM job_descriptions
UNION ALL
SELECT
    'resume_gen'  AS event_type,
    'v' || version || ' for JD #' || jd_id AS description,
    created_at    AS event_time
FROM generated_resumes
UNION ALL
SELECT
    'email_sent'  AS event_type,
    subject       AS description,
    sent_at       AS event_time
FROM email_queue
WHERE sent_at IS NOT NULL
ORDER BY event_time DESC
LIMIT 50;
"""

TRIGGERS_SQL = """
-- Auto-update the updated_at timestamp on job_descriptions
CREATE TRIGGER IF NOT EXISTS trg_jd_updated_at
AFTER UPDATE ON job_descriptions
FOR EACH ROW
BEGIN
    UPDATE job_descriptions SET updated_at = datetime('now') WHERE id = OLD.id;
END;
"""


# ═══════════════════════════════════════════════════════════════
# Execution
# ═══════════════════════════════════════════════════════════════

def init_database(db_path: Path, *, reset: bool = False) -> None:
    """Create (or recreate) the Career OS database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if reset and db_path.exists():
        db_path.unlink()
        print(f"  Deleted existing database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")      # better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")        # enforce FK constraints

    print(f"  Database: {db_path}")
    print(f"  Creating tables …")
    conn.executescript(TABLES_SQL)

    print(f"  Creating indexes …")
    conn.executescript(INDEXES_SQL)

    print(f"  Creating views …")
    conn.executescript(VIEWS_SQL)

    print(f"  Creating triggers …")
    conn.executescript(TRIGGERS_SQL)

    # Record initial migration
    conn.execute(
        "INSERT OR IGNORE INTO _migrations(name) VALUES (?)",
        ("001_initial_schema",),
    )
    conn.commit()

    # Verify
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    views = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    ).fetchall()

    print(f"\n  Tables ({len(tables)}): {', '.join(t[0] for t in tables)}")
    print(f"  Views  ({len(views)}): {', '.join(v[0] for v in views)}")
    print(f"\n  Database initialised successfully.")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Initialise Career OS database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the database from scratch",
    )
    args = parser.parse_args()

    db_path = settings.db_full_path
    print(f"\nCareer OS — Database Init")
    print(f"{'=' * 40}")
    init_database(db_path, reset=args.reset)


if __name__ == "__main__":
    main()
