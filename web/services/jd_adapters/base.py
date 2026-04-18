"""Adapter 基类 + 数据结构 + HTTP 工具。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

import requests


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


@dataclass
class FetchResult:
    ok: bool
    raw_text: str = ""
    company: str = ""
    title: str = ""
    location: str = ""
    source_url: str = ""
    adapter_name: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class FetchError(Exception):
    pass


class Adapter:
    name: str = "base"
    priority: int = 0  # 数字大优先

    def match(self, url: str) -> bool:
        raise NotImplementedError

    def fetch(self, url: str) -> FetchResult:
        raise NotImplementedError


# ── HTTP helpers ────────────────────────────────────────
def http_get(
    url: str,
    *,
    timeout: int = 15,
    headers: dict[str, str] | None = None,
) -> str:
    """用 requests 做 GET。requests 自动处理 gzip/SSL/重定向，比 urllib 兼容中国站点。"""
    req_headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        req_headers.update(headers)

    try:
        resp = requests.get(
            url,
            headers=req_headers,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        # requests 自动解 gzip，encoding 推断有时错，强制按 apparent_encoding 解
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.HTTPError as e:
        raise FetchError(f"HTTP {e.response.status_code} {url}")
    except requests.RequestException as e:
        raise FetchError(f"request failed: {e}")
    except Exception as e:
        raise FetchError(f"fetch failed: {e}")


def strip_html(html: str) -> str:
    """粗暴剥 HTML 标签 + 压缩空白。"""
    txt = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
    txt = re.sub(r"</(p|div|li|h[1-6])>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&lt;", "<", txt)
    txt = re.sub(r"&gt;", ">", txt)
    txt = re.sub(r"&quot;", '"', txt)
    txt = re.sub(r"\n\s*\n", "\n\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt.strip()
