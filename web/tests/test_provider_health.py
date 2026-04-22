from __future__ import annotations

from types import SimpleNamespace
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.provider_health import ping_provider  # noqa: E402


def test_anthropic_ping_reports_missing_key_without_calling_client():
    called = False

    def fake_client_factory(_config):
        nonlocal called
        called = True

    result = ping_provider(
        provider="anthropic",
        api_key="",
        client_factory=fake_client_factory,
    )

    assert not result.ok
    assert result.status == "missing_config"
    assert "API Key" in result.message
    assert called is False


def test_codex_ping_uses_shared_key_when_user_key_empty():
    seen = {}

    class FakeMessages:
        def create(self, **kwargs):
            seen["call"] = kwargs
            return SimpleNamespace(content=[SimpleNamespace(text="pong")])

    def fake_client_factory(config):
        seen["config"] = config
        return SimpleNamespace(messages=FakeMessages())

    result = ping_provider(
        provider="codex",
        api_key="",
        codex_shared_key="shared-codex-key",
        client_factory=fake_client_factory,
    )

    assert result.ok
    assert result.status == "success"
    assert result.provider == "codex"
    assert result.reply == "pong"
    assert seen["config"].api_key == "shared-codex-key"
    assert seen["config"].using_shared_key is True
    assert seen["call"]["model"] == seen["config"].model
