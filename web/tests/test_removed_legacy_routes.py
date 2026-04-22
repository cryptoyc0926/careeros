from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_app_navigation_excludes_legacy_product_sections() -> None:
    app_source = _read("app.py")

    legacy_tokens = [
        "pages/pipeline.py",
        "pages/email_composer.py",
        "pages/interview.py",
        "pages/interview_prep.py",
        "pages/followup.py",
        "pages/dashboard.py",
        "pages/cheatsheet.py",
        "pages/delivery_tracking.py",
        "pages/interview_prep_v2.py",
        "pages/story_bank.py",
        '"投递进度"',
        "投递追踪",
        "看板追踪",
        "邮件撰写",
        "模拟面试",
        "面试准备",
        "题库 & 故事",
        "跟进提醒",
    ]

    found = [token for token in legacy_tokens if token in app_source]
    assert found == []


def test_home_page_does_not_link_to_legacy_product_entries() -> None:
    home_source = _read("pages/home.py")

    legacy_tokens = [
        "pages/pipeline.py",
        "pages/email_composer.py",
        "pages/interview.py",
        "pages/interview_prep.py",
        "pages/followup.py",
        "pages/dashboard.py",
        "pages/cheatsheet.py",
        "pages/delivery_tracking.py",
        "pages/interview_prep_v2.py",
        "pages/story_bank.py",
        "进度追踪",
        "投递追踪",
        "面试准备",
        "检查跟进提醒",
    ]

    found = [token for token in legacy_tokens if token in home_source]
    assert found == []


def test_legacy_files_physically_deleted() -> None:
    legacy = [
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
    pages_dir = ROOT / "pages"

    existing = [filename for filename in legacy if (pages_dir / filename).exists()]

    assert existing == [], f"Legacy pages still exist: {existing}"
