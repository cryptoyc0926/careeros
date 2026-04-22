#!/usr/bin/env python3
"""Smoke-test configured LLM providers from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
sys.path.insert(0, str(WEB_ROOT))

from config import settings  # noqa: E402
from services.provider_health import PROVIDER_PRESETS, ping_current_provider, ping_provider  # noqa: E402


def _print_result(result, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False))
        return
    mark = "OK" if result.ok else "FAIL"
    print(f"[{mark}] {result.provider} · {result.model} · {result.status}")
    print(f"      {result.message}")
    if result.reply:
        print(f"      reply: {result.reply[:120]}")
    if result.base_url:
        print(f"      base_url: {result.base_url}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ping CareerOS LLM provider config.")
    parser.add_argument(
        "--provider",
        default="current",
        choices=["current", "all", *PROVIDER_PRESETS.keys()],
        help="Provider to ping. Defaults to current app settings.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON lines.")
    args = parser.parse_args(argv)

    if args.provider == "current":
        result = ping_current_provider()
        _print_result(result, as_json=args.json)
        return 0 if result.ok else 1

    providers = list(PROVIDER_PRESETS) if args.provider == "all" else [args.provider]
    failures = 0
    for provider in providers:
        result = ping_provider(
            provider=provider,
            api_key=settings.anthropic_api_key,
            codex_shared_key=settings.codex_shared_key,
        )
        _print_result(result, as_json=args.json)
        if not result.ok:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
