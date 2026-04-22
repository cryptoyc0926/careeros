#!/usr/bin/env python3
"""Career OS structural smoke test for the current product surface."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ACTIVE_PAGES = [
    "pages/home.py",
    "pages/job_pool.py",
    "pages/master_resume.py",
    "pages/resume_tailor.py",
    "pages/star_pool.py",
    "pages/settings_page.py",
    "pages/history_versions.py",
    "pages/resume_templates.py",
    "pages/case_library.py",
    "pages/help_feedback.py",
]

LEGACY_PAGE_FILES = [
    "pipeline.py",
    "email_composer.py",
    "interview.py",
    "interview_prep.py",
    "followup.py",
    "dashboard.py",
    "cheatsheet.py",
    "delivery_tracking.py",
    "interview_prep_v2.py",
    "story_bank.py",
]


passed: list[str] = []
failed: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"[PASS] {name}")
    else:
        failed.append((name, detail))
        print(f"[FAIL] {name}: {detail}")


print("Career OS current-surface smoke")
print("=" * 48)

app_source = (ROOT / "app.py").read_text(encoding="utf-8")

try:
    ast.parse(app_source)
    check("app.py parses", True)
except SyntaxError as exc:
    check("app.py parses", False, str(exc))

for page in ACTIVE_PAGES:
    check(f"active page exists: {page}", (ROOT / page).exists(), "missing")

for filename in LEGACY_PAGE_FILES:
    check(f"legacy page removed: {filename}", not (ROOT / "pages" / filename).exists(), "still exists")
    check(f"legacy page not routed: {filename}", filename not in app_source, "still referenced in app.py")

for page in [
    "pages/home.py",
    "pages/job_pool.py",
    "pages/master_resume.py",
    "pages/resume_tailor.py",
    "pages/settings_page.py",
]:
    source = (ROOT / page).read_text(encoding="utf-8")
    check(f"{page} has content", len(source.strip()) > 100, "unexpectedly small")

print("=" * 48)
print(f"passed={len(passed)} failed={len(failed)}")

if failed:
    for name, detail in failed:
        print(f"- {name}: {detail}")
    raise SystemExit(1)
