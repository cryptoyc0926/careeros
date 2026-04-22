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
# 国内域名：走直连不过 HTTPS_PROXY（本机代理对国内站 TLS 握手会被 reset）
_CN_DOMAINS = (
    ".cn", "ai-indeed.com", "liblib.art", "wujieai.com",
    "nowcoder.com", "shixiseng.com", "yingjiesheng.com",
    "liepin.com", "lagou.com", "51job.com",
    "metaso.cn", "moonshot.cn", "minimaxi.com",
    "stepfun.com", "deepseek.com", "kimi.com",
    "baichuan-ai.com", "lingyiwanwu.com", "sensetime.com",
    "zhipuai.cn", "bigmodel.cn", "infiniflow.org", "feishu.cn",
)


def _is_cn_domain(url: str) -> bool:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower()
    if not host:
        return False
    return any(host == d.lstrip(".") or host.endswith(d) for d in _CN_DOMAINS)


def http_get(
    url: str,
    *,
    timeout: int = 15,
    headers: dict[str, str] | None = None,
) -> str:
    """用 requests 做 GET。国内域名自动绕 HTTPS_PROXY。"""
    req_headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        req_headers.update(headers)

    # 国内站：显式 proxies=None 覆盖 session.trust_env
    is_cn = _is_cn_domain(url)
    session = requests.Session()
    session.trust_env = not is_cn
    proxies = {"http": None, "https": None} if is_cn else None

    try:
        resp = session.get(
            url,
            headers=req_headers,
            timeout=timeout,
            allow_redirects=True,
            proxies=proxies,
        )
        resp.raise_for_status()
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
