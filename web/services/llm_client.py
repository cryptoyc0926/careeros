"""
LLM 客户端统一封装 + 友好错误提示
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
所有调 Claude / Kimi / GLM / DeepSeek / Codex(OpenAI-wire) 的地方都通过这里。

设计：
- 业务层只认 Anthropic 的 `client.messages.create(...)` 接口
- Anthropic-wire provider (anthropic/kimi/glm/deepseek) → 返回原生 Anthropic client
- OpenAI-wire provider (codex/openai) → 返回 OpenAICompatClient（同签名 adapter）

同时：
- 公开池（Codex Shared Key）兜底：用户没填 Key 但选了 codex → 自动读 Streamlit secrets 里的共享 Key
- session 级额度控制：每次调用后估算 cost 累加，超 $0.5 提示换自己 Key
"""
from __future__ import annotations

import os
from typing import Any


def _safe_str(obj: Any) -> str:
    """保证返回的字符串是 UTF-8 安全的。"""
    try:
        s = str(obj)
    except Exception:
        s = repr(obj)
    try:
        return s.encode("utf-8", errors="replace").decode("utf-8")
    except Exception:
        return s.encode("ascii", errors="replace").decode("ascii")


# ═════════════════════════════════════════════════════════════════
# 公开池 · session 级额度追踪
# ═════════════════════════════════════════════════════════════════

# 粗略定价（美元 / 1K tokens）· 按 GPT-4o 参考 · 其他模型可能偏差
_MODEL_PRICING = {
    "gpt-4o":         {"in": 0.0025, "out": 0.010},
    "gpt-4o-mini":    {"in": 0.00015, "out": 0.0006},
    "gpt-5.4":        {"in": 0.003,  "out": 0.015},   # Codex 代理自定义模型，定价估算
    "gpt-4-turbo":    {"in": 0.010,  "out": 0.030},
    "_default":       {"in": 0.003,  "out": 0.015},
}


def _estimate_cost_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    """按模型估算本次调用花费（美元）。"""
    price = _MODEL_PRICING.get(model, _MODEL_PRICING["_default"])
    return (in_tokens / 1000.0) * price["in"] + (out_tokens / 1000.0) * price["out"]


def _is_using_shared_pool() -> bool:
    """当前调用是否走"公开池共享 Key"（而非用户自己的 Key）。"""
    try:
        from config import settings
        if not settings.is_openai_wire:
            return False
        # session_state 里没 Key（用户没填），但 provider=codex 且 secrets 有 shared key
        import streamlit as st
        user_key = st.session_state.get("ANTHROPIC_API_KEY", "")
        return (not user_key) and bool(settings.codex_shared_key)
    except Exception:
        return False


def _accumulate_pool_spend(cost_usd: float) -> float:
    """累加 session 级公开池花费，返回累计值。"""
    try:
        import streamlit as st
        cur = float(st.session_state.get("_pool_spend_usd", 0.0) or 0.0)
        cur += cost_usd
        st.session_state["_pool_spend_usd"] = cur
        return cur
    except Exception:
        return 0.0


def get_pool_remaining_usd() -> float:
    """查询当前 session 公开池剩余预算（供 UI 显示）。"""
    try:
        from config import settings
        import streamlit as st
        spent = float(st.session_state.get("_pool_spend_usd", 0.0) or 0.0)
        budget = settings.codex_per_session_budget_usd
        return max(0.0, budget - spent)
    except Exception:
        return 0.0


# ═════════════════════════════════════════════════════════════════
# OpenAI → Anthropic 签名 adapter
# ═════════════════════════════════════════════════════════════════

class _TextBlock:
    __slots__ = ("text", "type")

    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class _UsageWrap:
    __slots__ = ("input_tokens", "output_tokens")

    def __init__(self, oa_usage):
        self.input_tokens = int(getattr(oa_usage, "prompt_tokens", 0) or 0)
        self.output_tokens = int(getattr(oa_usage, "completion_tokens", 0) or 0)


class _AnthropicLikeResponse:
    """模拟 Anthropic SDK 的 Message 对象，让业务层 `resp.content[0].text` 可用。"""
    def __init__(self, text: str, usage=None):
        self.content = [_TextBlock(text or "")]
        self.usage = _UsageWrap(usage) if usage is not None else None
        self.stop_reason = "end_turn"
        self.role = "assistant"


class _MessagesProxy:
    """把 client.messages.create(...) 路由到 OpenAI chat.completions.create(...)。"""
    def __init__(self, oa_client, using_shared_pool: bool = False):
        self._oa = oa_client
        self._using_shared_pool = using_shared_pool

    def create(self, *, model: str, messages: list[dict], system: str | None = None,
               max_tokens: int = 1024, temperature: float = 0.7,
               tools: list | None = None, **_kwargs) -> _AnthropicLikeResponse:
        # 公开池预算前置检查
        if self._using_shared_pool:
            remaining = get_pool_remaining_usd()
            if remaining <= 0:
                raise RuntimeError(
                    "公开池试玩额度已用完（本次会话）。请到「系统设置 → LLM 配置」填入你自己的 API Key，"
                    "或关闭浏览器重开获得新 session。"
                )

        # Anthropic messages → OpenAI messages
        oa_msgs = []
        if system:
            oa_msgs.append({"role": "system", "content": system})
        for m in messages:
            c = m.get("content", "")
            if isinstance(c, list):
                # content blocks → 拼成纯文本
                parts = []
                for b in c:
                    if isinstance(b, dict):
                        if b.get("type") == "text" or "text" in b:
                            parts.append(str(b.get("text", "")))
                c = "\n".join(parts)
            oa_msgs.append({"role": m["role"], "content": str(c)})

        # 调用 OpenAI
        resp = self._oa.chat.completions.create(
            model=model,
            messages=oa_msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = resp.choices[0] if resp.choices else None
        text = choice.message.content if choice and choice.message else ""
        usage = getattr(resp, "usage", None)

        # 公开池额度累计
        if self._using_shared_pool and usage is not None:
            cost = _estimate_cost_usd(model,
                                       getattr(usage, "prompt_tokens", 0) or 0,
                                       getattr(usage, "completion_tokens", 0) or 0)
            _accumulate_pool_spend(cost)

        return _AnthropicLikeResponse(text, usage)


class OpenAICompatClient:
    """业务层看起来像 Anthropic client，但底层走 OpenAI chat.completions。"""
    def __init__(self, oa_client, using_shared_pool: bool = False):
        self._oa = oa_client
        self.messages = _MessagesProxy(oa_client, using_shared_pool=using_shared_pool)


# ═════════════════════════════════════════════════════════════════
# 客户端工厂
# ═════════════════════════════════════════════════════════════════

def make_client():
    """根据 settings.llm_provider 构造对应的客户端。

    anthropic / kimi / glm / deepseek → 原生 Anthropic SDK
    codex / openai                     → OpenAICompatClient（adapter）
    """
    from config import settings

    if settings.is_openai_wire:
        return _make_openai_client()

    # Anthropic-wire
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("缺少 anthropic SDK，请运行 `pip install anthropic>=0.39`") from e

    if not settings.has_anthropic_key:
        raise RuntimeError("API Key 未配置。请到「系统设置」填入你的 Key 后重试。")

    kwargs: dict[str, Any] = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    return Anthropic(**kwargs)


def _make_openai_client() -> OpenAICompatClient:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("缺少 openai SDK，请运行 `pip install openai>=1.40`") from e

    from config import settings

    # 优先用用户自己的 Key（BYO-Key），没填则 fallback 到公开池 Shared Key
    user_key = settings.anthropic_api_key  # 复用 ANTHROPIC_API_KEY 字段作为"当前活跃 Key"
    using_shared = False
    if not user_key and settings.codex_shared_key:
        user_key = settings.codex_shared_key
        using_shared = True

    if not user_key:
        raise RuntimeError(
            "OpenAI 协议 provider 需要 API Key。请到「系统设置 → LLM 配置」填入你的 Key；"
            "或联系作者开启「Codex 公开池」试玩额度。"
        )

    base_url = settings.anthropic_base_url
    oa_client = OpenAI(api_key=user_key, base_url=base_url or None)
    return OpenAICompatClient(oa_client, using_shared_pool=using_shared)


# ═════════════════════════════════════════════════════════════════
# 错误翻译（同时支持 Anthropic + OpenAI 异常）
# ═════════════════════════════════════════════════════════════════

def friendly_error(e: Exception) -> str:
    """把任意 SDK 异常翻译成用户能看懂的中文提示。"""
    raw_msg = _safe_str(e)
    cls_name = type(e).__name__

    # OpenAI 异常优先检测（sdk 版本不同，不直接 import 以免 ImportError）
    if "authentication" in cls_name.lower() or "401" in raw_msg or "invalid_api_key" in raw_msg.lower():
        if "exhausted" in raw_msg.lower() or "用尽" in raw_msg or "insufficient" in raw_msg.lower() or "quota" in raw_msg.lower():
            return (
                "API Key 额度已用尽。请到「系统设置」换一个有余额的 Key，"
                "或给当前代理充值。详细错误：" + raw_msg[:300]
            )
        if "invalid" in raw_msg.lower() or "无效" in raw_msg or "failed" in raw_msg.lower():
            return "API Key 无效，请检查是否粘贴正确、是否过期。详细错误：" + raw_msg[:300]
        return "API 鉴权失败：" + raw_msg[:400]

    if "ratelimit" in cls_name.lower() or "429" in raw_msg or "rate_limit" in raw_msg.lower():
        return "触发限流（每分钟请求次数超限）。请等 1 分钟后重试。详细：" + raw_msg[:300]

    if "timeout" in cls_name.lower() or "timed out" in raw_msg.lower():
        return "API 请求超时。可能是代理不通或模型响应慢，建议切换 provider 或重试。详细：" + raw_msg[:200]

    if "connection" in cls_name.lower() or "connect" in raw_msg.lower():
        return (
            "无法连接到 API 端点。请检查「系统设置」里的 base_url 是否正确，"
            "以及当前网络能否访问。详细：" + raw_msg[:300]
        )

    if "badrequest" in cls_name.lower() or "400" in raw_msg:
        return "请求参数错误（通常是模型名不对或不支持某个参数）。详细：" + raw_msg[:400]

    if "notfound" in cls_name.lower() or "404" in raw_msg:
        return "API 端点或模型不存在。请检查 base_url 和模型名。详细：" + raw_msg[:400]

    if "UnicodeEncodeError" in cls_name or "UnicodeError" in cls_name:
        return (
            "字符编码异常（通常是云端 locale 不支持中文导致）。请尝试刷新页面重试；"
            "或切换到更干净的 provider（如 Claude 官方）。详细：" + raw_msg[:300]
        )

    # Anthropic SDK 原生异常（若 import 可用则精准匹配）
    try:
        from anthropic import (
            AuthenticationError, RateLimitError, APIStatusError,
            APIConnectionError, APITimeoutError, BadRequestError,
        )
        if isinstance(e, (AuthenticationError,)):
            return "API 鉴权失败：" + raw_msg[:400]
        if isinstance(e, RateLimitError):
            return "触发限流：" + raw_msg[:300]
        if isinstance(e, APITimeoutError):
            return "请求超时：" + raw_msg[:200]
        if isinstance(e, APIConnectionError):
            return "连接失败：" + raw_msg[:300]
        if isinstance(e, BadRequestError):
            return "参数错误：" + raw_msg[:400]
        if isinstance(e, APIStatusError):
            return f"HTTP {getattr(e, 'status_code', '?')}：{raw_msg[:400]}"
    except ImportError:
        pass

    return f"{cls_name}：{raw_msg[:400]}"
