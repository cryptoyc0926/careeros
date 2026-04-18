"""
LinkedIn Lead Finder — CareerOS Phase B
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

目的：用 WebSearch（不是浏览器）发现目标 LinkedIn profiles，写入 `linkedin_leads` 表供人工批准。

调用链：
  Claude 在对话里用 WebSearch 执行查询
    → 用户/Claude 把搜索结果交给 ingest_search_results()
    → 本模块解析、过滤、去重、匹配人设、渲染招呼语、入库 NEW 状态

设计原则：
  - 纯函数 + DB，无浏览器依赖（浏览器阶段在 Phase D）
  - 所有 lead 默认 status='NEW'，必须用户显式 approve 才会进入发送队列
  - 硬过滤黑名单（字节/蚂蚁/腾讯/网易）在入库前就执行
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 允许作为 module 或 script 运行
_THIS_DIR = Path(__file__).resolve().parent
_WEB_DIR = _THIS_DIR.parent
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from config import settings  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
TARGETS_YAML = _ROOT / "data" / "linkedin_targets.yaml"
GREETINGS_YAML = _ROOT / "data" / "linkedin_greetings.yaml"


# ── 数据结构 ────────────────────────────────────────
@dataclass
class RawHit:
    """一条 WebSearch / 人工粘贴的原始结果。"""
    url: str
    title: str = ""      # e.g. "Zhang Wei - Growth Ops at MiniMax | LinkedIn"
    snippet: str = ""    # 搜索结果的摘要片段


@dataclass
class ParsedLead:
    full_name: str
    profile_url: str
    company: str = ""
    title: str = ""
    city: str = ""
    persona: str = ""
    priority: int = 2
    source: str = "websearch"


@dataclass
class FindStats:
    total_hits: int = 0
    parsed: int = 0
    excluded_blacklist: int = 0
    excluded_wrong_persona: int = 0
    duplicated: int = 0
    inserted: int = 0
    errors: list[str] = field(default_factory=list)


# ── 配置加载 ────────────────────────────────────────
def load_targets() -> dict:
    if not TARGETS_YAML.exists():
        raise FileNotFoundError(f"缺少 {TARGETS_YAML}")
    return yaml.safe_load(TARGETS_YAML.read_text(encoding="utf-8"))


def load_greetings() -> dict:
    if not GREETINGS_YAML.exists():
        raise FileNotFoundError(f"缺少 {GREETINGS_YAML}")
    return yaml.safe_load(GREETINGS_YAML.read_text(encoding="utf-8"))


# ── 解析 ────────────────────────────────────────────
_LINKEDIN_URL_RE = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[^/?\s]+")
_TITLE_RE = re.compile(r"^(?P<name>[^\-|·|]+?)\s*[-|·|]\s*(?P<rest>.+?)(?:\s*\|\s*LinkedIn)?$")


def parse_hit(hit: RawHit) -> ParsedLead | None:
    """把一条原始搜索结果解析成 ParsedLead。解析不出来返回 None。"""
    url_match = _LINKEDIN_URL_RE.search(hit.url or "")
    if not url_match:
        return None
    profile_url = url_match.group(0).rstrip("/")

    name, rest = "", ""
    if hit.title:
        m = _TITLE_RE.match(hit.title.strip())
        if m:
            name = m.group("name").strip()
            rest = m.group("rest").strip()

    if not name:
        # 从 URL 兜底
        slug = profile_url.rsplit("/", 1)[-1]
        name = slug.replace("-", " ").title()

    # 从 rest 粗提取 title / company
    title, company = "", ""
    if rest:
        # "Growth Ops at MiniMax" / "Growth @ MiniMax" / "HR, MiniMax"
        at_split = re.split(r"\s+(?:at|@|,)\s+", rest, maxsplit=1)
        if len(at_split) == 2:
            title, company = at_split[0].strip(), at_split[1].strip()
        else:
            title = rest

    # 从 snippet 兜底抓 city
    city = ""
    if hit.snippet:
        for kw in ["Hangzhou", "Shanghai", "Beijing", "Shenzhen", "杭州", "上海", "北京", "深圳"]:
            if kw in hit.snippet:
                city = kw
                break

    return ParsedLead(
        full_name=name,
        profile_url=profile_url,
        company=company,
        title=title,
        city=city,
    )


# ── 人设匹配 ────────────────────────────────────────
def match_persona(lead: ParsedLead, config: dict) -> tuple[str, int] | None:
    """按 linkedin_targets.yaml 的 persona_rules 匹配人设。返回 (persona, priority)。"""
    rules = config.get("persona_rules", {})
    text = f"{lead.title} {lead.company} {lead.full_name}".lower()

    best = None  # (persona, priority)
    for persona_key, rule in rules.items():
        match_kw = [k.lower() for k in rule.get("match_keywords", [])]
        excl_kw = [k.lower() for k in rule.get("exclude_keywords", [])]

        if any(ex in text for ex in excl_kw):
            continue
        if not any(kw in text for kw in match_kw):
            continue

        pr = int(rule.get("priority", 9))
        if best is None or pr < best[1]:
            best = (persona_key, pr)

    return best


def is_blacklisted(lead: ParsedLead, config: dict) -> bool:
    blacklist = [c.lower() for c in config.get("hard_exclude", {}).get("companies", [])]
    target = lead.company.lower()
    return any(b in target for b in blacklist)


# ── DB ──────────────────────────────────────────────
def _conn():
    return sqlite3.connect(settings.db_full_path)


def is_duplicate(profile_url: str) -> bool:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id FROM linkedin_leads WHERE profile_url = ? LIMIT 1",
            (profile_url,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def insert_lead(lead: ParsedLead, greeting_lang: str, greeting_rendered: str) -> int:
    conn = _conn()
    try:
        first_name = (lead.full_name or "").split()[0] if lead.full_name else ""
        cur = conn.execute(
            '''INSERT INTO linkedin_leads
               (full_name, first_name, profile_url, company, title, city,
                persona, priority, source, status,
                greeting_lang, greeting_rendered, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?, ?)''',
            (
                lead.full_name, first_name, lead.profile_url,
                lead.company, lead.title, lead.city,
                lead.persona, lead.priority, lead.source,
                greeting_lang, greeting_rendered,
                f"auto-found {datetime.now().strftime('%Y-%m-%d')}",
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── Greeting 渲染 ───────────────────────────────────
def render_greeting(lead: ParsedLead, persona: str, lang: str, greetings: dict) -> str:
    tmpl = greetings.get("personas", {}).get(persona, {}).get(lang, "")
    if not tmpl:
        return ""
    first_name = (lead.full_name or "").split()[0] if lead.full_name else "there"
    称呼 = first_name  # 中文也用 first_name 兜底
    return (
        tmpl.replace("{first_name}", first_name)
            .replace("{company}", lead.company or "your company")
            .replace("{topic}", "growth & automation")
            .replace("{称呼}", 称呼)
            .strip()
    )


# ── 主入口 ──────────────────────────────────────────
def ingest_search_results(
    hits: list[RawHit],
    default_lang: str = "en",
) -> FindStats:
    """
    把一批原始搜索结果解析、过滤、匹配人设、渲染招呼语、入库。
    所有 lead 默认 status='NEW'，不会主动发送。
    """
    config = load_targets()
    greetings = load_greetings()
    stats = FindStats(total_hits=len(hits))

    for hit in hits:
        try:
            lead = parse_hit(hit)
            if not lead:
                stats.errors.append(f"parse failed: {hit.url}")
                continue
            stats.parsed += 1

            if is_blacklisted(lead, config):
                stats.excluded_blacklist += 1
                continue

            matched = match_persona(lead, config)
            if matched is None:
                stats.excluded_wrong_persona += 1
                continue
            lead.persona, lead.priority = matched

            if is_duplicate(lead.profile_url):
                stats.duplicated += 1
                continue

            greeting = render_greeting(lead, lead.persona, default_lang, greetings)
            insert_lead(lead, default_lang, greeting)
            stats.inserted += 1
        except Exception as e:
            stats.errors.append(f"{hit.url}: {e}")

    return stats


# ── 查询辅助 ────────────────────────────────────────
def pending_leads(limit: int = 20) -> list[dict]:
    """列出待批准的 NEW leads（供用户审核）。"""
    conn = _conn()
    try:
        rows = conn.execute(
            '''SELECT id, full_name, profile_url, company, title, city,
                      persona, priority, greeting_lang, greeting_rendered
               FROM linkedin_leads
               WHERE status = 'NEW'
               ORDER BY priority ASC, discovered_at DESC
               LIMIT ?''',
            (limit,),
        ).fetchall()
        cols = ["id","full_name","profile_url","company","title","city",
                "persona","priority","greeting_lang","greeting_rendered"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def approve_leads(ids: list[int]) -> int:
    conn = _conn()
    try:
        cur = conn.execute(
            f"UPDATE linkedin_leads SET status='APPROVED', last_updated_at=CURRENT_TIMESTAMP "
            f"WHERE id IN ({','.join('?'*len(ids))}) AND status='NEW'",
            ids,
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ── CLI ─────────────────────────────────────────────
def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="LinkedIn Lead Finder")
    sub = ap.add_subparsers(dest="cmd")

    ing = sub.add_parser("ingest", help="从 JSON 文件导入原始 hits")
    ing.add_argument("json_file", type=Path)
    ing.add_argument("--lang", default="en", choices=["en", "cn"])

    sub.add_parser("pending", help="列出待批准 leads")

    apv = sub.add_parser("approve", help="批准 lead ids")
    apv.add_argument("ids", nargs="+", type=int)

    args = ap.parse_args()

    if args.cmd == "ingest":
        raw = json.loads(args.json_file.read_text(encoding="utf-8"))
        hits = [RawHit(**r) for r in raw]
        stats = ingest_search_results(hits, default_lang=args.lang)
        print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "pending":
        rows = pending_leads()
        print(f"共 {len(rows)} 条待批准：")
        for r in rows:
            print(f"  [{r['id']}] {r['full_name']} — {r['title']} @ {r['company']} ({r['persona']})")
            print(f"       {r['profile_url']}")
            print(f"       > {r['greeting_rendered'][:120]}")
        return 0

    if args.cmd == "approve":
        n = approve_leads(args.ids)
        print(f"approved {n} leads")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
