"""
Career OS — Centralised Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads settings from .env via python-dotenv.
Every module imports `settings` from here — single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

try:
    import yaml  # PyYAML — 已在 requirements.txt
except ImportError:
    yaml = None

# Project root is wherever this file lives
_ROOT = Path(__file__).resolve().parent

# Load .env file
load_dotenv(_ROOT / ".env", override=True)

# 用户画像文件位置（相对项目根上一级）
_USER_PROFILE_PATH = (_ROOT.parent / "data" / "user_profile.yaml")
_USER_PROFILE_EXAMPLE = (_ROOT.parent / "data" / "user_profile.example.yaml")


class Settings:
    """Application settings loaded from environment / .env file."""

    # ── Anthropic ────────────────────────────────────────────
    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def anthropic_base_url(self) -> str:
        """自定义 API 端点（留空则使用 Anthropic 官方地址）"""
        return os.getenv("ANTHROPIC_BASE_URL", "")

    @property
    def claude_model(self) -> str:
        return os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    # ── Email (SMTP) ────────────────────────────────────────
    @property
    def smtp_host(self) -> str:
        return os.getenv("SMTP_HOST", "smtp.gmail.com")

    @property
    def smtp_port(self) -> int:
        return int(os.getenv("SMTP_PORT", "587"))

    @property
    def smtp_user(self) -> str:
        return os.getenv("SMTP_USER", "")

    @property
    def smtp_password(self) -> str:
        return os.getenv("SMTP_PASSWORD", "")

    # ── Email (SendGrid) ────────────────────────────────────
    @property
    def sendgrid_api_key(self) -> str:
        return os.getenv("SENDGRID_API_KEY", "")

    # ── Paths ───────────────────────────────────────────────
    @property
    def db_path(self) -> str:
        return os.getenv("DB_PATH", "../data/career_os.db")

    @property
    def master_resume_path(self) -> str:
        return os.getenv("MASTER_RESUME_PATH", "data/master_resume.yaml")

    @property
    def output_dir(self) -> str:
        return os.getenv("OUTPUT_DIR", "output/")

    # ── Derived helpers ─────────────────────────────────────
    @property
    def project_root(self) -> Path:
        return _ROOT

    @property
    def db_full_path(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else _ROOT / p

    @property
    def master_resume_full_path(self) -> Path:
        p = Path(self.master_resume_path)
        return p if p.is_absolute() else _ROOT / p

    @property
    def output_full_path(self) -> Path:
        p = Path(self.output_dir)
        return p if p.is_absolute() else _ROOT / p

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key not in ("", "sk-ant-your-key-here"))

    @property
    def has_custom_base_url(self) -> bool:
        return bool(self.anthropic_base_url)

    @property
    def has_smtp(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def has_sendgrid(self) -> bool:
        return bool(self.sendgrid_api_key)

    def masked_key(self, key: str, visible: int = 4) -> str:
        """Return a masked version of a secret, showing only the last N chars."""
        if not key or len(key) <= visible:
            return "••••"
        return "•" * 8 + key[-visible:]

    # ── 用户画像 ────────────────────────────────────────────
    @property
    def user_profile_path(self) -> Path:
        return _USER_PROFILE_PATH

    @property
    def has_user_profile(self) -> bool:
        return _USER_PROFILE_PATH.exists()

    @property
    def user_profile(self) -> dict:
        """读取 data/user_profile.yaml，如果不存在返回空 dict。
        外部调用：settings.user_profile.get('user', {}).get('name', '')
        """
        if yaml is None:
            return {}
        if not _USER_PROFILE_PATH.exists():
            # 首次启动，尝试 fallback 到 example（只读参考，不做任何写入）
            if _USER_PROFILE_EXAMPLE.exists():
                try:
                    return yaml.safe_load(_USER_PROFILE_EXAMPLE.read_text(encoding="utf-8")) or {}
                except Exception:
                    return {}
            return {}
        try:
            return yaml.safe_load(_USER_PROFILE_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def save_user_profile(self, data: dict) -> None:
        """把 user_profile 写回 data/user_profile.yaml。"""
        if yaml is None:
            raise RuntimeError("PyYAML 未安装，无法保存 user_profile")
        _USER_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _USER_PROFILE_PATH.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    # ── Demo 模式（Phase I）────────────────────────────────
    @property
    def demo_mode(self) -> bool:
        """DEMO_MODE=true 时启用 BYO-Key 模式、禁用真实邮件发送等。"""
        return os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call this everywhere."""
    return Settings()


# Convenience alias
settings = get_settings()
