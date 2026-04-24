from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_demo_pages_do_not_expose_real_contact_info():
    targets = [
        ROOT / "pages" / "landing.py",
        ROOT / "pages" / "resume_tailor.py",
    ]
    leaked_tokens = [
        "杨超",
        "杨 超",
        "杨　超",
        "186-8795-0926",
        "bc1chao0926@gmail.com",
        "YC",
    ]

    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)

    for token in leaked_tokens:
        assert token not in combined
