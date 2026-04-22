"""通用静态 HTML careers page poller（配置驱动）。

不同公司的官网 careers 页 HTML 结构各异，不可能写统一 selector。
策略：按 slug 查内置 config（CSS class 前缀 + 标题正则），抽岗位 block。

新增一家公司 = 在 CONFIGS 里加一条 StaticConfig。
LiblibAI 作为首个落地（13 个岗位全量提取已验证）。

入库行为：
  - 每个岗位共用同一个 careers URL（因为自建页通常所有岗位在一页上）
  - link_type 标记为 "✅直达"（用户点开能直接看到岗位内容，即使不能精确定位到某一个）
  - notes 会附上 "static_html:{slug}" 便于后续追踪
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .base import Poller, SlugInvalid, instrument


@dataclass
class StaticConfig:
    """一家公司的静态 HTML parser 配置。"""
    slug: str
    careers_url: str
    # 岗位标题 div 的 class 前缀（Next.js / CSS modules 带 hash 后缀 → 用前缀匹配）
    title_class_prefix: str
    # 从标题纯文本里提取 name + city；name 是必须的，city 可选
    # 默认匹配 "N. {name} ｜ {city}" 或 "{name} ｜ {city}" 或 "{name}"
    title_regex: str = (
        r"^\s*(?:\d+[\.\)]\s*)?(?P<name>[^｜|]+?)"
        r"(?:\s*[｜|]\s*(?P<city>[^<>]+))?\s*$"
    )
    company_display: str = ""  # 写入 JobLead.company；留空则用 filters["company"]


# ── 已知公司配置 ───────────────────────────────────────
CONFIGS: dict[str, StaticConfig] = {
    "liblib": StaticConfig(
        slug="liblib",
        careers_url="https://www.liblib.art/us/joinus",
        title_class_prefix="joinus_jobItemTitle",
        company_display="LiblibAI",
    ),
}


# ── 简单 HTML 清洗（不引入 BeautifulSoup 以保持轻量）──────
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    """去标签 + 合并空白。"""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", s)).strip()


def _extract_titles(html: str, class_prefix: str) -> list[str]:
    """匹配所有 class 以 class_prefix 开头的 div 的内部 HTML 片段。"""
    pat = re.compile(
        rf'<div[^>]*class="[^"]*{re.escape(class_prefix)}[^"]*"[^>]*>(.*?)</div>',
        re.S,
    )
    return pat.findall(html)


class StaticHtmlPoller(Poller):
    name = "static_html"

    @instrument
    def list_jobs(self, filters: dict | None = None) -> list:
        # 延迟 import 避免循环
        from services.job_crawler import JobLead
        from services.jd_adapters.base import http_get

        filters = filters or {}
        slug = (filters.get("slug") or "").strip().lower()
        if not slug or slug not in CONFIGS:
            raise SlugInvalid(f"static_html: unknown slug {slug!r}")
        cfg = CONFIGS[slug]

        html = http_get(cfg.careers_url, timeout=20)

        raw_titles = _extract_titles(html, cfg.title_class_prefix)
        if not raw_titles:
            return []

        title_re = re.compile(cfg.title_regex, re.S)
        company = cfg.company_display or filters.get("company", slug.title())
        priority = filters.get("priority", "P1")
        direction = filters.get("direction", "")
        q = filters.get("q") or filters.get("role")
        city_want = filters.get("city")

        leads: list = []
        for raw in raw_titles:
            text = _strip_html(raw)
            if not text:
                continue
            m = title_re.match(text)
            if not m:
                # 兜底：直接把全文当岗位名（不抽 city）
                name, city = text, ""
            else:
                name = (m.group("name") or "").strip()
                try:
                    city = (m.group("city") or "").strip()
                except IndexError:
                    city = ""

            # 客户端筛选（关键词 + 城市）
            if not self._position_matches(name, q):
                continue
            if not self._city_matches(city, city_want):
                continue

            leads.append(JobLead(
                company=company,
                position=name,
                city=city,
                url=cfg.careers_url,  # 所有岗位共用招聘页 URL
                priority=priority,
                source="static_html",
                direction=direction,
                link_type="✅直达",
            ))
        return leads
