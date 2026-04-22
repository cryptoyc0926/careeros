"""ATS poller 注册表。用法：

    from services.ats_pollers import get_poller
    poller = get_poller("lever")
    leads = poller.list_jobs({"slug": "dify"})
"""
from __future__ import annotations

from .base import Poller, PollerError, NeedsBrowserError, SlugInvalid

__all__ = ["get_poller", "list_pollers", "Poller", "PollerError", "NeedsBrowserError", "SlugInvalid"]


def _registry() -> dict[str, type[Poller]]:
    # 延迟 import，避免顶层循环
    from .lever import LeverPoller
    reg: dict[str, type[Poller]] = {
        "lever": LeverPoller,
    }
    # 以下 poller 按 D2-D7 顺序加入，先做保护性 import
    try:
        from .greenhouse import GreenhousePoller
        reg["greenhouse"] = GreenhousePoller
    except ImportError:
        pass
    try:
        from .ashby import AshbyPoller
        reg["ashby"] = AshbyPoller
    except ImportError:
        pass
    try:
        from .feishu import FeishuPoller
        reg["feishu"] = FeishuPoller
    except ImportError:
        pass
    try:
        from .moka import MokaPoller
        reg["moka"] = MokaPoller
    except ImportError:
        pass
    try:
        from .static_html import StaticHtmlPoller
        reg["static_html"] = StaticHtmlPoller
    except ImportError:
        pass
    return reg


def get_poller(name: str) -> Poller:
    """返回 poller 实例。name 如 'lever' / 'greenhouse' / 'feishu' / 'moka' / 'ashby'。"""
    key = (name or "").strip().lower()
    reg = _registry()
    cls = reg.get(key)
    if cls is None:
        raise KeyError(f"unknown ATS poller: {name!r} (known: {sorted(reg.keys())})")
    return cls()


def list_pollers() -> list[str]:
    return sorted(_registry().keys())
