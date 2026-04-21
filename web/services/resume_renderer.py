"""
Resume Renderer — 结构化 JSON → HTML → PDF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
使用 Jinja2 模板 resume_default_tmpl.html，配合 WeasyPrint 生成单页 A4 PDF。

数据结构（resume_master 表 / resume_versions.content_json）:
{
  "basics": {
    "name": "你的姓名",
    "phone": "13800000000",
    "email": "you@example.com",
    "target_role": "目标岗位",
    "city": "目标城市",
    "availability": "到岗时间",
    "photo": ""  # 相对 templates/ 的路径，可选；为空则不显示照片
  },
  "profile": "你的个人总结...（支持 <b> 加粗）",
  "projects": [
    {
      "company": "项目名",
      "role": "担任角色",
      "date": "YYYY.MM - YYYY.MM",
      "bullets": ["核心贡献 <b>量化成果</b>", "..."]
    }
  ],
  "internships": [ { company, role, date, bullets } ],
  "skills": [ { "label": "技能分类", "text": "具体技能" } ],
  "education": [
    { "school": "学校名", "major": "专业",
      "date": "YYYY.MM - YYYY.MM", "bullets": ["核心课程...", "..."] }
  ]
}
"""

from __future__ import annotations

import json
import os
import sys
import ctypes
import tempfile
from pathlib import Path
from typing import Any

# macOS: 确保 weasyprint 能找到 brew 安装的 pango / cairo 等依赖
# （macOS SIP 会在子进程中剥离 DYLD_* 环境变量，此处 monkeypatch ctypes.util.find_library
#   + 预加载，让 cffi.dlopen 能拿到绝对路径）
if sys.platform == "darwin":
    _BREW_LIB = "/opt/homebrew/lib"
    if os.path.isdir(_BREW_LIB):
        _LIB_MAP = {
            "gobject-2.0": "libgobject-2.0.0.dylib",
            "pango-1.0": "libpango-1.0.0.dylib",
            "pangoft2-1.0": "libpangoft2-1.0.0.dylib",
            "pangocairo-1.0": "libpangocairo-1.0.0.dylib",
            "harfbuzz": "libharfbuzz.0.dylib",
            "fontconfig-1": "libfontconfig.1.dylib",
            "fontconfig": "libfontconfig.1.dylib",
            "cairo-2": "libcairo.2.dylib",
            "cairo": "libcairo.2.dylib",
            "libpango-1.0-0": "libpango-1.0.0.dylib",
            "libpangoft2-1.0-0": "libpangoft2-1.0.0.dylib",
            "libharfbuzz-0": "libharfbuzz.0.dylib",
            "libfontconfig-1": "libfontconfig.1.dylib",
            "libpangocairo-1.0-0": "libpangocairo-1.0.0.dylib",
            "libgobject-2.0-0": "libgobject-2.0.0.dylib",
        }
        # 1) 预加载（让 dlopen 缓存这些库）
        for _fname in set(_LIB_MAP.values()):
            _p = os.path.join(_BREW_LIB, _fname)
            if os.path.exists(_p):
                try:
                    ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass
        # 2) Monkeypatch find_library —— cffi 的 dlopen 用它查路径
        import ctypes.util as _ctu
        _orig_find = _ctu.find_library

        def _patched_find(name):
            mapped = _LIB_MAP.get(name)
            if mapped:
                cand = os.path.join(_BREW_LIB, mapped)
                if os.path.exists(cand):
                    return cand
            return _orig_find(name)

        _ctu.find_library = _patched_find

from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_TEMPLATE = "resume_default_tmpl.html"


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=()),  # 用 |safe 控制
)


def render_html(data: dict[str, Any], template_name: str = DEFAULT_TEMPLATE) -> str:
    """把结构化数据渲染成 HTML 字符串。"""
    tpl = _env.get_template(template_name)
    return tpl.render(**data)


def render_pdf(
    data: dict[str, Any],
    output_path: Path | str | None = None,
    template_name: str = DEFAULT_TEMPLATE,
) -> Path:
    """渲染为 PDF 并返回路径。output_path 为 None 时写临时文件。"""
    from weasyprint import HTML

    html_str = render_html(data, template_name=template_name)

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = Path(tmp.name)
        tmp.close()
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # base_url 指向 templates 目录，保证 <img src="your_photo.png"> 可解析
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(output_path))
    return output_path


def render_pdf_bytes(data: dict[str, Any], template_name: str = DEFAULT_TEMPLATE) -> bytes:
    """直接返回 PDF bytes，方便 Streamlit st.download_button。"""
    from weasyprint import HTML

    html_str = render_html(data, template_name=template_name)
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf()


def render_preview_png(
    data: dict[str, Any],
    template_name: str = DEFAULT_TEMPLATE,
    dpi: int = 110,
) -> tuple[bytes | None, str]:
    """
    生成简历第一页 PNG 预览。三级降级：
      1. PyMuPDF (fitz)  — 纯 Python wheel，无系统依赖，首选
      2. pdf2image      — 需要 poppler/pdftoppm，作为次选
      3. 失败            — 返回 (None, "iframe")，调用方自行展示 PDF iframe

    返回：(png_bytes, backend_name)。backend 可选值：pymupdf / pdf2image / iframe。
    失败时 png_bytes 为 None，调用方应降级展示 PDF。
    """
    pdf_bytes = render_pdf_bytes(data, template_name=template_name)

    # 方案 1：PyMuPDF（首选）
    try:
        import fitz  # type: ignore
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count > 0:
            zoom = dpi / 72.0
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            return pix.tobytes("png"), "pymupdf"
    except Exception:
        pass

    # 方案 2：pdf2image（需 poppler）
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        import io as _io
        images = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=1, last_page=1)
        if images:
            buf = _io.BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue(), "pdf2image"
    except Exception:
        pass

    # 方案 3：降级，交给调用方
    return None, "iframe"


def load_json(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    # 自测：从 data/resume_master_sample.json 渲染
    import sys
    sample = Path(__file__).resolve().parents[2] / "data" / "resume_master_sample.json"
    if not sample.exists():
        print(f"[!] 缺少样本文件: {sample}")
        sys.exit(1)
    out = render_pdf(load_json(sample), output_path="/tmp/resume_renderer_test.pdf")
    print(f"[OK] 已生成: {out}")
