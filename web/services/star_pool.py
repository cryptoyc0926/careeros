"""STAR 素材池 (T3)

职责：
  1. 从 resume_master 一次性提取所有 bullets，AI 打标签后入 pending 队列（approved=0）
  2. CRUD：list / approve / update / delete / add
  3. 按 JD intent 召回最匹配的 top-N 候选（给 tailor prompt 使用）

标签维度（按 T3-Q3 你的决定）：
  - direction_tags: 岗位方向（AI增长 / 产品运营 / 数据运营 / 内容运营 / 用户增长 / 海外增长）
  - outcome_tags:   成果类型（用户数 / 收入 / 转化率 / 效率提升 / 品牌 / 成本 / 冷启动）
  - impact:         影响力（high / mid / low）

数据源：`star_pool` 表（2026-04-15 新增）
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import settings
from services.ai_engine import AIError, _call_claude

DB_PATH = settings.db_full_path

# ── 可选标签常量 ─────────────────────────────────────────
DIRECTION_TAGS = [
    "AI增长", "产品运营", "数据运营", "内容运营",
    "用户增长", "海外增长", "社区运营", "商业化",
]
OUTCOME_TAGS = [
    "用户数", "收入", "转化率", "效率提升",
    "品牌", "成本", "冷启动", "自动化",
]
IMPACT_LEVELS = ["high", "mid", "low"]


# ── 数据结构 ─────────────────────────────────────────────
@dataclass
class StarItem:
    id: int | None
    bullet_text: str
    source_type: str           # "project" | "internship" | "manual"
    source_company: str = ""
    source_index: int = 0
    direction_tags: list[str] = field(default_factory=list)
    outcome_tags: list[str] = field(default_factory=list)
    impact: str = "mid"
    approved: int = 0
    used_count: int = 0
    notes: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "StarItem":
        return cls(
            id=row["id"],
            bullet_text=row["bullet_text"],
            source_type=row["source_type"],
            source_company=row["source_company"] or "",
            source_index=row["source_index"] or 0,
            direction_tags=json.loads(row["direction_tags"] or "[]"),
            outcome_tags=json.loads(row["outcome_tags"] or "[]"),
            impact=row["impact"] or "mid",
            approved=row["approved"] or 0,
            used_count=row["used_count"] or 0,
            notes=row["notes"] or "",
        )

    def to_insert_tuple(self) -> tuple:
        return (
            self.bullet_text,
            self.source_type,
            self.source_company,
            self.source_index,
            json.dumps(self.direction_tags, ensure_ascii=False),
            json.dumps(self.outcome_tags, ensure_ascii=False),
            self.impact,
            self.approved,
            self.notes,
        )


# ── DB 操作 ──────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_items(approved: int | None = None, limit: int = 200) -> list[StarItem]:
    sql = "SELECT * FROM star_pool"
    args: tuple = ()
    if approved is not None:
        sql += " WHERE approved = ?"
        args = (approved,)
    sql += " ORDER BY approved ASC, impact DESC, id DESC LIMIT ?"
    args = args + (limit,)
    conn = _conn()
    try:
        rows = conn.execute(sql, args).fetchall()
        return [StarItem.from_row(r) for r in rows]
    finally:
        conn.close()


def insert_item(item: StarItem) -> int:
    conn = _conn()
    try:
        cur = conn.execute(
            """INSERT INTO star_pool
               (bullet_text, source_type, source_company, source_index,
                direction_tags, outcome_tags, impact, approved, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            item.to_insert_tuple(),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_item(item: StarItem) -> None:
    if not item.id:
        raise ValueError("update 需要 id")
    conn = _conn()
    try:
        conn.execute(
            """UPDATE star_pool SET
                bullet_text=?, direction_tags=?, outcome_tags=?,
                impact=?, approved=?, notes=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                item.bullet_text,
                json.dumps(item.direction_tags, ensure_ascii=False),
                json.dumps(item.outcome_tags, ensure_ascii=False),
                item.impact,
                item.approved,
                item.notes,
                item.id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_item(item_id: int) -> None:
    conn = _conn()
    try:
        conn.execute("DELETE FROM star_pool WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()


def bump_used(item_ids: list[int]) -> None:
    if not item_ids:
        return
    conn = _conn()
    try:
        conn.executemany(
            "UPDATE star_pool SET used_count = used_count + 1 WHERE id = ?",
            [(i,) for i in item_ids],
        )
        conn.commit()
    finally:
        conn.close()


def stats() -> dict:
    conn = _conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM star_pool").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM star_pool WHERE approved=0").fetchone()[0]
        approved = total - pending
        high = conn.execute("SELECT COUNT(*) FROM star_pool WHERE approved=1 AND impact='high'").fetchone()[0]
        return {"total": total, "pending": pending, "approved": approved, "high": high}
    finally:
        conn.close()


# ── AI 提取 + 打标签 ────────────────────────────────────
EXTRACT_SYSTEM = f"""你是简历素材提取器。输入一段 bullet，输出它的标签。

只从以下选项里选（多选，每类 1-3 个）：
direction_tags: {DIRECTION_TAGS}
outcome_tags:   {OUTCOME_TAGS}
impact:         {IMPACT_LEVELS}（high=结果量化显著且可验证；mid=有数据但不炸裂；low=过程性/无硬指标）

严格输出 JSON，不要解释：
{{"direction_tags": [...], "outcome_tags": [...], "impact": "high|mid|low"}}"""


def _tag_one(bullet: str) -> dict:
    try:
        raw = _call_claude(
            system_prompt=EXTRACT_SYSTEM,
            user_prompt=f"bullet：\n{bullet}",
            max_tokens=256,
            temperature=0.2,
        )
        t = raw.strip()
        if t.startswith("```"):
            t = "\n".join(t.split("\n")[1:-1])
        start, end = t.find("{"), t.rfind("}") + 1
        return json.loads(t[start:end])
    except Exception:
        return {"direction_tags": [], "outcome_tags": [], "impact": "mid"}


def extract_from_master(master: dict, replace: bool = False) -> list[int]:
    """一次性从 master 提取所有 project / internship bullets，入库 approved=0。

    replace=True 时先清空现有 pending（approved=0）条目。
    返回：新插入的 id 列表。
    """
    conn = _conn()
    try:
        if replace:
            conn.execute("DELETE FROM star_pool WHERE approved = 0")
            conn.commit()
    finally:
        conn.close()

    inserted: list[int] = []

    for section_key in ("projects", "internships"):
        source_type = "project" if section_key == "projects" else "internship"
        for idx, exp in enumerate(master.get(section_key, []) or []):
            company = exp.get("company", "")
            for bi, bullet in enumerate(exp.get("bullets", []) or []):
                tags = _tag_one(bullet)
                item = StarItem(
                    id=None,
                    bullet_text=bullet,
                    source_type=source_type,
                    source_company=company,
                    source_index=idx * 100 + bi,
                    direction_tags=tags.get("direction_tags", []),
                    outcome_tags=tags.get("outcome_tags", []),
                    impact=tags.get("impact", "mid"),
                    approved=0,
                    notes="auto-extracted from resume_master",
                )
                new_id = insert_item(item)
                inserted.append(new_id)

    return inserted


# ── 召回：按 JD intent 挑候选 ────────────────────────────
def find_best_matches(jd_intent: dict, n: int = 8) -> list[StarItem]:
    """按 JD intent 的 target_role / top_keywords 召回 approved 素材里最匹配的 top-N。

    简单评分：
      impact high=+3 mid=+1 low=0
      direction_tag 命中 JD target_role 字符串 +2
      outcome_tag 命中 JD top_keywords +1
      JD top_keyword 出现在 bullet_text +1
    """
    role = (jd_intent.get("target_role") or "").lower()
    keywords = [k.lower() for k in (jd_intent.get("top_keywords") or [])]

    items = list_items(approved=1, limit=500)
    scored: list[tuple[int, StarItem]] = []
    for it in items:
        score = 0
        score += {"high": 3, "mid": 1, "low": 0}.get(it.impact, 0)
        for t in it.direction_tags:
            if t and t.lower() in role:
                score += 2
        for t in it.outcome_tags:
            if any(k in t.lower() or t.lower() in k for k in keywords):
                score += 1
        text_low = it.bullet_text.lower()
        for k in keywords:
            if k and k in text_low:
                score += 1
        scored.append((score, it))

    scored.sort(key=lambda x: (-x[0], -x[1].used_count))
    return [it for s, it in scored[:n] if s > 0]


# ── CLI smoke test ─────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        for it in list_items():
            print(f"[{it.id}] approved={it.approved} impact={it.impact}")
            print(f"    dir={it.direction_tags} out={it.outcome_tags}")
            print(f"    {it.bullet_text[:100]}")
    else:
        print("usage: python star_pool.py [stats|list]")
