#!/usr/bin/env python3
"""
Migration · Phase 2
~~~~~~~~~~~~~~~~~~~~
给 resume_master 添加 original_docx_blob（存 DOCX 原始字节）；
给 resume_versions 添加 chat_transcript_json（保存定制时的 chat 流水）。

幂等：多次运行安全（检测列已存在则跳过）。

Usage:
    python scripts/migrate_add_docx_blob_and_chat.py
    python scripts/migrate_add_docx_blob_and_chat.py --db /path/to/career_os.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def migrate(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[!] 数据库不存在：{db_path}")
        sys.exit(1)
    print(f"[*] Migrating: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        rm_cols = _columns(conn, "resume_master")
        if "original_docx_blob" in rm_cols:
            print("  [skip] resume_master.original_docx_blob already exists")
        else:
            conn.execute("ALTER TABLE resume_master ADD COLUMN original_docx_blob BLOB")
            print("  [+] resume_master.original_docx_blob BLOB")

        if "original_docx_filename" in rm_cols:
            print("  [skip] resume_master.original_docx_filename already exists")
        else:
            conn.execute("ALTER TABLE resume_master ADD COLUMN original_docx_filename TEXT")
            print("  [+] resume_master.original_docx_filename TEXT")

        rv_cols = _columns(conn, "resume_versions")
        if "chat_transcript_json" in rv_cols:
            print("  [skip] resume_versions.chat_transcript_json already exists")
        else:
            conn.execute("ALTER TABLE resume_versions ADD COLUMN chat_transcript_json TEXT")
            print("  [+] resume_versions.chat_transcript_json TEXT")

        conn.execute(
            "INSERT OR IGNORE INTO _migrations(name) VALUES (?)",
            ("002_docx_blob_and_chat_transcript",),
        )
        conn.commit()
        print("[OK] migration done")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=None,
                        help="SQLite 数据库路径，默认读 config.settings.db_full_path")
    args = parser.parse_args()

    db = args.db
    if db is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
        from config import settings  # type: ignore
        db = settings.db_full_path
    migrate(Path(db))


if __name__ == "__main__":
    main()
