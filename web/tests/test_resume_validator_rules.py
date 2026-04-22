from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_validator import validate_tailored  # noqa: E402


MASTER = {
    "profile": "有 AI 增长经验。",
    "projects": [],
    "internships": [
        {
            "company": "Fancy Tech",
            "role": "海外产品运营实习生",
            "date": "2024.06 - 2024.09",
            "bullets": ["产出 30+ 页竞品画像，官网 UV 到 200+"],
        }
    ],
    "education": [],
}


def test_naked_numbers_are_warnings_not_hard_errors():
    tailored = {
        "profile": "有 AI 增长经验。",
        "projects": [],
        "internships": [
            {
                "company": "Fancy Tech",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": ["产出 30+ 页竞品画像，官网 UV 到 200+"],
            }
        ],
    }

    report = validate_tailored(MASTER, tailored, None)

    assert report.ok
    assert not report.hard_errors
    assert any(w.rule == "number_not_bolded" for w in report.warnings)


def test_changed_company_remains_hard_error():
    tailored = {
        "profile": "有 AI 增长经验。",
        "projects": [],
        "internships": [
            {
                "company": "Fancy Tech Co",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": ["产出 30+ 页竞品画像，官网 UV 到 200+"],
            }
        ],
    }

    report = validate_tailored(MASTER, tailored, None)

    assert not report.ok
    assert any(e.rule == "company_changed" for e in report.hard_errors)
