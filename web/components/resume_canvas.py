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
  h1.cv-name{font-size:28px;font-weight:600;letter-spacing:-.01em;
    margin:0 0 6px;text-align:center;color:#1d1d1f;}
  .cv-contact{text-align:center;color:#6e6e73;font-size:13px;margin-bottom:20px;}
  h2.cv-section{font-size:15px;font-weight:600;margin:22px 0 10px;
    padding-bottom:4px;border-bottom:1px solid rgba(29,29,31,0.12);letter-spacing:.02em;
    color:#1d1d1f;}
  .cv-item{position:relative;margin-bottom:10px;}
  .cv-item-head{display:flex;justify-content:space-between;align-items:baseline;
    gap:16px;font-size:13.5px;margin-bottom:4px;color:#1d1d1f;}
  .cv-item-title{font-weight:600;}
  .cv-item-role{font-weight:500;color:#1d1d1f;margin-left:8px;}
  .cv-item-meta{color:#6e6e73;font-size:12px;white-space:nowrap;}
  .cv-skill-row,.cv-bullet-read,.cv-edu-row{font-size:13.5px;line-height:1.55;color:#1d1d1f;}
  .cv-skill-row{margin:3px 0;}
  .cv-skill-label{font-weight:600;margin-right:6px;}
  .cv-edu-row{display:flex;justify-content:space-between;gap:16px;margin:4px 0;}
  .cv-edit-pane{
    margin:8px 0 14px;padding:10px 12px;border-radius:8px;
    background:#f5f5f7;border:1px solid rgba(29,29,31,0.08);
  }
  .cos-canvas-anchor{display:none;}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cos-canvas-anchor){
    background:#ffffff !important;
    border:1px solid rgba(29,29,31,0.08) !important;
    border-radius:6px !important;
    box-shadow:0 1px 3px rgba(0,0,0,0.04),0 12px 32px rgba(0,0,0,0.06) !important;
    max-width:820px !important;
    margin:0 auto 32px auto !important;
    padding:48px 56px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cos-canvas-anchor) .stButton button{
    padding:5px 10px !important;
    min-height:30px !important;
    font-size:12px !important;
    border-radius:6px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cos-canvas-anchor) textarea,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.cos-canvas-anchor) input{
    font-size:13.5px !important;
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
