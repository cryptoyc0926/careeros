from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class SidebarRestoreTest(unittest.TestCase):
    def test_main_app_exposes_expand_sidebar_button_after_collapse(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('[data-testid="stToolbar"]', app_source)
        self.assertIn('[data-testid="stExpandSidebarButton"]', app_source)
        self.assertIn("展开导航", app_source)


if __name__ == "__main__":
    unittest.main()
