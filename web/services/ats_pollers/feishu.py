"""飞书招聘 ({slug}.jobs.feishu.cn) poller — 两 tier。

Tier 1（本文件，纯 Python）：
  飞书招聘 list 页面几乎全是 SPA（经实测 moonshot / poizon / zhipu-ai 等租户
  根页面 HTML 均无 __NEXT_DATA__，也无稳定 /s/<id> anchor）。
  因此 tier 1 只验证 slug 存活 → 抛 NeedsBrowserError，让 skill 会话里的
  Chrome MCP tier 2 接管。

Tier 2（在 ~/.claude/skills/careeros-job-finder/SKILL.md 里实现）：
  - preview_start / mcp__Claude_in_Chrome__navigate 打开 list 页
  - preview_snapshot / get_page_text 等待 SPA 渲染
  - 抽所有 /s/<id> anchor + 岗位名/城市
  - 回灌到 DB
"""
from __future__ import annotations

from services.jd_adapters.base import http_get, FetchError
from .base import Poller, NeedsBrowserError, SlugInvalid, instrument, _get_job_lead_cls


class FeishuPoller(Poller):
    name = "feishu"

    @instrument
    def list_jobs(self, filters: dict | None = None) -> list:
        filters = filters or {}
        slug = (filters.get("slug") or "").strip()
        if not slug:
            raise ValueError("FeishuPoller requires filters['slug']")

        url = f"https://{slug}.jobs.feishu.cn"
        try:
            html = http_get(url, timeout=12)
        except FetchError as e:
            msg = str(e).lower()
            if "http 404" in msg or "ssl" in msg or "eof" in msg:
                raise SlugInvalid(slug) from e
            raise

        # 粗过滤：页面里没有招聘关键词 → 视为无效 slug
        if "招聘" not in html and "feishu" not in html.lower():
            raise SlugInvalid(f"{slug} page is not feishu recruit")

        # 所有 feishu list 页都 SPA 化，tier 1 无法提取直达链接
        raise NeedsBrowserError(
            f"{slug}.jobs.feishu.cn 是 SPA，需 Chrome MCP 在 skill 会话中渲染后抓取"
        )
