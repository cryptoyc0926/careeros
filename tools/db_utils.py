"""
Career OS — 共享数据库工具库
所有 subagent 通过此模块访问 SQLite
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

# 数据库路径（相对于项目根目录）
_DB_PATH: Optional[Path] = None

def get_db_path() -> Path:
    """自动发现数据库路径"""
    global _DB_PATH
    if _DB_PATH and _DB_PATH.exists():
        return _DB_PATH

    # 按优先级查找
    candidates = [
        Path("data/career_os.db"),
        Path("../data/career_os.db"),
        Path(__file__).parent.parent / "data" / "career_os.db",
    ]
    for p in candidates:
        if p.exists():
            _DB_PATH = p.resolve()
            return _DB_PATH

    # 不存在则创建
    default = Path(__file__).parent.parent / "data" / "career_os.db"
    default.parent.mkdir(parents=True, exist_ok=True)
    _DB_PATH = default
    return _DB_PATH


def connect() -> sqlite3.Connection:
    """获取数据库连接（带Row factory）"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# Jobs Pool CRUD
# ─────────────────────────────────────────────

def get_jobs(priority: str = None, status: str = None, limit: int = 100) -> pd.DataFrame:
    """获取岗位列表"""
    conn = connect()
    where_clauses = []
    params = []

    if priority:
        where_clauses.append("priority = ?")
        params.append(priority)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    else:
        where_clauses.append("status != '已排除'")

    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = f"SELECT * FROM jobs_pool {where} ORDER BY match_score DESC LIMIT ?"
    params.append(limit)

    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df


def upsert_job(job: dict) -> bool:
    """插入或忽略重复岗位，返回是否新增"""
    conn = connect()
    required = ['company', 'position']
    if not all(job.get(k) for k in required):
        return False

    fields = ['company', 'position', 'city', 'direction', 'priority', 'link_type',
              'apply_url', 'referral_code', 'publish_days', 'match_score',
              'action_today', 'status', 'source', 'notes']

    data = {k: job.get(k, '') for k in fields if k in job or k in ['company','position']}

    cols = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    conn.execute(
        f"INSERT OR IGNORE INTO jobs_pool ({cols}) VALUES ({placeholders})",
        list(data.values())
    )
    added = conn.execute("SELECT changes()").fetchone()[0] > 0
    conn.commit()
    conn.close()
    return added


def update_job_status(job_id: int, status: str, notes: str = ""):
    """更新岗位状态"""
    conn = connect()
    conn.execute("""
        UPDATE jobs_pool
        SET status = ?,
            notes = CASE WHEN notes = '' THEN ? ELSE notes || ' | ' || ? END,
            updated_at = datetime('now','localtime')
        WHERE id = ?
    """, (status, notes, notes, job_id))
    conn.commit()
    conn.close()


def get_today_new_jobs() -> pd.DataFrame:
    """获取今日新增岗位"""
    conn = connect()
    today = datetime.now().strftime('%Y-%m-%d')
    df = pd.read_sql(
        "SELECT * FROM jobs_pool WHERE date(created_at) = ? ORDER BY match_score DESC",
        conn, params=[today]
    )
    conn.close()
    return df


# ─────────────────────────────────────────────
# Contacts CRUD
# ─────────────────────────────────────────────

def get_contacts(priority: str = None, status: str = None) -> pd.DataFrame:
    """获取联系人列表"""
    conn = connect()
    where_clauses = []
    params = []

    if priority:
        where_clauses.append("priority LIKE ?")
        params.append(f"%{priority}%")
    if status:
        where_clauses.append("status = ?")
        params.append(status)

    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    df = pd.read_sql(f"SELECT * FROM contacts {where} ORDER BY priority, status", conn, params=params)
    conn.close()
    return df


def upsert_contact(contact: dict) -> bool:
    """插入联系人，返回是否新增"""
    conn = connect()
    if not contact.get('name') or not contact.get('company'):
        return False

    fields = ['name', 'company', 'role', 'contact_type', 'linkedin_url',
              'maimai_id', 'email', 'priority', 'status', 'message_template',
              'notes', 'verified_method']

    data = {k: contact.get(k, '') for k in fields}
    cols = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))

    conn.execute(
        f"INSERT OR IGNORE INTO contacts ({cols}) VALUES ({placeholders})",
        list(data.values())
    )
    added = conn.execute("SELECT changes()").fetchone()[0] > 0
    conn.commit()
    conn.close()
    return added


def update_contact_status(contact_id: int, status: str, notes: str = ""):
    """更新联系人触达状态"""
    conn = connect()
    conn.execute("""
        UPDATE contacts
        SET status = ?,
            last_action = ?,
            last_action_date = datetime('now','localtime'),
            notes = CASE WHEN notes = '' THEN ? ELSE notes || ' | ' || ? END
        WHERE id = ?
    """, (status, status, notes, notes, contact_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────

def get_summary_stats() -> dict:
    """获取全局统计数据"""
    conn = connect()
    stats = {}

    try:
        # 岗位统计
        rows = conn.execute("""
            SELECT priority, COUNT(*) as cnt
            FROM jobs_pool WHERE status != '已排除'
            GROUP BY priority
        """).fetchall()
        stats['jobs_by_priority'] = {r['priority']: r['cnt'] for r in rows}
        stats['total_jobs'] = sum(stats['jobs_by_priority'].values())

        # 联系人统计
        rows = conn.execute("""
            SELECT status, COUNT(*) as cnt FROM contacts GROUP BY status
        """).fetchall()
        stats['contacts_by_status'] = {r['status']: r['cnt'] for r in rows}
        stats['total_contacts'] = sum(stats['contacts_by_status'].values())

        # 已投递数
        stats['applied'] = conn.execute(
            "SELECT COUNT(*) FROM jobs_pool WHERE status = '已投递'"
        ).fetchone()[0]

        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        stats['today_new_jobs'] = conn.execute(
            "SELECT COUNT(*) FROM jobs_pool WHERE date(created_at) = ?", [today]
        ).fetchone()[0]

    except sqlite3.OperationalError:
        pass  # 表不存在时返回空统计

    conn.close()
    return stats


def export_to_excel(output_path: str = "data/jobs_pool.xlsx"):
    """导出岗位池到 Excel"""
    conn = connect()
    df = pd.read_sql("SELECT * FROM jobs_pool ORDER BY match_score DESC", conn)
    conn.close()

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df[df.status != '已排除'].to_excel(writer, sheet_name='岗位池', index=False)
        df[df.priority == 'P0'].to_excel(writer, sheet_name='P0优先', index=False)

        today = datetime.now().strftime('%Y-%m-%d')
        df[df.created_at.str.startswith(today)].to_excel(writer, sheet_name='今日新增', index=False)

    print(f"✅ 已导出: {output_path}")


def export_contacts_to_excel(output_path: str = "data/contacts.xlsx"):
    """导出联系人到 Excel"""
    conn = connect()
    df = pd.read_sql("SELECT * FROM contacts ORDER BY priority, status", conn)
    conn.close()

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='所有联系人', index=False)
        df[df.priority.str.contains('P0', na=False)].to_excel(writer, sheet_name='P0优先触达', index=False)
        df[df.contact_type == '校友'].to_excel(writer, sheet_name='浙工商校友', index=False)

    print(f"✅ 已导出: {output_path}")
