"""
LLM 客户端统一封装 + 友好错误提示
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
所有调 Claude / Kimi / GLM / DeepSeek 的地方都应该通过这里，统一：
- 客户端构造（注入 base_url）
- 错误转换（把 SDK 的 AuthError / RateLimitError / APIError 转成中文人话）
- UTF-8 安全（防云端 locale 把中文错误消息炸成 UnicodeEncodeError）
"""
from __future__ import annotations

import os
from typing import Any


def _safe_str(obj: Any) -> str:
    """保证返回的字符串是 UTF-8 安全的（防云端 ASCII-only locale）。"""
    try:
        s = str(obj)
    except Exception:
        s = repr(obj)
    # 尝试 encode/decode 一轮，确保不会在后续 logging/header 崩溃
    try:
        return s.encode("utf-8", errors="replace").decode("utf-8")
    except Exception:
        return s.encode("ascii", errors="replace").decode("ascii")


def make_client():
    """根据 settings 构造 Anthropic 客户端（支持多 provider 的兼容端点）。"""
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("缺少 anthropic SDK，请运行 `pip install anthropic>=0.39`") from e

    from config import settings

    if not settings.has_anthropic_key:
        raise RuntimeError("API Key 未配置。请到「系统设置」填入你的 Key 后重试。")

    kwargs: dict[str, Any] = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    return Anthropic(**kwargs)


def friendly_error(e: Exception) -> str:
    """把任意 SDK 异常翻译成用户能看懂的中文提示。"""
    from anthropic import (
        AuthenticationError, RateLimitError, APIStatusError,
        APIConnectionError, APITimeoutError, BadRequestError,
    )

    raw_msg = _safe_str(e)
    # 不同错误类的友好翻译
    if isinstance(e, AuthenticationError):
        if "用尽" in raw_msg or "exhausted" in raw_msg.lower() or "remain" in raw_msg.lower():
            return (
                "API Key 额度已用尽。请到「系统设置」换一个有余额的 Key，"
                "或给当前代理充值。详细错误：" + raw_msg[:300]
            )
        if "invalid" in raw_msg.lower() or "无效" in raw_msg or "失效" in raw_msg:
            return "API Key 无效，请检查是否粘贴正确、是否过期。详细错误：" + raw_msg[:300]
        return "API 鉴权失败：" + raw_msg[:400]

    if isinstance(e, RateLimitError):
        return "触发限流（每分钟请求次数超限）。请等 1 分钟后重试，或切换到更高配额的模型。详细：" + raw_msg[:300]

    if isinstance(e, APITimeoutError):
        return "API 请求超时。可能是代理不通或模型响应慢，建议切换 provider 或重试。详细：" + raw_msg[:200]

    if isinstance(e, APIConnectionError):
        return (
            "无法连接到 API 端点。请检查「系统设置」里的 base_url 是否正确，"
            "以及当前网络能否访问。详细：" + raw_msg[:300]
        )

    if isinstance(e, BadRequestError):
        return "请求参数错误（通常是模型名不对或不支持某个参数）。详细：" + raw_msg[:400]

    if isinstance(e, APIStatusError):
        return f"API 返回错误状态码 {getattr(e, 'status_code', '?')}：{raw_msg[:400]}"

    # 非 SDK 异常（可能是 httpx / asyncio 相关）
    if "UnicodeEncodeError" in type(e).__name__ or "UnicodeError" in type(e).__name__:
        return (
            "字符编码异常（通常是云端 locale 不支持中文导致）。请尝试刷新页面重试；"
            "或切换到更干净的 provider（如 Claude 官方）。详细：" + raw_msg[:300]
        )

    return f"{type(e).__name__}：{raw_msg[:400]}"
