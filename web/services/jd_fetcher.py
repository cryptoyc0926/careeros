"""JD 抓取主路由。

单入口 `fetch_jd(url)` → 按域名匹配 adapter → 返回 FetchResult。
包含持久化助手 `fetch_and_save(job_pool_id, url)`，失败也落 jd_status。

使用：
    from services.jd_fetcher import fetch_and_save
    result = fetch_and_save(job_pool_id=128, url="https://moonshot.jobs.feishu.cn/s/xxx")
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from urllib.parse import urlparse

from config import settings
from services.jd_adapters import pick, FetchResult

DB_PATH = settings.db_full_path


# 排除公司黑名单（CLAUDE.md 规定：字节/蚂蚁/腾讯/网易不投）
BLOCKED_DOMAINS = {
    "jobs.bytedance.com", "job.toutiao.com",
    "talent.antgroup.com", "alipay.com",
    "join.qq.com", "careers.tencent.com",
    "hr.163.com", "game.163.com",
}

BLOCKED_COMPANIES = {
    "字节跳动", "抖音", "TikTok", "ByteDance",
    "蚂蚁集团", "支付宝", "Alipay",
    "腾讯", "WeChat", "微信",
    "网易", "NetEase",
}


def is_blocked(url: str, company: str = "") -> bool:
    if company and company in BLOCKED_COMPANIES:
        return True
    host = urlparse(url).netloc.lower() if url else ""
    return any(host.endswith(d) or host == d for d in BLOCKED_DOMAINS)


# Auto 白名单：已知可纯 Python 抓取的域名（SSR 或有公开 API）
AUTO_WHITELIST = {
    "jobs.lever.co",          # Lever API
    "boards.greenhouse.io",   # Greenhouse 常见 SSR
    "jobs.ashbyhq.com",       # Ashby JSON
    "cn.linkedin.com",        # LinkedIn jobs/view/* 是 SSR
    "www.linkedin.com",
    "linkedin.com",
}


def classify_mode(url: str, company: str = "") -> str:
    """按 URL + 公司名判断 jd_fetch_mode（白名单制）。

    - blocked: 黑名单公司/域名，不抓
    - manual:  邮箱、纯门户列表页、失效链接
    - auto:    白名单域名（Lever/Greenhouse/Ashby/LinkedIn jobs/view）
    - browser: 其他一切（默认 SPA，需 Chrome MCP 渲染）
    """
    if is_blocked(url, company):
        return "blocked"
    if not url or not url.startswith("http"):
        return "manual"

    host = urlparse(url).netloc.lower()

    # 明确 manual：企业首页/门户列表/邮箱
    if "nowcoder.com" in host or "linkedin.com/company" in url:
        return "manual"

    # LinkedIn 必须是具体 /jobs/view/ 才能抓
    if "linkedin.com" in host and "/jobs/view/" not in url:
        return "manual"

    # Auto 白名单命中
    if host in AUTO_WHITELIST or any(host.endswith("." + d) for d in AUTO_WHITELIST):
        return "auto"
    # LinkedIn 具体职位也归 auto
    if "linkedin.com" in host and "/jobs/view/" in url:
        return "auto"

    # 其他一切视为 SPA → browser
    return "browser"


def fetch_jd(url: str) -> FetchResult:
    """纯抓取，不落库。"""
    adapter = pick(url)
    if not adapter:
        return FetchResult(ok=False, source_url=url, error="no adapter matched")
    return adapter.fetch(url)


def fetch_and_save(job_pool_id: int, url: str) -> FetchResult:
    """抓取 + 落库 + 更新 jobs_pool.jd_status。"""
    result = fetch_jd(url)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    try:
        if result.ok:
            # 查 jobs_pool 基本信息
            row = conn.execute(
                'SELECT "公司", "岗位名称", "城市" FROM jobs_pool WHERE id = ?',
                (job_pool_id,),
            ).fetchone()
            if not row:
                result.ok = False
                result.error = f"job_pool_id {job_pool_id} not found"
                return result

            company_fb, title_fb, city_fb = row
            conn.execute(
                """INSERT INTO job_descriptions
                   (company, title, location, raw_text, source_url, status, notes)
                   VALUES (?, ?, ?, ?, ?, 'bookmarked', ?)""",
                (
                    result.company or company_fb,
                    result.title or title_fb,
                    result.location or city_fb,
                    result.raw_text,
                    url,
                    f"来源:岗位池#{job_pool_id}|adapter:{result.adapter_name}",
                ),
            )
            conn.execute(
                """UPDATE jobs_pool
                   SET jd_status='fetched', jd_fetched_at=?, jd_last_error=NULL
                   WHERE id=?""",
                (now, job_pool_id),
            )
        else:
            # needs_chrome → 特殊状态 needs_browser（不算永久失败）
            new_status = (
                "needs_browser" if result.meta.get("needs_chrome") else "failed"
            )
            conn.execute(
                """UPDATE jobs_pool
                   SET jd_status=?, jd_last_error=?
                   WHERE id=?""",
                (new_status, result.error[:500], job_pool_id),
            )
        conn.commit()
    finally:
        conn.close()

    return result


# ── CLI smoke test ──────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m services.jd_fetcher <url>")
        sys.exit(1)
    r = fetch_jd(sys.argv[1])
    print(f"ok={r.ok} adapter={r.adapter_name} error={r.error}")
    print(f"company={r.company} title={r.title} location={r.location}")
    print(f"meta={r.meta}")
    print("--- raw_text ---")
    print(r.raw_text[:500])
