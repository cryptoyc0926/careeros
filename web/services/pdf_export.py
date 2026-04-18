"""
PDF 简历导出 — Markdown → HTML → PDF (WeasyPrint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
中文字体适配，ATS 友好的单栏布局。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from jinja2 import Template
import markdown


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _get_template() -> Template:
    tpl_path = _TEMPLATE_DIR / "resume_zh.html"
    return Template(tpl_path.read_text(encoding="utf-8"))


def markdown_to_pdf(md_text: str, output_path: Path | None = None) -> Path:
    """将 Markdown 简历转换为 ATS 友好的 PDF。

    Args:
        md_text: Markdown 格式的简历内容
        output_path: 输出路径，None 则自动生成临时文件

    Returns:
        生成的 PDF 文件路径
    """
    from weasyprint import HTML

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    template = _get_template()
    full_html = template.render(body=html_body)

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = Path(tmp.name)
        tmp.close()

    HTML(string=full_html).write_pdf(str(output_path))
    return output_path
