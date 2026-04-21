"""Resume canvas helpers for the /resume_tailor page.

This module owns only presentational CSS and tiny HTML helpers. The page keeps
all state mutation in resume_tailor.py so Chat patches, undo, validation, and
version saving continue to share the same data path.
"""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st


CANVAS_CSS = """
<style>
  .cos-canvas-wrap{display:flex;justify-content:center;padding:8px 0 32px;}
  .cos-canvas{
    width:100%;max-width:820px;background:#ffffff;
    border:1px solid rgba(29,29,31,0.08);
    border-radius:6px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04),0 12px 32px rgba(0,0,0,0.06);
    padding:48px 56px;color:#1d1d1f;
    font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',sans-serif;
    line-height:1.55;
  }
  .cos-canvas h1.cv-name{font-size:28px;font-weight:600;letter-spacing:-.01em;
    margin:0 0 6px;text-align:center;}
  .cos-canvas .cv-contact{text-align:center;color:#6e6e73;font-size:13px;margin-bottom:20px;}
  .cos-canvas h2.cv-section{font-size:15px;font-weight:600;margin:22px 0 10px;
    padding-bottom:4px;border-bottom:1px solid rgba(29,29,31,0.12);letter-spacing:.02em;}
  .cos-canvas .cv-item{position:relative;margin-bottom:10px;}
  .cos-canvas .cv-item-head{display:flex;justify-content:space-between;align-items:baseline;
    gap:16px;font-size:13.5px;margin-bottom:4px;}
  .cos-canvas .cv-item-title{font-weight:600;}
  .cos-canvas .cv-item-role{font-weight:500;color:#1d1d1f;margin-left:8px;}
  .cos-canvas .cv-item-meta{color:#6e6e73;font-size:12px;white-space:nowrap;}
  .cos-canvas ul.cv-bullets{margin:4px 0 10px;padding-left:20px;}
  .cos-canvas ul.cv-bullets li{font-size:13.5px;margin:3px 0;}
  .cos-canvas .cv-skill-row{font-size:13.5px;margin:3px 0;}
  .cos-canvas .cv-skill-label{font-weight:600;margin-right:6px;}
  .cos-canvas .cv-edu-row{display:flex;justify-content:space-between;gap:16px;
    font-size:13.5px;margin:4px 0;}
  .cos-canvas .cv-edit-pane{
    margin:8px 0 14px;padding:10px 12px;border-radius:8px;
    background:#f5f5f7;border:1px solid rgba(29,29,31,0.08);
  }
  .cos-canvas .cv-inline-actions{display:flex;gap:6px;align-items:center;}
  .cos-canvas .cv-bullet-read{font-size:13.5px;line-height:1.55;margin:2px 0;}
  .cos-canvas .cv-muted{color:#6e6e73;}
  h1.cv-name{font-size:23px;font-weight:600;letter-spacing:-.01em;
    margin:0 0 3px;text-align:center;color:#1d1d1f;line-height:1.18;}
  .cv-contact{text-align:center;color:#6e6e73;font-size:11px;margin-bottom:12px;line-height:1.35;}
  h2.cv-section{font-size:13px;font-weight:600;margin:13px 0 6px;
    padding-bottom:4px;border-bottom:1px solid rgba(29,29,31,0.12);letter-spacing:.02em;
    color:#1d1d1f;}
  .cv-item{position:relative;margin-bottom:4px;}
  .cv-item-head{display:flex;justify-content:space-between;align-items:baseline;
    gap:12px;font-size:12px;margin-bottom:1px;color:#1d1d1f;line-height:1.25;}
  .cv-item-title{font-weight:600;}
  .cv-item-role{font-weight:500;color:#1d1d1f;margin-left:8px;}
  .cv-item-meta{color:#6e6e73;font-size:10.5px;white-space:nowrap;}
  .cv-skill-row,.cv-bullet-read,.cv-edu-row{font-size:12px;line-height:1.35;color:#1d1d1f;}
  .cv-skill-row{margin:1px 0;}
  .cv-skill-label{font-weight:600;margin-right:6px;}
  .cv-edu-row{display:flex;justify-content:space-between;gap:12px;margin:2px 0;}
  .cv-edit-pane{
    margin:6px 0 10px;padding:8px 10px;border-radius:8px;
    background:#f5f5f7;border:1px solid rgba(29,29,31,0.08);
  }
  .cos-canvas-anchor{display:none;}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor){
    background:#ffffff !important;
    border:1px solid rgba(29,29,31,0.08) !important;
    border-radius:6px !important;
    box-shadow:0 1px 3px rgba(0,0,0,0.04),0 12px 32px rgba(0,0,0,0.06) !important;
    box-sizing:border-box !important;
    max-width:820px !important;
    margin:0 auto 32px auto !important;
    padding:26px 34px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) > div > div[data-testid="stVerticalBlock"]{
    width:100% !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) div[data-testid="element-container"]{
    margin-bottom:0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stMarkdown p{
    margin-bottom:0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) div[data-testid="stHorizontalBlock"]{
    gap:0.35rem !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stButton button{
    background:#ffffff !important;
    color:#1d1d1f !important;
    border:1px solid rgba(29,29,31,0.14) !important;
    box-shadow:none !important;
    padding:1px 5px !important;
    min-height:24px !important;
    height:24px !important;
    font-size:11px !important;
    line-height:1 !important;
    border-radius:5px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stButton button:hover,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stButton button:active,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stButton button:focus,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) .stButton button:focus-visible{
    background:#f5f7fb !important;
    color:#1d1d1f !important;
    border-color:rgba(0,113,227,0.28) !important;
    box-shadow:0 0 0 2px rgba(0,113,227,0.10) !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) textarea,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-anchor) input{
    font-size:12px !important;
  }
  .cos-canvas-note{
    max-width:820px;margin:12px auto 24px auto;padding:10px 14px;
    border-left:3px solid #0071e3;border-radius:7px;
    background:#f5f9ff;color:#3a3a3c;font-size:12px;line-height:1.45;
  }
  .cos-canvas-note .muted{display:block;margin-top:4px;color:#6e6e73;}
  .cos-right-title{
    font-size:20px;font-weight:650;letter-spacing:0;color:#1d1d1f;
    margin:0 0 8px 0;line-height:1.25;
  }
  .cos-preview-thumb img{
    max-width:180px !important;
    max-height:240px !important;
    object-fit:contain !important;
    border:1px solid rgba(29,29,31,0.08);
    border-radius:6px;
    background:#ffffff;
  }
</style>
"""


def render_canvas_css() -> None:
    st.markdown(CANVAS_CSS, unsafe_allow_html=True)


def rich_text_html(text: Any) -> str:
    """Escape text while preserving the allowed <b>...</b> inline tag."""
    raw = "" if text is None else str(text)
    parts = re.split(r"(<b>.*?</b>)", raw, flags=re.IGNORECASE | re.DOTALL)
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        match = re.fullmatch(r"<b>(.*?)</b>", part, flags=re.IGNORECASE | re.DOTALL)
        if match:
            out.append(f"<b>{html.escape(match.group(1))}</b>")
        else:
            out.append(html.escape(part))
    return "".join(out)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def render_section(title: str) -> None:
    st.markdown(f'<h2 class="cv-section">{esc(title)}</h2>', unsafe_allow_html=True)


def render_basics_header(basics: dict[str, Any], education: list[dict[str, Any]] | None = None) -> None:
    edu = (education or [{}])[0] if education else {}
    school_major = " ".join(
        x for x in [str(edu.get("school", "") or ""), str(edu.get("major", "") or "")] if x
    )
    contact_parts = [
        basics.get("email"),
        basics.get("phone"),
        basics.get("city"),
        basics.get("target_role"),
        school_major,
    ]
    contact = " · ".join(str(x) for x in contact_parts if x)
    st.markdown(
        f'<h1 class="cv-name">{esc(basics.get("name", ""))}</h1>'
        f'<div class="cv-contact">{esc(contact)}</div>',
        unsafe_allow_html=True,
    )


def render_item_header(company: str, role: str, date: str) -> None:
    st.markdown(
        '<div class="cv-item-head">'
        f'<div><span class="cv-item-title">{esc(company)}</span>'
        f'<span class="cv-item-role">{esc(role)}</span></div>'
        f'<div class="cv-item-meta">{esc(date)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
