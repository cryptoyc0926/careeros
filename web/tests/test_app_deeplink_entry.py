import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def _load_deeplink_symbols():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "_DEEPLINK_SLUGS" in targets:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_requested_deeplink_slug":
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_requested_default_page_slug":
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_should_enter_app_from_request":
            selected.append(node)

    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {}
    exec(compile(module, str(APP), "exec"), namespace)
    return (
        namespace["_DEEPLINK_SLUGS"],
        namespace["_requested_deeplink_slug"],
        namespace["_requested_default_page_slug"],
        namespace["_should_enter_app_from_request"],
    )


def test_app_deeplink_helper_covers_active_slugs():
    slugs, _requested_slug, _requested_default_slug, should_enter = _load_deeplink_symbols()

    assert "resume_tailor" in slugs
    assert "settings_page" in slugs

    assert should_enter({}, "https://careeros-chad.streamlit.app/resume_tailor")
    assert should_enter({}, "https://careeros-chad.streamlit.app/settings_page")
    assert should_enter({"app": "1"}, "https://careeros-chad.streamlit.app/")
    assert should_enter({"page": "resume_tailor"}, "https://careeros-chad.streamlit.app/")
    assert not should_enter({}, "https://careeros-chad.streamlit.app/")


def test_app_deeplink_slug_helper_maps_query_page_to_page_file():
    slugs, requested_slug, requested_default_slug, _should_enter = _load_deeplink_symbols()

    assert requested_slug({"page": "resume_tailor"}, "https://careeros-chad.streamlit.app/") == "resume_tailor"
    assert requested_slug({}, "https://careeros-chad.streamlit.app/settings_page") == "settings_page"
    assert requested_default_slug({"page": "resume_tailor"}, "https://careeros-chad.streamlit.app/") == "resume_tailor"
    assert requested_default_slug({}, "https://careeros-chad.streamlit.app/settings_page") is None
    assert requested_default_slug({"page": "nope"}, "https://careeros-chad.streamlit.app/") is None
    assert "resume_tailor" in slugs
