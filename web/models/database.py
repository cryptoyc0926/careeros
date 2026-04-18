"""
Career OS — Database Connection Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides a context-managed SQLite connection used by all modules.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import settings


def _get_db_path() -> Path:
    return settings.db_full_path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a configured SQLite connection with auto-commit/rollback."""
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row          # dict-like row access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return all rows as plain dicts (safe for .get())."""
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def execute(sql: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return lastrowid."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def executemany(sql: str, params_list: list[tuple]) -> None:
    """Run a batch operation."""
    with get_connection() as conn:
        conn.executemany(sql, params_list)


def sync_job_to_jd(job_pool_id: int, raw_text: str) -> int:
    """从 jobs_pool 同步到 job_descriptions，返回新建的 jd_id。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 公司, 岗位名称, 城市, 链接 FROM jobs_pool WHERE id = ?",
            (job_pool_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"jobs_pool id={job_pool_id} not found")

        cur = conn.execute(
            "INSERT INTO job_descriptions (company, title, location, raw_text, source_url, status, notes) "
            "VALUES (?, ?, ?, ?, ?, 'bookmarked', ?)",
            (row["公司"], row["岗位名称"], row["城市"], raw_text, row["链接"],
             f"来源:岗位池#{job_pool_id}"),
        )
        return cur.lastrowid


def get_jd_id_for_job(job_pool_id: int) -> int | None:
    """查询 jobs_pool 对应的 job_descriptions id（通过 notes 关联）。"""
    rows = query(
        "SELECT id FROM job_descriptions WHERE notes LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%岗位池#{job_pool_id}%",),
    )
    return rows[0]["id"] if rows else None


def has_resume_for_jd(jd_id: int) -> bool:
    """检查某个 JD 是否已生成简历。"""
    rows = query("SELECT COUNT(*) AS c FROM generated_resumes WHERE jd_id = ?", (jd_id,))
    return rows[0]["c"] > 0 if rows else False
