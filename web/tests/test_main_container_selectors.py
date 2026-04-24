from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_app_uses_stmain_block_container_selector_for_default_width():
    source = _read("app.py")

    assert "section[data-testid=\"stMain\"] > [data-testid=\"stMainBlockContainer\"]" in source
    assert "[data-testid=\"stMain\"] .block-container" in source
    assert "max-width: 1080px !important;" in source
    assert ".main .block-container" not in source


def test_resume_tailor_overrides_canvas_width_with_higher_specificity():
    source = _read("pages/resume_tailor.py")

    assert "section[data-testid=\"stMain\"] > [data-testid=\"stMainBlockContainer\"]" in source
    assert "section[data-testid=\"stMain\"] .block-container" in source
    assert "div[data-testid=\"stMainBlockContainer\"]" in source
    assert "max-width: none !important;" in source
    assert ".main .block-container" not in source


def test_resume_canvas_keeps_non_rt_fallback_width_rule():
    source = _read("components/resume_canvas.py")

    assert "div.block-container," in source
    assert "[data-testid=\"stMainBlockContainer\"]{" in source
    assert "max-width: 1480px !important;" in source
