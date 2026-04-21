"""
数据导出 / 导入（本地同步）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
设计目的：Streamlit Cloud 文件系统只读，数据无法持久化。
让用户通过「下载/上传 JSON 文件」手动保存 - 恢复数据。

用户侧流程：
  1. 每次用完点「导出所有数据」 → 浏览器下载 careeros_backup_YYYYMMDD.json
  2. 把这个文件保存到本地文件夹（iCloud / OneDrive / 任何同步盘都行）
  3. 下次打开应用 → 点「从文件导入」 → 选刚刚的文件 → 所有数据恢复
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


# 需要备份的表清单（核心业务数据）
EXPORTABLE_TABLES = [
    "jobs_pool",
    "job_descriptions",
    "generated_resumes",
    "applications",
    "resume_master",
    "resume_versions",
    "star_pool",
    "star_stories",
    "interview_prep",
    "interview_qa",
    "jd_evaluations",
    "email_queue",
    "contacts",
]


def export_all_data(db_path: Path, user_profile: dict | None = None) -> dict:
    """导出所有表为 JSON-serializable dict。

    返回格式：
    {
      "_meta": {
        "exported_at": "2026-04-18T12:34:56",
        "schema_version": 1,
        "app": "CareerOS"
      },
      "user_profile": {...},
      "tables": {
        "jobs_pool": [{...}, {...}],
        "resume_master": [{...}],
        ...
      }
    }
    """
    if not db_path.exists():
        return {"_meta": _meta(), "user_profile": user_profile or {}, "tables": {}}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tables_data: dict[str, list[dict]] = {}

    # 获取所有现有表
    existing = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()}

    for tbl in EXPORTABLE_TABLES:
        if tbl not in existing:
            continue
        rows = conn.execute(f"SELECT * FROM {tbl}").fetchall()
        tables_data[tbl] = [dict(r) for r in rows]

    conn.close()
    return {
        "_meta": _meta(),
        "user_profile": user_profile or {},
        "tables": tables_data,
    }


def import_all_data(db_path: Path, payload: dict, mode: str = "merge") -> dict:
    """把 JSON payload 导入回数据库。

    mode:
      - "merge": 合并（跳过冲突行）
      - "replace": 清空对应表后重新插入（危险，会丢失现有数据）

    返回：每个表导入的行数。
    """
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在：{db_path}")
    if mode not in ("merge", "replace"):
        raise ValueError(f"mode 必须是 merge/replace，收到 {mode}")

    tables = payload.get("tables", {})
    stats: dict[str, int] = {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for tbl, rows in tables.items():
            if not rows or tbl not in EXPORTABLE_TABLES:
                stats[tbl] = 0
                continue

            # 获取目标表的现有列（避免插入陌生字段）
            cols_info = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
            valid_cols = {c[1] for c in cols_info}
            if not valid_cols:
                stats[tbl] = 0
                continue

            if mode == "replace":
                conn.execute(f"DELETE FROM {tbl}")

            inserted = 0
            for row in rows:
                # 只保留目标表真实存在的列
                filtered = {k: v for k, v in row.items() if k in valid_cols and k != "id"}
                if not filtered:
                    continue
                cols = ", ".join(f"[{k}]" for k in filtered.keys())
                placeholders = ", ".join("?" * len(filtered))
                try:
                    conn.execute(
                        f"INSERT OR IGNORE INTO {tbl} ({cols}) VALUES ({placeholders})",
                        list(filtered.values()),
                    )
                    inserted += 1
                except sqlite3.Error:
                    # 单行失败不阻塞整批
                    continue
            stats[tbl] = inserted
        conn.commit()
    finally:
        conn.close()
    return stats


def _meta() -> dict[str, Any]:
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "schema_version": 1,
        "app": "CareerOS",
    }
