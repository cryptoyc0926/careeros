"""LLM provider health checks used by Settings and CLI smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "codex": {
        "label": "Codex 免费共享",
        "wire": "openai",
        "base_url": "https://navacodex.shop/v1",
        "model": "gpt-5.4",
    },
    "anthropic": {
        "label": "Claude (Anthropic 官方)",
        "wire": "anthropic",
        "base_url": "",
        "model": "claude-sonnet-4-6",
    },
    "openai": {
        "label": "OpenAI (官方)",
        "wire": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "kimi": {
        "label": "Kimi (月之暗面)",
        "wire": "anthropic",
        "base_url": "https://api.moonshot.cn/anthropic",
        "model": "kimi-k2-0905-preview",
    },
    "glm": {
        "label": "智谱 GLM-4.6",
        "wire": "anthropic",
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "model": "glm-4.6",
    },
    "deepseek": {
        "label": "DeepSeek",
        "wire": "anthropic",
        "base_url": "https://api.deepseek.com/anthropic",
        "model": "deepseek-chat",
    },
    "proxy": {
        "label": "自定义代理",
        "wire": "anthropic",
        "base_url": "",
        "model": "claude-sonnet-4-6",
    },
}


@dataclass(frozen=True)
class ProviderProbeConfig:
    provider: str
    label: str
    wire: str
    api_key: str
    base_url: str
    model: str
    using_shared_key: bool = False


@dataclass(frozen=True)
class ProviderPingResult:
    provider: str
    label: str
    model: str
    base_url: str
    status: str
    message: str
    reply: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "label": self.label,
            "model": self.model,
            "base_url": self.base_url,
            "status": self.status,
            "message": self.message,
            "reply": self.reply,
            "error": self.error,
            "ok": self.ok,
        }


ClientFactory = Callable[[ProviderProbeConfig], Any]


def build_provider_probe_config(
    provider: str,
    *,
    api_key: str = "",
    base_url: str | None = None,
    model: str | None = None,
    codex_shared_key: str = "",
) -> ProviderProbeConfig:
    provider_key = (provider or "codex").lower()
    preset = PROVIDER_PRESETS.get(provider_key)
    if not preset:
        preset = {
            "label": provider_key,
            "wire": "anthropic",
            "base_url": "",
            "model": "claude-sonnet-4-6",
        }

    effective_key = (api_key or "").strip()
    using_shared = False
    if not effective_key and provider_key == "codex" and codex_shared_key:
        effective_key = codex_shared_key.strip()
        using_shared = bool(effective_key)

    return ProviderProbeConfig(
        provider=provider_key,
        label=preset["label"],
        wire=preset["wire"],
        api_key=effective_key,
        base_url=preset["base_url"] if base_url is None else str(base_url or ""),
        model=preset["model"] if model is None else str(model or preset["model"]),
        using_shared_key=using_shared,
    )


def _make_probe_client(config: ProviderProbeConfig) -> Any:
    if config.wire == "openai":
        from openai import OpenAI

        from services.llm_client import OpenAICompatClient

        client = OpenAI(api_key=config.api_key, base_url=config.base_url or None)
        return OpenAICompatClient(client, using_shared_pool=config.using_shared_key)

    from anthropic import Anthropic

    kwargs: dict[str, Any] = {"api_key": config.api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return Anthropic(**kwargs)


def _response_text(resp: Any) -> str:
    content = getattr(resp, "content", None) or []
    if not content:
        return ""
    first = content[0]
    if isinstance(first, dict):
        return str(first.get("text", "") or "")
    return str(getattr(first, "text", "") or "")


def ping_provider(
    *,
    provider: str,
    api_key: str = "",
    base_url: str | None = None,
    model: str | None = None,
    codex_shared_key: str = "",
    client_factory: ClientFactory | None = None,
) -> ProviderPingResult:
    """Run a minimal real provider ping, or return a real config failure."""
    config = build_provider_probe_config(
        provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        codex_shared_key=codex_shared_key,
    )
    if not config.api_key:
        return ProviderPingResult(
            provider=config.provider,
            label=config.label,
            model=config.model,
            base_url=config.base_url,
            status="missing_config",
            message="API Key 未配置，无法发起真实连接测试。",
        )

    try:
        client = client_factory(config) if client_factory else _make_probe_client(config)
        resp = client.messages.create(
            model=config.model,
            max_tokens=16,
            temperature=0,
            messages=[{"role": "user", "content": "ping"}],
        )
        reply = _response_text(resp) or "(空响应)"
        key_source = "共享 Key" if config.using_shared_key else "当前 Key"
        return ProviderPingResult(
            provider=config.provider,
            label=config.label,
            model=config.model,
            base_url=config.base_url,
            status="success",
            message=f"{config.label} 连接成功（{key_source}）。",
            reply=reply,
        )
    except Exception as e:
        try:
            from services.llm_client import friendly_error

            msg = friendly_error(e)
        except Exception:
            msg = f"{type(e).__name__}: {e}"
        return ProviderPingResult(
            provider=config.provider,
            label=config.label,
            model=config.model,
            base_url=config.base_url,
            status="error",
            message=msg,
            error=f"{type(e).__name__}: {e}",
        )


def ping_current_provider() -> ProviderPingResult:
    """Ping the provider currently selected in app settings."""
    from config import settings

    return ping_provider(
        provider=settings.llm_provider,
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
        model=settings.claude_model,
        codex_shared_key=settings.codex_shared_key,
    )
