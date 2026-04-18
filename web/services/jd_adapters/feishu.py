"""飞书招聘 adapter (*.jobs.feishu.cn)。

覆盖：
- Kimi:  moonshot.jobs.feishu.cn/s/<id>
- 智谱:  zhipu-ai.jobs.feishu.cn/s/<id>
- 得物:  poizon.jobs.feishu.cn/s/<id>
- 以及飞书招聘分配的 hash 子域（vrfi1sk8a0.jobs.feishu.cn 这种）

策略：
1. 短链 /s/<id> 页面 HTML 里有 __NEXT_DATA__ 嵌入的 JSON，含完整 JD
2. 若解析失败，剥 HTML 后走 generic LLM fallback
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from .base import Adapter, FetchResult, FetchError, http_get, strip_html


_NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.S,
)


class FeishuAdapter(Adapter):
    name = "feishu_jobs"
    priority = 100

    def match(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host.endswith(".jobs.feishu.cn") or host == "jobs.feishu.cn"

    def fetch(self, url: str) -> FetchResult:
        """飞书招聘是 SPA，JD 数据通过 XHR 异步加载，纯 HTTP 抓不到正文。

        策略：
        1. 试 __NEXT_DATA__（部分 tenant 开启 SSR）—— 成功即返回
        2. 否则标记 needs_chrome，由 browser worker 接管
        """
        try:
            html = http_get(url)
            payload = self._extract_next_data(html)
            if payload:
                jd = self._parse_next_data(payload)
                if jd:
                    return FetchResult(
                        ok=True,
                        raw_text=jd["raw_text"],
                        company=jd.get("company", ""),
                        title=jd.get("title", ""),
                        location=jd.get("location", ""),
                        source_url=url,
                        adapter_name=self.name,
                        meta={"via": "next_data"},
                    )
        except FetchError:
            pass

        return FetchResult(
            ok=False,
            source_url=url,
            adapter_name=self.name,
            error="NEEDS_CHROME: 飞书招聘 SPA，需 Chrome MCP 渲染后抓取",
            meta={"needs_chrome": True},
        )

    # ── 私有 ─────────────────────────────────
    def _extract_next_data(self, html: str) -> dict | None:
        m = _NEXT_DATA_RE.search(html)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    def _parse_next_data(self, data: dict) -> dict | None:
        """飞书招聘 __NEXT_DATA__ 结构：props.pageProps.jobPost 或 props.pageProps.post"""
        try:
            props = data.get("props", {}).get("pageProps", {})
            post = (
                props.get("jobPost")
                or props.get("post")
                or props.get("data", {}).get("post")
                or props.get("job")
            )
            if not post or not isinstance(post, dict):
                return None

            title = post.get("title") or post.get("name") or ""
            desc = post.get("description") or post.get("content") or ""
            req = post.get("requirement") or post.get("requirements") or ""
            company = (
                post.get("company_name")
                or post.get("companyName")
                or props.get("tenant", {}).get("name", "")
                or ""
            )
            city_list = post.get("city_list") or post.get("cityList") or []
            if isinstance(city_list, list):
                location = ", ".join(
                    c.get("name", "") if isinstance(c, dict) else str(c)
                    for c in city_list
                )
            else:
                location = str(city_list)

            # 描述字段本身是 HTML，要再剥一次
            desc_text = strip_html(desc) if desc else ""
            req_text = strip_html(req) if req else ""

            raw_text = "\n\n".join(
                seg for seg in [
                    f"【岗位】{title}" if title else "",
                    f"【公司】{company}" if company else "",
                    f"【城市】{location}" if location else "",
                    f"【职位描述】\n{desc_text}" if desc_text else "",
                    f"【任职要求】\n{req_text}" if req_text else "",
                ] if seg
            )

            if len(raw_text) < 100:
                return None

            return {
                "raw_text": raw_text,
                "title": title,
                "company": company,
                "location": location,
            }
        except Exception:
            return None
