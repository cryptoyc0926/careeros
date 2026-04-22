"""
关键词全网搜索岗位 → 批量入库 jobs_pool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
用 Claude 的 web_search tool 做 SERP，然后把搜索结果转成结构化岗位 JSON，批量 insert 到 jobs_pool。

设计目标：
- 一次搜索至多 15-20 个岗位
- 不保证所有结果都是精确岗位链接（部分是公司页）→ 用 link_type 标注
- 已存在的 (公司, 岗位, 城市) 会被 UNIQUE 约束跳过
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


# ── link_type 规范化 ─────────────────────────────────
# DB 现存值：🔶门户(46) ✅直达(8) 📧邮件(4) ❌失效(1)
# 统一到这 4 值，UI 靠 emoji 前缀判定（web/pages/job_pool.py:211 依赖）
_LT_DIRECT = "✅直达"
_LT_PORTAL = "🔶门户"
_LT_EMAIL = "📧邮件"
_LT_DEAD = "❌失效"

_PORTAL_URL_RE = re.compile(
    r"(^https?://[^/]+/?$"           # 裸域名首页
    r"|/gongsi/"                      # zhipin.com/gongsi/xxx
    r"|/companies?/?(?:\?|$)"
    r"|/careers/?(?:\?|$)"
    r"|/jobs/?(?:\?|$))"              # 末尾是 /jobs 的门户入口
)

_EMAIL_RE = re.compile(r"^mailto:|@[\w.-]+\.[a-z]{2,}\s*$", re.I)


def _normalize_link_type(raw: str, url: str = "") -> str:
    """把 LLM/外部输入的 link_type 归一到 DB 存在的 4 值。"""
    s = (raw or "").strip()
    if not s and not url:
        return _LT_PORTAL
    # 已经是规范值
    for v in (_LT_DIRECT, _LT_PORTAL, _LT_EMAIL, _LT_DEAD):
        if v in s:
            return v
    # 关键词兜底
    if "直达" in s or "具体" in s or "详情" in s:
        return _LT_DIRECT
    if "邮件" in s or "mail" in s.lower() or _EMAIL_RE.search(url or ""):
        return _LT_EMAIL
    if "失效" in s or "404" in s:
        return _LT_DEAD
    return _LT_PORTAL


def post_filter_direct_only(results: list[dict]) -> tuple[list[dict], dict]:
    """丢弃非直达链接的 lead。返回 (kept, stats)。

    规则（OR 命中即丢）：
      - link_type 归一化后不等于 ✅直达
      - URL 匹配 _PORTAL_URL_RE（公司首页 / /gongsi/ / /careers/ / 末尾 /jobs）

    与 CLAUDE.md §四 红线对齐：禁止把 zhipin.com/gongsi/* 或 careers.xxx.com 标注为具体岗位。
    """
    kept: list[dict] = []
    dropped_portal = 0
    dropped_no_url = 0
    dropped_type = 0
    for it in results:
        url = str(it.get("link", "")).strip()
        lt_raw = str(it.get("link_type", "")).strip()
        lt = _normalize_link_type(lt_raw, url)
        if not url:
            dropped_no_url += 1
            continue
        if _PORTAL_URL_RE.search(url):
            dropped_portal += 1
            continue
        if lt != _LT_DIRECT:
            dropped_type += 1
            continue
        # 规范化写回
        new_it = dict(it)
        new_it["link_type"] = lt
        kept.append(new_it)
    stats = {
        "input": len(results),
        "kept": len(kept),
        "dropped_portal": dropped_portal,
        "dropped_no_url": dropped_no_url,
        "dropped_type": dropped_type,
        "keep_ratio": round(len(kept) / len(results), 2) if results else 0.0,
    }
    return kept, stats


SEARCH_SYSTEM = """你是一个求职岗位发现助手。用户会给你若干关键词和目标岗位方向，你要用 web_search 工具搜索近期公开的招聘岗位信息，然后输出结构化 JSON。

## 搜索策略
1. 至少做 2-4 次不同角度的 web_search 查询（例：关键词+"2026校招" / 关键词+"招聘" / 关键词+"jobs" / 公司名+岗位名）
2. 优先关注近 3 个月的招聘
3. 覆盖：招聘官网 / 招聘门户（BOSS/拉勾/猎聘/Moka/飞书招聘）/ 公司 X/LinkedIn 招聘贴

## 硬规则
1. 只输出一个合法 JSON 数组（外层 []），不要有前后文本
2. 每项至少包含 company / position；其他字段有多少填多少，没有留空字符串
3. 绝对不能编造公司名或岗位名 — 要能在搜索结果中找到证据
4. link_type 必须标注为下列 emoji 短值之一：`✅直达`（link 指向具体岗位详情页）/ `🔶门户`（公司/招聘门户首页、需二次点击）/ `📧邮件`（无 URL 只能邮件投递）
5. 单次至少返回 5 个，最多 20 个；按与关键词匹配度降序

## 输出 Schema（数组）
[
  {
    "company":     "公司名",
    "position":    "岗位名",
    "city":        "城市（例：北京 / 上海 / 杭州 / 远程）",
    "priority":    "P0" or "P1" or "P2",
    "link":        "具体 URL",
    "link_type":   "✅直达 | 🔶门户 | 📧邮件",
    "source":      "来源（例：Moka HR / 公司官网 / LinkedIn）",
    "notes":       "一句话核心匹配点或吸引人处（20 字以内）",
    "match_score": 50-95,
    "fit_rationale": "为什么这个岗位匹配用户关键词（30 字以内）"
  }
]

## 优先级打分
- P0：公司在用户 target_companies_p0 清单内；或关键词超高匹配
- P1：相邻赛道 / 关键词部分匹配
- P2：较远但值得扫一眼

开始搜索。"""


def search_and_extract(
    keywords: list[str],
    target_roles: list[str] | None = None,
    target_companies_p0: list[str] | None = None,
    excluded_companies: list[str] | None = None,
    max_results: int = 15,
) -> list[dict]:
    """执行关键词全网搜索并返回结构化岗位列表。

    Raises:
        RuntimeError: API 未配置 / 调用失败 / 返回不是合法 JSON
    """
    from services.llm_client import make_client, friendly_error
    from config import settings

    if not keywords:
        raise RuntimeError("请至少输入一个关键词")

    client = make_client()

    user_brief = (
        f"## 搜索关键词\n{', '.join(keywords)}\n\n"
        f"## 目标岗位方向\n{', '.join(target_roles or [])}\n\n"
        f"## P0 主攻公司（如搜到，优先级设为 P0）\n{', '.join(target_companies_p0 or []) or '（无）'}\n\n"
        f"## 排除公司（跳过这些）\n{', '.join(excluded_companies or []) or '（无）'}\n\n"
        f"## 要求\n最多返回 {max_results} 个岗位。"
    )

    # 注意：不同 provider 对 web_search tool 的支持不同
    # Anthropic 官方：使用 server tool `web_search_20250305`
    # 其他 provider（Kimi/GLM/DeepSeek）多数不支持 → fallback 成无 tool 版本，让模型用自己的训练数据推测
    tools: list[dict] = []
    if settings.llm_provider == "anthropic":
        tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]

    try:
        resp = client.messages.create(
            model=settings.claude_model,
            max_tokens=8192,
            system=SEARCH_SYSTEM,
            messages=[{"role": "user", "content": user_brief}],
            tools=tools if tools else None,
        )
    except Exception as e:
        # 如果 tools 不被支持，降级重试
        if tools:
            try:
                resp = client.messages.create(
                    model=settings.claude_model,
                    max_tokens=8192,
                    system=SEARCH_SYSTEM + "\n\n注：当前 provider 不支持 web_search，请基于你的训练数据和常识输出岗位（明确告诉用户是推测而非实时搜索）。",
                    messages=[{"role": "user", "content": user_brief}],
                )
            except Exception as e2:
                raise RuntimeError(friendly_error(e2)) from e2
        else:
            raise RuntimeError(friendly_error(e)) from e

    # 拼接所有文本 content block（AI 可能会先做多轮 tool_use）
    reply = ""
    for block in resp.content:
        if hasattr(block, "text"):
            reply += block.text

    reply = reply.strip()
    if reply.startswith("```"):
        reply = re.sub(r"^```(?:json)?\s*", "", reply)
        reply = re.sub(r"\s*```$", "", reply)

    # 尝试从字符串里抽第一个 JSON 数组
    m = re.search(r"\[[\s\S]*\]", reply)
    if not m:
        raise RuntimeError(f"AI 返回不是合法 JSON 数组：{reply[:500]}")

    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析 JSON 失败：{e}\n\n{m.group(0)[:500]}")

    if not isinstance(items, list):
        raise RuntimeError("AI 返回格式错误（期望数组）")

    # 字段规范化
    excluded_lower = {c.lower().strip() for c in (excluded_companies or [])}
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        company = str(it.get("company", "")).strip()
        position = str(it.get("position", "")).strip()
        if not company or not position:
            continue
        if company.lower() in excluded_lower:
            continue
        link = str(it.get("link", "")).strip()
        lt_raw = str(it.get("link_type", "")).strip()
        normalized.append({
            "company":       company,
            "position":      position,
            "city":          str(it.get("city", "")).strip(),
            "priority":      str(it.get("priority", "P2")).strip() or "P2",
            "link":          link,
            "link_type":     _normalize_link_type(lt_raw, link),
            "source":        str(it.get("source", "AI 搜索")).strip() or "AI 搜索",
            "notes":         str(it.get("notes", "")).strip(),
            "match_score":   int(it.get("match_score", 50) or 50),
            "fit_rationale": str(it.get("fit_rationale", "")).strip(),
            "direction":     str(it.get("direction", "")).strip(),
        })

    return normalized[:max_results]


def insert_jobs_to_pool(db_path: Path, jobs: list[dict]) -> dict:
    """批量插入到 jobs_pool 表（已存在的 (公司,岗位名称,城市) 跳过）。

    对齐 job_crawler.insert_job 的列集和 link_type emoji 规范。
    返回：{"inserted": N, "skipped": M, "errors": [...]}
    """
    if not db_path.exists():
        raise FileNotFoundError(str(db_path))

    from datetime import datetime  # 本地导入避免顶层循环

    conn = sqlite3.connect(db_path)
    inserted = 0
    skipped = 0
    errors: list[str] = []
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        for j in jobs:
            try:
                # 主键查重
                row = conn.execute(
                    'SELECT id FROM jobs_pool WHERE "公司"=? AND "岗位名称"=? AND COALESCE("城市",\'\')=?',
                    (j["company"], j["position"], j.get("city", "") or ""),
                ).fetchone()
                if row:
                    skipped += 1
                    continue

                link_type = _normalize_link_type(j.get("link_type", ""), j.get("link", ""))
                notes = j.get("notes") or j.get("fit_rationale") or f"auto-search {today}"
                conn.execute(
                    '''INSERT INTO jobs_pool
                       ("公司","岗位名称","城市","方向分类","等级","匹配分",
                        "发布时间","时间等级","来源平台","链接","今日行动",
                        status, link_type, credibility)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        j["company"], j["position"], j.get("city", ""),
                        j.get("direction", ""), j.get("priority", "P2"),
                        float(j.get("match_score", 50)),
                        today, "≤7天",
                        j.get("source", "AI 搜索"), j.get("link", ""),
                        notes,
                        "NEW", link_type, "🟡中",
                    ),
                )
                inserted += 1
            except sqlite3.Error as e:
                errors.append(f"{j.get('company', '?')}/{j.get('position', '?')}: {e}")
                continue
        conn.commit()
    finally:
        conn.close()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}
