"""统一 HTTP 客户端：国内域名自动绕 HTTPS_PROXY。

背景：本机设了 HTTPS_PROXY=http://127.0.0.1:7897（clash/ss 等），
海外站走代理正常，但国内站点（.cn / ai-indeed.com / liblib.art 等）经代理转发时
TLS 握手会被 reset（SSL_ERROR_SYSCALL）。需要按域名分流：
  - 国内：proxies={'http':None,'https':None} 直连
  - 海外：默认走 env 代理

所有 adapter / poller / careers parser 统一用这里的 http_get，不要自己写 requests.get。
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# 国内域名（走直连，不过代理）
_CN_DOMAINS = (
    # 后缀类
    ".cn",
    # 招聘站
    "ai-indeed.com", "liblib.art", "wujieai.com",
    "nowcoder.com", "shixiseng.com", "yingjiesheng.com",
    "liepin.com", "lagou.com", "51job.com",
    # 国内 AI 公司官网
    "metaso.cn", "moonshot.cn", "minimaxi.com",
    "stepfun.com", "deepseek.com", "kimi.com",
    "baichuan-ai.com", "01.ai", "lingyiwanwu.com",
    "sensetime.com", "zhipuai.cn", "bigmodel.cn",
    "stepfun.com", "infiniflow.org", "zilliz.com.cn",
    # 海外但有国内优先走直连（大厂 CDN，代理反而更慢）
    "feishu.cn",
)


class HttpError(Exception):
    pass


def is_cn_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return False
    return any(host == d.lstrip(".") or host.endswith(d) for d in _CN_DOMAINS)


def http_get(
    url: str,
    *,
    timeout: int = 15,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> requests.Response:
    """GET，自动按域名决定是否绕代理。

    返回 Response 对象（而非 text），方便调用方读 status_code / headers / cookies。
    encoding 自动修复（apparent_encoding）。
    """
    req_headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        req_headers.update(headers)

    proxies = None
    if is_cn_domain(url):
        # requests 会读 env 里的 HTTPS_PROXY，传显式 None 覆盖
        proxies = {"http": None, "https": None}

    try:
        session = requests.Session()
        # 阻止 session 自己读 env proxy
        session.trust_env = not is_cn_domain(url)
        resp = session.get(
            url,
            headers=req_headers,
            cookies=cookies or None,
            timeout=timeout,
            allow_redirects=True,
            proxies=proxies,
        )
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp
    except requests.HTTPError as e:
        raise HttpError(f"HTTP {e.response.status_code} {url}")
    except requests.RequestException as e:
        raise HttpError(f"request failed ({type(e).__name__}): {e}")


def http_get_text(url: str, **kw) -> str:
    """便捷方法：只要 text。"""
    return http_get(url, **kw).text


# 向后兼容：原来 jd_adapters.base.http_get 返回 text，保留签名
def http_get_compat(url: str, *, timeout: int = 15, headers: dict | None = None) -> str:
    try:
        return http_get(url, timeout=timeout, headers=headers).text
    except HttpError as e:
        # 保留 FetchError 语义供旧代码捕获
        from services.jd_adapters.base import FetchError
        raise FetchError(str(e)) from e
