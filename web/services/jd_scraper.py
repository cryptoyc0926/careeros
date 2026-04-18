"""
JD 爬虫服务 — 从招聘链接自动抓取职位描述
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
第一性原理：数据在服务器上，我们只需要找到正确的方式拿到它。

抓取优先级（每一层失败后自动降级到下一层）：
  1. API 直取 — 已知平台（Moka / 飞书）直接调用其内部 API，零依赖最快
  2. requests + HTML — 传统 SSR 站点，轻量可靠
  3. Playwright 渲染 — SPA 站点需要 JS 执行，带反检测
  4. AI 兜底 — 从已获取的部分文本中智能提取结构化信息

支持渠道:
  Moka HR · 飞书招聘 · Boss 直聘 · 拉勾 · 智联 · 猎聘 · 牛客 · 通用
"""

import re
import json
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ScrapedJD:
    """爬取结果。"""
    title: str = ""
    company: str = ""
    location: str = ""
    job_type: str = ""
    raw_text: str = ""
    source_url: str = ""
    salary: str = ""
    experience: str = ""
    education: str = ""
    success: bool = False
    error: str = ""


# ═══════════════════════════════════════════════════════════════
# 渠道识别
# ═══════════════════════════════════════════════════════════════

SPA_DOMAINS = {"mokahr.com", "feishu.cn", "zhipin.com", "liepin.com", "nowcoder.com"}

CHANNEL_MAP = {
    "mokahr.com": "官网招聘(Moka)",
    "feishu.cn": "飞书招聘",
    "zhipin.com": "Boss直聘",
    "lagou.com": "拉勾网",
    "zhaopin.com": "智联招聘",
    "liepin.com": "猎聘",
    "nowcoder.com": "牛客",
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
    "51job.com": "前程无忧",
}


def _detect_channel(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for domain, channel in CHANNEL_MAP.items():
        if domain in host:
            return channel
    return "其他"


def _is_spa(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(d in host for d in SPA_DOMAINS)


# ═══════════════════════════════════════════════════════════════
# 第 1 层：API 直取（已知平台，零依赖最快）
# ═══════════════════════════════════════════════════════════════

_COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _try_api_direct(url: str) -> ScrapedJD | None:
    """
    尝试直接调用已知平台的内部 API，跳过浏览器渲染。
    成功返回 ScrapedJD，不适用或失败返回 None。
    """
    host = (urlparse(url).hostname or "").lower()

    if "mokahr.com" in host:
        return _api_moka(url)
    elif "feishu.cn" in host or "feishu.com" in host:
        return _api_feishu(url)

    return None


def _api_moka(url: str) -> ScrapedJD | None:
    """
    Moka HR API 直取。
    URL 格式: https://app.mokahr.com/campus_apply/{org}/{id}#/job/{job_uuid}
    API:      https://app.mokahr.com/api/campus-recruit/{org}/{id}/job/{job_uuid}
              或 https://gateway.mokahr.com/api/campus-recruit/...
    """
    import requests as req_lib

    channel = "官网招聘(Moka)"
    parsed = urlparse(url)

    # 从 URL 中提取 org / recruitment_id / job_id
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    fragment = parsed.fragment or ""

    # 提取 job_id (在 hash fragment 中: #/job/{uuid})
    job_id = ""
    frag_match = re.search(r'/job/([a-f0-9-]+)', fragment)
    if frag_match:
        job_id = frag_match.group(1)

    # 提取 org_name 和 recruitment_id
    # path 通常是 /campus_apply/{org}/{id} 或 /apply/{org}/{id}
    org_name = ""
    recruit_id = ""
    for i, part in enumerate(path_parts):
        if part in ("campus_apply", "apply", "social-recruitment", "campus-recruitment"):
            if i + 1 < len(path_parts):
                org_name = path_parts[i + 1]
            if i + 2 < len(path_parts):
                recruit_id = path_parts[i + 2]
            break

    if not (org_name and job_id):
        return None

    # 尝试多种 API 路径
    api_patterns = []
    if recruit_id:
        api_patterns.append(f"https://app.mokahr.com/api/campus-recruit/{org_name}/{recruit_id}/job/{job_id}")
        api_patterns.append(f"https://gateway.mokahr.com/api/campus-recruit/{org_name}/{recruit_id}/job/{job_id}")
        api_patterns.append(f"https://app.mokahr.com/api/recruitment/{org_name}/{recruit_id}/job/{job_id}")
    api_patterns.append(f"https://app.mokahr.com/api/job/{job_id}")

    session = req_lib.Session()
    session.headers.update(_COMMON_HEADERS)
    session.headers["Referer"] = url
    session.headers["Origin"] = f"https://{parsed.hostname}"

    for api_url in api_patterns:
        try:
            resp = session.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                # Moka API 返回格式可能是 {data: {...}} 或直接 {...}
                job_data = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(job_data, dict):
                    result = ScrapedJD(source_url=url, job_type=channel)
                    result = _parse_json_job_data(job_data, result)
                    if result.success:
                        logger.info(f"Moka API 直取成功: {api_url}")
                        return result
        except Exception as e:
            logger.debug(f"Moka API 尝试失败 {api_url}: {e}")
            continue

    return None


def _api_feishu(url: str) -> ScrapedJD | None:
    """
    飞书招聘 API 直取。
    URL 格式: https://{tenant}.jobs.feishu.cn/{id}/m/position/{position_id}/detail
    API:      https://{tenant}.jobs.feishu.cn/api/v1/position/{position_id}
              或 /api/v2/position/{position_id}
    """
    import requests as req_lib

    channel = "飞书招聘"
    parsed = urlparse(url)
    host = parsed.hostname or ""

    # 提取 position_id
    pos_match = re.search(r'/position/(\d+)', parsed.path)
    if not pos_match:
        return None
    position_id = pos_match.group(1)

    # 提取 tenant portal id (路径中的第一段数字)
    portal_match = re.search(r'/(\d+)/', parsed.path)
    portal_id = portal_match.group(1) if portal_match else ""

    # 尝试多种 API 路径
    base = f"https://{host}"
    api_patterns = [
        f"{base}/api/v1/position/{position_id}",
        f"{base}/api/v2/position/{position_id}",
        f"{base}/api/v1/portal/{portal_id}/position/{position_id}" if portal_id else None,
        f"{base}/api/v2/portal/{portal_id}/position/{position_id}" if portal_id else None,
        # 飞书招聘的另一种 API 格式
        f"{base}/career/openapi/v1/position/detail?position_id={position_id}",
    ]
    api_patterns = [p for p in api_patterns if p]

    session = req_lib.Session()
    session.headers.update(_COMMON_HEADERS)
    session.headers["Referer"] = url
    session.headers["Origin"] = base

    for api_url in api_patterns:
        try:
            resp = session.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                job_data = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(job_data, dict) and job_data:
                    result = ScrapedJD(source_url=url, job_type=channel)
                    result = _parse_json_job_data(job_data, result)
                    if result.success:
                        logger.info(f"飞书 API 直取成功: {api_url}")
                        return result
        except Exception as e:
            logger.debug(f"飞书 API 尝试失败 {api_url}: {e}")
            continue

    # 飞书备用：直接 requests 获取页面 HTML（有时 SSR 会包含数据）
    try:
        session.headers["Accept"] = "text/html,application/xhtml+xml"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            # 查找内嵌的 JSON 数据
            for pattern in [
                r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*</script>',
                r'window\.__NEXT_DATA__\s*=\s*(\{.+?\});?\s*</script>',
                r'<script\s+id="__NEXT_DATA__"[^>]*>\s*(\{.+?\})\s*</script>',
            ]:
                m = re.search(pattern, html, re.DOTALL)
                if m:
                    try:
                        embedded = json.loads(m.group(1))
                        result = ScrapedJD(source_url=url, job_type=channel)
                        result = _parse_json_job_data(embedded, result)
                        if result.success:
                            return result
                    except json.JSONDecodeError:
                        continue

            # 兜底：从 HTML 中提取
            result = ScrapedJD(source_url=url, job_type=channel)
            result = _fallback_html_parse(html, result)
            if result.success:
                return result
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════
# 第 2 层：Playwright 抓取（SPA 站点，带反检测）
# ═══════════════════════════════════════════════════════════════

def _check_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def _apply_stealth(page):
    """注入反检测 JS，让 headless Chrome 更难被识别。"""
    stealth_js = """
    // 覆盖 webdriver 属性
    Object.defineProperty(navigator, 'webdriver', { get: () => false });

    // 覆盖 chrome 对象
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };

    // 覆盖 permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);

    // 覆盖 plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // 覆盖 languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en'],
    });
    """
    try:
        page.add_init_script(stealth_js)
    except Exception:
        pass


def _scrape_with_playwright(url: str) -> ScrapedJD:
    """用 Playwright 打开页面，等 JS 渲染完后提取文本（带反检测）。"""
    channel = _detect_channel(url)
    result = ScrapedJD(source_url=url, job_type=channel)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.error = (
            "此链接来自 SPA 站点，需要浏览器渲染。\n\n"
            "请安装 Playwright：\n"
            "```\npip install playwright\nplaywright install chromium\n```\n\n"
            "或使用「智能粘贴」功能。"
        )
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                ],
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"macOS"',
                },
            )
            page = ctx.new_page()

            # 注入反检测脚本
            _apply_stealth(page)

            host = (urlparse(url).hostname or "").lower()

            # ── 拦截 API 响应（在导航之前设置）──
            api_responses = []

            def _capture_response(response):
                """捕获页面发出的 API 请求的响应。"""
                try:
                    resp_url = response.url.lower()
                    ct = response.headers.get("content-type", "")
                    if "json" in ct and response.status == 200:
                        # 只捕获可能包含职位数据的 API
                        job_keywords = ["job", "position", "recruit", "detail", "vacancy"]
                        if any(kw in resp_url for kw in job_keywords):
                            body = response.json()
                            if isinstance(body, dict):
                                api_responses.append(body)
                except Exception:
                    pass

            page.on("response", _capture_response)

            # ── 导航 ──
            try:
                page.goto(url, wait_until="commit", timeout=30000)
            except Exception:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                except Exception as nav_err:
                    result.error = f"页面加载超时: {nav_err}"
                    browser.close()
                    return result

            # ── 等待 SPA 渲染 ──
            if "mokahr.com" in host:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                try:
                    page.wait_for_selector(
                        ".job-detail, .job-content, .job-detail-card, "
                        "[class*='detail'], [class*='position'], [class*='job-info'], "
                        "[class*='JobDetail'], [class*='recruitment']",
                        timeout=15000,
                    )
                except Exception:
                    page.wait_for_timeout(6000)

            elif "feishu.cn" in host:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                try:
                    page.wait_for_selector(
                        "[class*='detail'], [class*='position'], [class*='content'], "
                        "[class*='job'], .job-detail",
                        timeout=15000,
                    )
                except Exception:
                    page.wait_for_timeout(6000)

            elif "zhipin.com" in host:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                try:
                    page.wait_for_selector(
                        ".job-detail, .job-sec, [class*='job-detail'], .job-banner",
                        timeout=15000,
                    )
                except Exception:
                    page.wait_for_timeout(6000)
            else:
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    page.wait_for_timeout(5000)

            page.wait_for_timeout(2000)

            # ── 优先从拦截到的 API 响应中提取 ──
            for api_data in api_responses:
                data = api_data.get("data", api_data)
                if isinstance(data, dict):
                    test = ScrapedJD(source_url=url, job_type=channel)
                    test = _parse_json_job_data(data, test)
                    if test.success:
                        logger.info("从拦截的 API 响应中提取到职位数据")
                        browser.close()
                        return test

            # ── 提取页面标题 ──
            page_title = page.title() or ""

            # ── 提取 meta（用 evaluate 避免超时）──
            og_title = ""
            og_desc = ""
            try:
                og_title = page.evaluate(
                    '() => document.querySelector(\'meta[property="og:title"]\')?.content || ""'
                ) or ""
            except Exception:
                pass
            try:
                og_desc = page.evaluate(
                    '() => document.querySelector(\'meta[property="og:description"]\')?.content || ""'
                ) or ""
            except Exception:
                pass

            # ── 提取页面可见文本 ──
            try:
                body_text = page.inner_text("body", timeout=10000)
            except Exception:
                body_text = ""
                try:
                    body_text = page.evaluate('() => document.body?.innerText || ""') or ""
                except Exception:
                    pass

            # ── 尝试从页面 JS 上下文提取 JSON ──
            json_data = _extract_json_from_page(page)

            browser.close()

        # ── 从 JSON 数据中提取 ──
        if json_data:
            result = _parse_json_job_data(json_data, result)
            if result.success:
                return result

        # ── 从页面文本提取 ──
        if body_text and len(body_text.strip()) > 50:
            result.raw_text = body_text.strip()
            if not result.title:
                if og_title:
                    result.title = og_title
                elif page_title:
                    parts = re.split(r'\s*[-|–—_]\s*', page_title)
                    result.title = parts[0].strip() if parts else ""
                    if len(parts) > 1:
                        result.company = result.company or parts[1].strip()
            result.success = True
        else:
            result.error = "页面渲染后未提取到有效内容"

    except Exception as e:
        err_str = str(e)
        if "ERR_CONNECTION_CLOSED" in err_str or "ERR_CONNECTION_REFUSED" in err_str:
            result.error = (
                f"目标网站拒绝了浏览器连接（反爬检测）。\n\n"
                f"请使用「🧠 智能粘贴」功能：\n"
                f"1. 在浏览器中打开此链接\n"
                f"2. 按 Cmd+A 全选页面内容\n"
                f"3. 按 Cmd+C 复制\n"
                f"4. 切换到「智能粘贴」标签粘贴"
            )
        else:
            result.error = f"Playwright 抓取失败: {e}"

    return result


def _extract_json_from_page(page) -> dict:
    """尝试从页面 JS 上下文中提取职位 JSON 数据。"""
    scripts = [
        "window.__INITIAL_STATE__",
        "window.__NUXT__",
        "JSON.parse(document.getElementById('__NEXT_DATA__')?.textContent || '{}')",
        "window.__APP_DATA__",
        "window.__PRELOADED_STATE__",
    ]

    for script in scripts:
        try:
            data = page.evaluate(f"() => {{ try {{ return {script} }} catch(e) {{ return null }} }}")
            if data and isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _parse_json_job_data(data: dict, result: ScrapedJD) -> ScrapedJD:
    """从嵌入页面的 JSON 数据中递归查找职位信息。"""

    def _find(d, keys, max_depth=8):
        """在嵌套 dict 中查找第一个匹配的 key。"""
        if max_depth <= 0 or not isinstance(d, dict):
            return None
        for k in keys:
            if k in d and d[k]:
                return d[k]
        for v in d.values():
            if isinstance(v, dict):
                r = _find(v, keys, max_depth - 1)
                if r:
                    return r
            elif isinstance(v, list):
                for item in v[:20]:  # 限制遍历数量
                    if isinstance(item, dict):
                        r = _find(item, keys, max_depth - 1)
                        if r:
                            return r
        return None

    result.title = _find(data, ["jobName", "name", "title", "positionName", "job_name", "position_name"]) or ""
    result.company = _find(data, ["orgName", "brandName", "companyName", "organizationName", "org_name", "company_name"]) or ""
    result.location = _find(data, ["city", "cityName", "location", "workCity", "city_name", "work_city"]) or ""
    result.salary = _find(data, ["salaryDesc", "salary", "salaryRange", "salary_desc"]) or ""

    desc = _find(data, ["description", "postDescription", "content", "jobDescription", "detail",
                         "job_description", "post_description", "responsibility"]) or ""
    req = _find(data, ["requirement", "qualifications", "jobRequirement", "job_requirement"]) or ""

    if desc:
        combined = f"{desc}\n\n{req}".strip() if req else str(desc)
        result.raw_text = _clean_html(combined)
        if result.raw_text:
            result.success = True

    return result


# ═══════════════════════════════════════════════════════════════
# 第 2 层备选：requests 抓取（传统 SSR 站点）
# ═══════════════════════════════════════════════════════════════

def _scrape_with_requests(url: str) -> ScrapedJD:
    """对传统服务端渲染的页面，用 requests 抓取。"""
    import requests as req_lib

    channel = _detect_channel(url)
    result = ScrapedJD(source_url=url, job_type=channel)

    try:
        session = req_lib.Session()
        session.headers.update({
            "User-Agent": _COMMON_HEADERS["User-Agent"],
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # JSON-LD
        jld = re.search(r'<script\s+type="application/ld\+json">\s*(\{.+?\})\s*</script>', html, re.DOTALL)
        if jld:
            try:
                ld = json.loads(jld.group(1))
                if ld.get("@type") in ("JobPosting", "jobPosting"):
                    result.title = ld.get("title", "")
                    org = ld.get("hiringOrganization", {})
                    result.company = org.get("name", "") if isinstance(org, dict) else ""
                    result.raw_text = _clean_html(ld.get("description", ""))
                    if result.raw_text:
                        result.success = True
                        return result
            except json.JSONDecodeError:
                pass

        # __NEXT_DATA__
        nd = re.search(r'id="__NEXT_DATA__"[^>]*>\s*(\{.+?\})\s*</script>', html, re.DOTALL)
        if nd:
            try:
                ndata = json.loads(nd.group(1))
                result = _parse_json_job_data(ndata, result)
                if result.success:
                    return result
            except json.JSONDecodeError:
                pass

        # 通用 HTML
        result = _fallback_html_parse(html, result)
        return result

    except Exception as e:
        result.error = f"请求失败: {e}"
        return result


def _fallback_html_parse(html: str, result: ScrapedJD) -> ScrapedJD:
    """通用 HTML 兜底解析。"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        if not result.title and soup.title:
            parts = re.split(r'\s*[-|–—]\s*', soup.title.string or "")
            if parts:
                result.title = parts[0].strip()
            if len(parts) > 1:
                result.company = result.company or parts[1].strip()

        for meta in soup.find_all("meta"):
            prop = meta.get("property", "") or meta.get("name", "")
            content = meta.get("content", "")
            if prop in ("og:title", "twitter:title") and not result.title:
                result.title = content
            elif prop in ("og:description", "description") and content and len(content) > 50:
                result.raw_text = result.raw_text or content

        for sel in [".job-detail", ".job-description", ".job-content",
                    ".position-detail", ".job-desc", "#job_detail",
                    "[class*='job-desc']", "[class*='detail-body']"]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 50:
                result.raw_text = _clean_html(str(el))
                break

        if not result.raw_text:
            for tag in soup.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
                tag.decompose()
            body = soup.get_text(separator="\n", strip=True)
            if len(body) > 100:
                result.raw_text = body[:5000]

        if result.raw_text:
            result.success = True

    except ImportError:
        title_m = re.search(r'<title>(.+?)</title>', html)
        if title_m:
            result.title = title_m.group(1).split("-")[0].strip()
        body = re.sub(r'<script[\s\S]*?</script>', '', html)
        body = re.sub(r'<style[\s\S]*?</style>', '', body)
        body = _clean_html(body)
        if body:
            result.raw_text = body[:5000]
            result.success = True

    return result


# ═══════════════════════════════════════════════════════════════
# AI 智能解析（从用户粘贴的文本中提取结构化信息）
# ═══════════════════════════════════════════════════════════════

def parse_pasted_jd(text: str, url: str = "") -> ScrapedJD:
    """用 Claude AI 从用户粘贴的页面文本中智能提取 JD 信息。"""
    channel = _detect_channel(url) if url else "手动粘贴"
    result = ScrapedJD(source_url=url, job_type=channel)

    try:
        from services.ai_engine import _call_claude

        truncated = text[:10000]

        prompt = f"""以下是用户从招聘网站复制粘贴的页面文本。请从中提取职位信息。

请严格按照以下 JSON 格式输出（不要输出其他内容）：
{{
  "title": "职位名称",
  "company": "公司名称",
  "location": "工作地点",
  "raw_text": "完整的职位描述正文（包括岗位职责和任职要求，不含公司介绍和页面导航文字）",
  "salary": "薪资范围（如有）",
  "experience": "经验要求（如有）",
  "education": "学历要求（如有）"
}}

规则：
- raw_text 应该是干净的纯文本，保留原始换行
- 去掉页面导航、面包屑、页脚、"立即申请"按钮等无关文字
- 如果识别不出某个字段，用空字符串

页面文本：
{truncated}"""

        ai_result = _call_claude(
            system_prompt="你是一个精确的信息提取器。只输出合法 JSON，不要有其他文字。",
            user_prompt=prompt,
            max_tokens=3000,
            temperature=0.1,
        )

        text_out = ai_result.strip()
        if text_out.startswith("```"):
            lines = text_out.split("\n")
            text_out = "\n".join(lines[1:-1])
        start = text_out.find("{")
        end = text_out.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text_out[start:end])
            result.title = data.get("title", "")
            result.company = data.get("company", "")
            result.location = data.get("location", "")
            result.raw_text = data.get("raw_text", "")
            result.salary = data.get("salary", "")
            result.experience = data.get("experience", "")
            result.education = data.get("education", "")
            if result.raw_text:
                result.success = True

    except Exception as e:
        result.error = f"AI 解析失败: {e}"

    return result


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _clean_html(text: str) -> str:
    if not text:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all(["br", "p", "div", "li", "h1", "h2", "h3", "h4"]):
            tag.insert_before("\n")
        clean = soup.get_text()
    except ImportError:
        clean = re.sub(r'<br\s*/?>', '\n', text)
        clean = re.sub(r'</?(p|div|li|h[1-4])[^>]*>', '\n', clean)
        clean = re.sub(r'<[^>]+>', '', clean)

    lines = [line.strip() for line in clean.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def calculate_quick_fit(jd_text: str) -> float:
    """快速计算简历匹配度（基于关键词，不调用 AI）。"""
    try:
        import yaml
        from config import settings

        resume_path = settings.master_resume_full_path
        if not resume_path.exists():
            return 0.0

        resume_data = yaml.safe_load(resume_path.read_text(encoding="utf-8"))

        all_skills = set()
        for cat, items in resume_data.get("skills", {}).items():
            if isinstance(items, list):
                all_skills.update(s.lower() for s in items)

        for exp in resume_data.get("experience", []):
            for ach in exp.get("achievements", []):
                for tag in ach.get("tags", []):
                    all_skills.add(tag.lower())

        if not all_skills:
            return 0.0

        jd_lower = jd_text.lower()
        hits = sum(1 for skill in all_skills if skill in jd_lower)
        score = min(100.0, (hits / max(len(all_skills), 1)) * 200)
        return round(score, 1)

    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def scrape_jd(url: str, use_playwright: bool = True, use_ai: bool = True) -> ScrapedJD:
    """
    从 URL 抓取 JD 内容。

    四层抓取策略（自动降级）：
      1. API 直取（Moka / 飞书已知 API）
      2. SPA → Playwright 渲染 / 传统 → requests
      3. AI 从部分文本中提取结构
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    channel = _detect_channel(url)
    is_spa = _is_spa(url)

    # ══ 第 1 层：API 直取（最快，无依赖）══
    try:
        api_result = _try_api_direct(url)
        if api_result and api_result.success:
            api_result.job_type = channel
            return api_result
    except Exception as e:
        logger.debug(f"API 直取异常: {e}")

    # ══ 第 2 层：SPA → Playwright / 传统 → requests ══
    if is_spa:
        if use_playwright and _check_playwright():
            result = _scrape_with_playwright(url)
            if result.success:
                if result.raw_text and (not result.title or not result.company) and use_ai:
                    ai_result = parse_pasted_jd(result.raw_text, url)
                    if ai_result.success:
                        ai_result.job_type = channel
                        return ai_result
                return result
            # Playwright 失败但有部分文本
            if not result.success and use_ai and result.raw_text:
                ai_result = parse_pasted_jd(result.raw_text, url)
                if ai_result.success:
                    ai_result.job_type = channel
                    return ai_result
            return result
        else:
            return ScrapedJD(
                source_url=url,
                job_type=channel,
                error=(
                    f"此链接来自 **{channel}**（SPA 站点），API 直取未命中。\n\n"
                    "**方案 A：安装 Playwright（推荐）**\n"
                    "```\npip install playwright\nplaywright install chromium\n```\n\n"
                    "**方案 B：智能粘贴（零安装）**\n"
                    "打开链接 → Cmd+A 全选 → Cmd+C 复制 → 「智能粘贴」标签粘贴"
                ),
            )

    # ── 传统站点：requests ──
    result = _scrape_with_requests(url)

    if not result.success and use_playwright and _check_playwright():
        pw_result = _scrape_with_playwright(url)
        if pw_result.success:
            pw_result.job_type = channel
            return pw_result

    # ══ 第 3 层：AI 兜底 ══
    if result.raw_text and (not result.title or not result.company) and use_ai:
        ai_result = parse_pasted_jd(result.raw_text, url)
        if ai_result.success:
            ai_result.job_type = channel
            return ai_result

    result.job_type = result.job_type or channel
    return result
