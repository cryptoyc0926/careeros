"""ATS poller 基类：给定公司 slug → 返回岗位列表（直达链接）。

与 jd_adapters 的区别：
  - jd_adapters：URL → JD 详情（input 是一个具体岗位的 URL）
  - ats_pollers：公司 slug → 岗位列表（input 是公司标识，output 是 N 条直达 URL）

所有 poller 输出标准 JobLead（复用 job_crawler.JobLead）。
每次调用经 @instrument 装饰器写 logs/ats_poller_health.jsonl，便于零返回告警。
"""
from __future__ import annotations

import functools
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# 复用已有 JobLead（不重新定义）— 延迟 import 避免循环
def _get_job_lead_cls():
    from services.job_crawler import JobLead
    return JobLead


class PollerError(Exception):
    """poller 基础异常。"""


class NeedsBrowserError(PollerError):
    """标记该 tenant 纯 Python 无法处理，需要 Chrome MCP 在 skill 会话里兜底。"""


class SlugInvalid(PollerError):
    """ATS slug 不存在或已改名（区别于 zero results）。"""


# ── Health log ─────────────────────────────────────
# 写到 career-os-claudecode/logs/ats_poller_health.jsonl
_HEALTH_LOG = Path(__file__).resolve().parents[3] / "logs" / "ats_poller_health.jsonl"


def _append_health(record: dict) -> None:
    try:
        _HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _HEALTH_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # 健康日志失败不应阻断主流程
        pass


def instrument(fn: Callable) -> Callable:
    """装饰 Poller.list_jobs，记录每次调用的健康度数据。"""
    @functools.wraps(fn)
    def wrapper(self: "Poller", filters: dict | None = None, *args, **kwargs):
        filters = filters or {}
        t0 = time.time()
        slug = filters.get("slug") or getattr(self, "default_slug", "")
        err = ""
        count = 0
        tier = "tier1"
        try:
            leads = fn(self, filters, *args, **kwargs)
            count = len(leads or [])
            return leads
        except NeedsBrowserError as e:
            tier = "needs_browser"
            err = str(e)
            raise
        except SlugInvalid as e:
            err = f"slug_invalid: {e}"
            raise
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            raise
        finally:
            _append_health({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "poller": self.name,
                "slug": slug,
                "returned_count": count,
                "tier_used": tier,
                "duration_ms": int((time.time() - t0) * 1000),
                "error": err,
            })
    return wrapper


class Poller:
    """ATS poller 抽象基类。子类实现 list_jobs + match。"""
    name: str = "base"

    def list_jobs(self, filters: dict | None = None) -> list:  # returns list[JobLead]
        """输入 filters（dict，含 slug / q / city 等），输出 JobLead 列表。
        子类覆盖此方法并加 @instrument 装饰器。
        """
        raise NotImplementedError

    # 可选：简单的客户端侧过滤
    @staticmethod
    def _position_matches(position: str, q: str | None) -> bool:
        """q 支持逗号分隔的 OR 关键词：'运营,增长,海外' → 任一命中即通过。"""
        if not q:
            return True
        pos_low = (position or "").lower()
        tokens = [t.strip().lower() for t in q.split(",") if t.strip()]
        if not tokens:
            return True
        return any(t in pos_low for t in tokens)

    @staticmethod
    def _city_matches(city: str, target: str | None) -> bool:
        if not target:
            return True
        if not city:
            return False
        return target.strip() in city
