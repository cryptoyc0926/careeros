"""
Job Crawler — CareerOS Phase 2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
输入：一批 (company, position, city, url) 元组（来自每日 9 点定时扫描任务的 WebSearch 结果）
输出：过滤黑名单 → 抓取 JD 全文 → 打匹配分 → 去重入库 `jobs_pool`

调用方：
  - 定时任务 `careeros-daily-job-scan`（Claude 每天 9 点跑）
  - CLI: `python -m services.job_crawler --from-json path.json`
  - 未来 `web/pages/job_pool.py` 的「🔄 一键扫描」按钮

设计哲学：
  - 纯函数、无 Streamlit 依赖（方便 cron / Claude 调用）
  - 容错：单条失败不影响整批
  - 所有行为有日志
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, asdict, field
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

# ── 常量 ─────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
TARGETS_YAML = _ROOT / "data" / "target_companies.yaml"
REPORTS_DIR = _ROOT / "reports"


# ── 数据结构 ─────────────────────────────────────────
@dataclass
class JobLead:
    """一条待爬取的岗位线索（定时任务 WebSearch 产出）。"""
    company: str
    position: str
    city: str = ""
    url: str = ""
    priority: str = "P1"       # P0 / P1 / P2
    source: str = "WebSearch"  # WebSearch / LinkedIn / Moka / 飞书 / ...
    direction: str = ""        # 增长运营 / 产品运营 / 数据运营 / ...


@dataclass
class CrawlStats:
    total: int = 0
    excluded: int = 0
    duplicated: int = 0
    scrape_failed: int = 0
    inserted: int = 0
    top_matches: list[dict] = field(default_factory=list)  # [{company, position, city, score, url}]
    excluded_reasons: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── 目标池 & 黑名单 ──────────────────────────────────
def load_targets(path: Path | None = None) -> dict:
    """读 target_companies.yaml，返回完整字典。"""
    p = path or TARGETS_YAML
    if not p.exists():
        raise FileNotFoundError(f"目标公司池不存在：{p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_excluded(path: Path | None = None) -> set[str]:
    """返回小写去空格的黑名单词集合。"""
    data = load_targets(path)
    raw = data.get("excluded", [])
    return {s.strip().lower() for s in raw if s}


def is_excluded(company: str, excluded: set[str] | None = None) -> bool:
    """公司名是否命中黑名单（子串匹配，大小写不敏感）。"""
    if excluded is None:
        excluded = load_excluded()
    name = (company or "").strip().lower()
    if not name:
        return False
    return any(bad in name for bad in excluded)


# ── 去重 ─────────────────────────────────────────────
def is_duplicate(company: str, position: str, city: str = "") -> bool:
    """jobs_pool 中是否已存在 (公司, 岗位, 城市) 三元组。"""
    conn = sqlite3.connect(settings.db_full_path)
    try:
        row = conn.execute(
            '''SELECT id FROM jobs_pool
               WHERE "公司" = ? AND "岗位名称" = ? AND COALESCE("城市",'') = ?
               LIMIT 1''',
            (company, position, city or ""),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# ── 入库 ─────────────────────────────────────────────
def insert_job(
    company: str,
    position: str,
    city: str,
    url: str,
    match_score: float,
    priority: str = "P1",
    direction: str = "",
    source: str = "WebSearch",
    link_type: str = "🔶门户",
    notes: str = "",
) -> int:
    """插入一条新岗位，返回 lastrowid。"""
    conn = sqlite3.connect(settings.db_full_path)
    try:
        cur = conn.execute(
            '''INSERT INTO jobs_pool
               ("公司","岗位名称","城市","方向分类","等级","匹配分",
                "发布时间","时间等级","来源平台","链接","今日行动",
                status, link_type, credibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                company, position, city, direction, priority, round(match_score, 1),
                datetime.now().strftime("%Y-%m-%d"), "≤7天", source, url,
                notes or f"auto-crawl {datetime.now().strftime('%m-%d')}",
                "NEW", link_type, "🟡中",
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── 抓取 + 打分 ──────────────────────────────────────
def _score_lead(lead: JobLead, raw_text: str) -> float:
    """用现有 ai_engine.calculate_fit_score 打分。失败降级为 60。"""
    try:
        from services import ai_engine  # 延迟导入，避免 CLI 启动慢
        jd_parsed = {
            "title": lead.position,
            "company": lead.company,
            "location": lead.city,
            "raw_text": raw_text or f"{lead.position} @ {lead.company}",
        }
        score = ai_engine.calculate_fit_score(jd_parsed)
        return float(score) if score is not None else 60.0
    except Exception:
        return 60.0


def _scrape_lead(lead: JobLead) -> tuple[str, str]:
    """抓 JD 全文。返回 (raw_text, error_msg)。raw_text 为空时表示抓取失败。"""
    if not lead.url:
        return "", "no url"
    try:
        from services.jd_scraper import scrape_jd
        result = scrape_jd(lead.url, use_playwright=False, use_ai=False)
        if result.success and result.raw_text:
            return result.raw_text, ""
        return "", result.error or "scrape returned empty"
    except Exception as e:
        return "", f"scrape exception: {e}"


def crawl_one(lead: JobLead, excluded: set[str] | None = None) -> dict:
    """
    跑单条完整流程：过滤 → 去重 → 抓取 → 打分 → 入库。
    返回诊断 dict：{status: excluded|duplicated|scrape_failed|inserted, ...}
    """
    excluded = excluded if excluded is not None else load_excluded()

    if is_excluded(lead.company, excluded):
        return {"status": "excluded", "reason": f"{lead.company} 命中黑名单"}

    if is_duplicate(lead.company, lead.position, lead.city):
        return {"status": "duplicated", "reason": f"{lead.company}/{lead.position}/{lead.city} 已存在"}

    raw_text, scrape_err = _scrape_lead(lead)
    # 即使抓取失败也入库（但打降级分 + 标注）
    score = _score_lead(lead, raw_text)
    notes = "auto-crawl"
    if scrape_err:
        notes += f" [scrape_failed: {scrape_err[:40]}]"

    try:
        jid = insert_job(
            company=lead.company,
            position=lead.position,
            city=lead.city,
            url=lead.url,
            match_score=score,
            priority=lead.priority,
            direction=lead.direction,
            source=lead.source,
            notes=notes,
        )
        return {
            "status": "inserted",
            "id": jid,
            "score": score,
            "scrape_ok": not bool(scrape_err),
            "company": lead.company,
            "position": lead.position,
            "city": lead.city,
            "url": lead.url,
        }
    except Exception as e:
        return {"status": "error", "reason": f"DB insert failed: {e}"}


def bulk_crawl(leads: list[JobLead]) -> CrawlStats:
    """批量跑，返回统计。"""
    excluded = load_excluded()
    stats = CrawlStats(total=len(leads))
    inserted_rows: list[dict] = []

    for lead in leads:
        result = crawl_one(lead, excluded=excluded)
        status = result.get("status")
        if status == "excluded":
            stats.excluded += 1
            stats.excluded_reasons.append(result.get("reason", ""))
        elif status == "duplicated":
            stats.duplicated += 1
        elif status == "inserted":
            stats.inserted += 1
            if not result.get("scrape_ok"):
                stats.scrape_failed += 1
            inserted_rows.append(result)
        else:
            stats.errors.append(result.get("reason", "unknown"))

    # Top 3 by score
    stats.top_matches = sorted(
        inserted_rows, key=lambda r: r.get("score", 0), reverse=True
    )[:3]
    return stats


# ── 日志 ─────────────────────────────────────────────
def append_report(stats: CrawlStats, report_date: str | None = None) -> Path:
    """把扫描结果追加到 reports/daily_scan_YYYYMMDD.md。"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = report_date or datetime.now().strftime("%Y%m%d")
    path = REPORTS_DIR / f"daily_scan_{date_str}.md"

    ts = datetime.now().strftime("%H:%M:%S")
    lines = [
        f"\n## 扫描批次 {ts}",
        f"- 输入 {stats.total} 条 · 入库 **{stats.inserted}** · 去重 {stats.duplicated} · 排除 {stats.excluded} · 抓取失败 {stats.scrape_failed}",
    ]
    if stats.top_matches:
        lines.append("- **Top 3 匹配**：")
        for r in stats.top_matches:
            lines.append(
                f"  - [{r['score']:.0f}] {r['company']} / {r['position']} / {r.get('city', '')}  → {r.get('url', '')}"
            )
    if stats.excluded_reasons:
        lines.append(f"- 排除命中：{', '.join(stats.excluded_reasons[:10])}")
    if stats.errors:
        lines.append(f"- 错误：{stats.errors[:5]}")
    path.write_text(
        (path.read_text(encoding="utf-8") if path.exists() else f"# 每日岗位扫描 {date_str}\n")
        + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return path


# ── CLI ──────────────────────────────────────────────
def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="CareerOS 岗位批量爬取")
    ap.add_argument("--from-json", type=Path, help="输入 JSON 文件：[{company,position,city,url,priority},...]")
    ap.add_argument("--dry-run", action="store_true", help="只打印不入库")
    args = ap.parse_args()

    if not args.from_json:
        ap.error("需要 --from-json")
        return 2

    data = json.loads(args.from_json.read_text(encoding="utf-8"))
    leads = [JobLead(**d) for d in data]

    if args.dry_run:
        print(f"[dry-run] 将处理 {len(leads)} 条线索")
        ex = load_excluded()
        for lead in leads:
            tag = "🚫excluded" if is_excluded(lead.company, ex) else (
                "🔁dup" if is_duplicate(lead.company, lead.position, lead.city) else "✅new"
            )
            print(f"  {tag}  {lead.company} / {lead.position} / {lead.city}")
        return 0

    stats = bulk_crawl(leads)
    report_path = append_report(stats)
    print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))
    print(f"[report] {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
