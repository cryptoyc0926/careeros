"""Lever (jobs.lever.co) adapter.

Lever 有公开 API：https://api.lever.co/v0/postings/{company}/{post_id}
从 URL 解析 company 和 post_id 即可拿结构化 JSON。
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from .base import Adapter, FetchResult, FetchError, http_get, strip_html


_LEVER_PATH = re.compile(r"^/([^/]+)/([0-9a-f-]{8,})/?$")


class LeverAdapter(Adapter):
    name = "lever"
    priority = 90

    def match(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == "jobs.lever.co"

    def fetch(self, url: str) -> FetchResult:
        parsed = urlparse(url)
        m = _LEVER_PATH.match(parsed.path)
        if not m:
            return FetchResult(ok=False, source_url=url, adapter_name=self.name, error="url path not lever format")

        company, post_id = m.group(1), m.group(2)
        api = f"https://api.lever.co/v0/postings/{company}/{post_id}"

        try:
            body = http_get(api, headers={"Accept": "application/json"})
            data = json.loads(body)
        except (FetchError, json.JSONDecodeError) as e:
            return FetchResult(ok=False, source_url=url, adapter_name=self.name, error=str(e))

        title = data.get("text") or ""
        desc_html = data.get("description") or ""
        lists = data.get("lists") or []  # [{text, content}]
        additional = data.get("additional") or ""
        categories = data.get("categories") or {}

        parts = [f"【岗位】{title}" if title else ""]
        if categories.get("location"):
            parts.append(f"【城市】{categories['location']}")
        if categories.get("team"):
            parts.append(f"【团队】{categories['team']}")
        if desc_html:
            parts.append(f"【职位描述】\n{strip_html(desc_html)}")
        for blk in lists:
            if isinstance(blk, dict):
                btitle = blk.get("text", "")
                bcontent = strip_html(blk.get("content", ""))
                if btitle or bcontent:
                    parts.append(f"【{btitle}】\n{bcontent}")
        if additional:
            parts.append(f"【其他】\n{strip_html(additional)}")

        raw_text = "\n\n".join(p for p in parts if p)
        if len(raw_text) < 100:
            return FetchResult(ok=False, source_url=url, adapter_name=self.name, error="empty jd")

        return FetchResult(
            ok=True,
            raw_text=raw_text,
            title=title,
            location=categories.get("location", ""),
            source_url=url,
            adapter_name=self.name,
            meta={"lever_id": post_id, "company_slug": company},
        )
