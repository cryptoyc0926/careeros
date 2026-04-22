"""CareerOS Job Finder CLI（v0：只走 L1 ATS poller，L2 LLM 兜底在 D4 加）。

用法：
    python scripts/find_jobs.py --priority P0,P1 --city 杭州 --role 运营 --max 30
    python scripts/find_jobs.py --companies Zilliz,Dify --q 增长
    python scripts/find_jobs.py --dry-run              # 只列出命中公司，不抓不写库

退出码：
    0  成功
    2  参数错误
    3  无命中公司
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 让 web/services/* 可 import
_ROOT = Path(__file__).resolve().parents[1]
_WEB = _ROOT / "web"
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))

import yaml  # noqa: E402

from services.ats_pollers import get_poller, PollerError, NeedsBrowserError, SlugInvalid  # noqa: E402
from services.job_crawler import JobLead, bulk_crawl, append_report, load_targets, load_excluded  # noqa: E402
from services.job_search import search_and_extract, post_filter_direct_only  # noqa: E402


# ── 工具 ─────────────────────────────────────────────

def _iter_company_groups(targets: dict):
    """yield (group_name, company_dict)。跳过 excluded / search_terms / scoring 等非公司键。"""
    for key, val in (targets or {}).items():
        if not isinstance(val, list):
            continue
        if not key.startswith(("P0_", "P1_", "P2_")):
            continue
        for c in val:
            if isinstance(c, dict) and c.get("name"):
                yield key, c


def _match_city(company_city: str, wanted: str | None) -> bool:
    if not wanted:
        return True
    if not company_city:
        return False
    # yaml 里 city 可能是 "杭州" / "深圳/海外" / "苏州/远程"，用包含判定
    return wanted.strip() in company_city


def _select_companies(
    targets: dict,
    priorities: set[str] | None,
    city: str | None,
    whitelist: set[str] | None,
) -> list[dict]:
    """筛选符合条件的公司。whitelist 优先。"""
    selected: list[dict] = []
    for _group, c in _iter_company_groups(targets):
        name = c.get("name", "").strip()
        if whitelist:
            if name in whitelist:
                selected.append(c)
            continue
        if priorities and c.get("priority") not in priorities:
            continue
        if not _match_city(c.get("city", ""), city):
            continue
        selected.append(c)
    return selected


# ── L1：ATS poller ───────────────────────────────────

def _leads_from_ats(
    companies: list[dict],
    q: str | None,
    city: str | None,
    direction: str | None,
) -> tuple[list[JobLead], list[dict], list[dict], list[dict]]:
    """返回 (leads, covered, uncovered, manual_follow_up)。

    分流：
      - covered: poller 成功，有岗位入库（_count>=0 都算）
      - uncovered: 未配 ats 字段，可以交给 L2 LLM 兜底
      - manual_follow_up: 技术上抓不了，建议用户手动跟进
          * ats: marketing_only       官网纯营销页
          * NeedsBrowserError         SPA 需 Cookie/浏览器
          * SlugInvalid               ATS slug 失效
    """
    leads: list[JobLead] = []
    covered: list[dict] = []
    uncovered: list[dict] = []
    manual: list[dict] = []

    def _manual_add(c: dict, reason: str, hint: str = ""):
        manual.append({**c, "_reason": reason, "_manual_hint": hint or _infer_manual_hint(c)})

    for c in companies:
        ats = (c.get("ats") or "").strip().lower()

        # 架构显式标注：这家官网没结构化岗位
        if ats == "marketing_only":
            _manual_add(c, "官网纯营销页，无结构化岗位可抓")
            continue

        slug = (c.get("ats_slug") or "").strip()
        if not ats:
            uncovered.append(c)  # 未配 ats → 可能由 L2 补
            continue
        if not slug and ats not in ("static_html",):
            uncovered.append({**c, "_note": f"缺 ats_slug（ats={ats}）"})
            continue

        try:
            poller = get_poller(ats)
        except KeyError:
            uncovered.append({**c, "_note": f"unknown ats {ats!r}"})
            continue

        filters = {
            "slug": slug,
            "company": c["name"],
            "q": q,
            "city": city,
            "priority": c.get("priority", "P1"),
            "direction": direction or "",
        }
        if c.get("ats_token"):
            filters["token"] = c["ats_token"]

        try:
            batch = poller.list_jobs(filters)
            leads.extend(batch)
            covered.append({**c, "_count": len(batch)})
        except NeedsBrowserError:
            _manual_add(c, "招聘页是 SPA，脚本抓不到（飞书 SPA 反爬）")
        except SlugInvalid as e:
            _manual_add(c, f"ATS slug 失效：{e}")
        except PollerError as e:
            uncovered.append({**c, "_note": f"poller error: {e}"})
        except Exception as e:
            uncovered.append({**c, "_note": f"error: {type(e).__name__}: {e}"})
    return leads, covered, uncovered, manual


def _infer_manual_hint(c: dict) -> str:
    """基于 yaml signals 字段推断人工跟进建议。"""
    sig = (c.get("signals") or "")
    if "内推码" in sig:
        return f"✅ {sig.split('内推码')[-1].strip(' ；;：:')}（走内推优先）"
    if "邮箱" in sig or "@" in sig:
        return f"📧 {sig}"
    # 默认建议
    return "🔍 LinkedIn / 脉脉 搜公司名 + 岗位关键词；或公众号发消息问 HR"


# ── CLI ─────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find direct JD links via ATS pollers.")
    ap.add_argument("--priority", default="P0,P1", help="逗号分隔的优先级（默认 P0,P1）")
    ap.add_argument("--city", default="", help="城市关键词（包含匹配）")
    ap.add_argument("--role", default="", help="岗位关键词（如 运营 / 增长 / 产品）")
    ap.add_argument("--q", default="", help="岗位名搜索（等价于 --role，兼容）")
    ap.add_argument("--direction", default="", help="方向分类（写入 DB 方向分类 列）")
    ap.add_argument("--companies", default="", help="逗号分隔的公司白名单，会覆盖 priority/city")
    ap.add_argument("--max", type=int, default=50, help="最多入库条数（截断）")
    ap.add_argument("--dry-run", action="store_true", help="只列公司，不抓不写库")
    ap.add_argument("--l2", action="store_true", help="对 uncovered 公司走 LLM+web_search 兜底（消耗 token）")
    ap.add_argument("--l2-max", type=int, default=20, help="L2 单次返回岗位数上限")
    args = ap.parse_args(argv)

    priorities = {p.strip() for p in args.priority.split(",") if p.strip()}
    city = args.city or None
    q = args.role or args.q or None
    whitelist = {c.strip() for c in args.companies.split(",") if c.strip()} or None

    targets = load_targets()
    companies = _select_companies(targets, priorities, city, whitelist)
    if not companies:
        print("⚠️  无命中公司。检查 --priority / --city / --companies", file=sys.stderr)
        return 3

    print(f"🎯 命中 {len(companies)} 家公司，开始扫描…", file=sys.stderr)

    if args.dry_run:
        for c in companies:
            ats = c.get("ats", "—")
            slug = c.get("ats_slug", "—")
            print(f"  [{c.get('priority','?')}] {c['name']}  ats={ats}/{slug}  city={c.get('city','')}")
        return 0

    leads, covered, uncovered, manual = _leads_from_ats(companies, q, city, args.direction)

    # L2：对 uncovered 公司走 LLM + web_search 兜底（opt-in）
    l2_stats: dict | None = None
    if args.l2 and uncovered:
        print(f"🧠 L2 兜底：{len(uncovered)} 家未覆盖公司送 LLM+web_search…", file=sys.stderr)
        kw = [x for x in [q, city, args.direction] if x]
        try:
            raw = search_and_extract(
                keywords=kw or [(args.role or "运营")],
                target_roles=[args.role] if args.role else None,
                target_companies_p0=[c["name"] for c in uncovered],
                excluded_companies=list(load_excluded()),
                max_results=args.l2_max,
            )
            kept, l2_stats = post_filter_direct_only(raw)
            print(f"   L2 返回 {l2_stats['input']}，post_filter 保留 {l2_stats['kept']} 条（过滤率 {1-l2_stats['keep_ratio']:.0%}）", file=sys.stderr)
            for r in kept:
                leads.append(JobLead(
                    company=r.get("company", ""),
                    position=r.get("position", ""),
                    city=r.get("city", ""),
                    url=r.get("link", ""),
                    priority=r.get("priority", "P2"),
                    source=f"L2-{r.get('source', 'AI搜索')}",
                    direction=r.get("direction", args.direction or ""),
                    link_type=r.get("link_type", "✅直达"),
                ))
        except Exception as e:
            print(f"   ⚠️  L2 兜底失败: {type(e).__name__}: {e}", file=sys.stderr)

    # 截断
    if args.max and len(leads) > args.max:
        leads = leads[: args.max]

    # 统一打印"两清单" —— 即使 leads 为空也要给清单 B
    stats = None
    if leads:
        print(f"📥 产出 {len(leads)} 条 lead，走 bulk_crawl 入库…", file=sys.stderr)
        stats = bulk_crawl(leads)

    # ─────────────── 清单 A：已抓到入库 ───────────────
    print("\n" + "=" * 60)
    print("清单 A：已抓到并入库的岗位")
    print("=" * 60)
    if stats and stats.inserted:
        print(f"新入库 {stats.inserted} 条 · 重复 {stats.duplicated} · 黑名单 {stats.excluded} · 抓取失败 {stats.scrape_failed}")
        print(f"\nTop 匹配：")
        for m in stats.top_matches:
            print(f"  [{m.get('score', 0):.0f}分] {m.get('company')} / {m.get('position')} @ {m.get('city') or '—'}")
            print(f"         ✅ {m.get('url')}")
    else:
        print("（本轮无新岗位入库）")
        if covered:
            print(f"\n覆盖公司 {len(covered)} 家但全为重复或被过滤：")
            for c in covered[:5]:
                print(f"  · {c['name']}  抓到 {c.get('_count', 0)} 条")

    # ─────────────── 清单 B：建议手动跟进 ───────────────
    print("\n" + "=" * 60)
    print("清单 B：建议你手动跟进的公司")
    print("=" * 60)
    if manual:
        for c in manual:
            city = c.get("city", "")
            prio = c.get("priority", "P?")
            print(f"\n【{prio}】{c['name']}  ({city})")
            print(f"  原因：{c.get('_reason', '未知')}")
            print(f"  建议：{c.get('_manual_hint', '')}")
            if c.get("careers_url"):
                print(f"  官网招聘页：{c['careers_url']}")
            if c.get("signals"):
                print(f"  内推/线索：{c['signals']}")
    else:
        print("（无）")

    # ─────────────── 未覆盖（可交 L2 LLM 兜底）──────────
    if uncovered:
        print("\n" + "-" * 60)
        print(f"未覆盖 {len(uncovered)} 家公司（未配 ats，可加 --l2 走 LLM 兜底）：")
        for u in uncovered[:10]:
            print(f"  · {u['name']}  {u.get('_note', '未配 ats 字段')}")

    # ─────────────── 日志 ──────────────────────────────
    if stats:
        report = append_report(stats)
        print(f"\n📄 日报追加到 {report}", file=sys.stderr)

    if l2_stats:
        print(f"\n🧠 L2 统计: input={l2_stats['input']} kept={l2_stats['kept']} "
              f"dropped_portal={l2_stats['dropped_portal']} dropped_no_url={l2_stats['dropped_no_url']} "
              f"dropped_type={l2_stats['dropped_type']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
