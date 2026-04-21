"""
一次性数据清洗：从 DB 删除排除公司记录。

触发来源：Codex 审查 #6 — jobs_pool / job_descriptions 中残留字节/腾讯/蚂蚁/网易。
规则来源：CLAUDE.md §目标公司 → 明确排除 + web/services/job_filter.EXCLUDED_COMPANIES

用法：
    cd career-os-claudecode
    python scripts/clean_excluded_companies.py --dry-run   # 先看会删什么
    python scripts/clean_excluded_companies.py             # 实删（自动备份）

安全：
    - 执行前自动备份到 data/career_os.db.bak_<timestamp>（CLAUDE.md §数据操作规则）
    - --dry-run 只预览不修改
    - applications/generated_resumes 通过 ON DELETE CASCADE 跟随 job_descriptions 清理
"""

from __future__ import annotations
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 让脚本能 import web/services
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from services.job_filter import is_excluded_company  # noqa: E402


DB_PATH = ROOT / "data" / "career_os.db"


def backup_db() -> Path:
    """备份 DB，返回备份文件路径。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"career_os.db.bak_{ts}")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def find_excluded(conn: sqlite3.Connection) -> tuple[list[tuple], list[tuple]]:
    """返回 (jobs_pool_rows, job_descriptions_rows) 中的待删记录。"""
    cur = conn.cursor()

    cur.execute("SELECT id, 公司, 岗位名称 FROM jobs_pool")
    jp_rows = [(rid, company, title) for rid, company, title in cur.fetchall()
               if is_excluded_company(company)]

    cur.execute("SELECT id, company, title FROM job_descriptions")
    jd_rows = [(rid, company, title) for rid, company, title in cur.fetchall()
               if is_excluded_company(company)]

    return jp_rows, jd_rows


def delete_rows(conn: sqlite3.Connection, jp_ids: list[int], jd_ids: list[int]) -> None:
    cur = conn.cursor()
    # 启用外键（确保 CASCADE 生效）
    cur.execute("PRAGMA foreign_keys = ON")

    if jp_ids:
        cur.executemany("DELETE FROM jobs_pool WHERE id = ?", [(i,) for i in jp_ids])
    if jd_ids:
        cur.executemany("DELETE FROM job_descriptions WHERE id = ?", [(i,) for i in jd_ids])

    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只预览，不实际删除")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERR] DB not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        jp_rows, jd_rows = find_excluded(conn)

        print(f"\n=== 排除公司命中扫描 ===")
        print(f"jobs_pool:        {len(jp_rows)} 条")
        for rid, company, title in jp_rows:
            print(f"  #{rid}  {company}  ·  {title}")
        print(f"job_descriptions: {len(jd_rows)} 条")
        for rid, company, title in jd_rows:
            print(f"  #{rid}  {company}  ·  {title}")

        if not jp_rows and not jd_rows:
            print("\n[OK] 无需清理，DB 干净。")
            return 0

        if args.dry_run:
            print("\n[DRY-RUN] 已预览，未执行删除。去掉 --dry-run 真删。")
            return 0

        backup = backup_db()
        print(f"\n[BACKUP] {backup}")

        delete_rows(
            conn,
            [r[0] for r in jp_rows],
            [r[0] for r in jd_rows],
        )

        # 复核
        jp_after, jd_after = find_excluded(conn)
        print(f"\n=== 清洗后复核 ===")
        print(f"jobs_pool:        {len(jp_after)} 条")
        print(f"job_descriptions: {len(jd_after)} 条")

        if jp_after or jd_after:
            print("[WARN] 仍有残留，请检查关键字覆盖。")
            return 2

        print("\n[DONE] 清洗完成。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
