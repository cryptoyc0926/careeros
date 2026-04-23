"""Resume canvas helpers for the /resume_tailor page.

Indigo-white canvas system:
  * Design tokens via CSS variables (:root)
  * Frosted sidebar, floating A4 paper, responsive easing
  * Hover-revealed inline actions, typography-led section hierarchy
  * No hard borders; layering through light + spacing

This module owns only presentational CSS and tiny HTML helpers. The page keeps
all state mutation in resume_tailor.py so Chat patches, undo, validation, and
version saving continue to share the same data path.
"""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st


# ────────────────────────────────────────────────────────────
#  Indigo-White Canvas Tokens (CSS variables)
# ────────────────────────────────────────────────────────────
# Only 10 colors · 4 type sizes · 3 radii · 2 shadows · 8pt spacing grid.
# Everything in this file references these — no one-off hex values.

CANVAS_CSS = """
<style>
:root{
  /* Surfaces */
  --cv-bg-page:     #FFFFFF;
  --cv-bg-paper:    #FFFFFF;
  --cv-bg-subtle:   #F7F8FA;
  --cv-bg-hover:    rgba(11,18,32,0.06);
  --cv-bg-sidebar:  rgba(255,255,255,0.86);

  /* Text */
  --cv-fg-primary:   #0B1220;
  --cv-fg-secondary: #6B7280;
  --cv-fg-tertiary:  #9CA3AF;

  /* Accent */
  --cv-accent:       #3B5BFE;
  --cv-accent-soft:  rgba(59,91,254,0.10);
  --cv-accent-text:  #FFFFFF;

  /* Lines (for rare hairlines) */
  --cv-hairline:     rgba(11,18,32,0.08);

  /* Radii */
  --r-sm: 6px;
  --r-md: 10px;
  --r-lg: 14px;

  /* Elevation */
  --shadow-paper:
    0 0 0 1px rgba(11,18,32,0.04),
    0 1px 2px rgba(11,18,32,0.04),
    0 24px 70px -24px rgba(11,18,32,0.18);
  --shadow-lift:
    0 0 0 1px rgba(11,18,32,0.08),
    0 4px 12px rgba(11,18,32,0.10);

  /* Responsive easing */
  --ease-spring: cubic-bezier(0.32,0.72,0,1);
}

/* ─── Reset: strip Streamlit default chrome that fights the design ─── */
body, .stApp{ background: var(--cv-bg-page) !important; }

/* Kill the big top padding so canvas sits 24px from header */
div.block-container,
[data-testid="stMainBlockContainer"]{
  padding-top: 24px !important;
  padding-bottom: 48px !important;
  max-width: 1480px !important;
}
[data-testid="stMainBlockContainer"] hr{
  margin: 10px 0 14px 0 !important;
  border-color: var(--cv-hairline) !important;
}

/* Hide style tags that Streamlit surfaces as empty element-containers */
div[data-testid="element-container"]:has(> style){
  display:none !important; height:0 !important; margin:0 !important; padding:0 !important;
}

/* ─── Kill Streamlit / baseweb dark active/focus states ─── */
button:focus, button:focus-visible, button:active,
button:focus:not(:active), button[aria-pressed="true"],
[data-testid="baseButton-primary"]:focus,
[data-testid="baseButton-secondary"]:focus,
[data-testid="baseButton-primary"]:active,
[data-testid="baseButton-secondary"]:active{
  outline: none !important;
  box-shadow: 0 0 0 3px var(--cv-accent-soft) !important;
  color: inherit !important;
}
button[kind="primary"]:focus, button[kind="primary"]:active,
button[kind="primary"]:focus:not(:active){
  background: var(--cv-accent) !important;
  color: var(--cv-accent-text) !important;
  border: none !important;
}
button[kind="secondary"]:focus, button[kind="secondary"]:active,
button[kind="secondary"]:focus:not(:active){
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
  border: 1px solid var(--cv-hairline) !important;
}
/* Expander / tab / popover triggers */
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] details[open] > summary{
  background: transparent !important;
  color: var(--cv-fg-primary) !important;
  outline: none !important;
  box-shadow: none !important;
}
[role="tab"]:focus, [role="tab"]:active{
  background: transparent !important;
  color: var(--cv-fg-primary) !important;
  outline: none !important;
  box-shadow: none !important;
}
/* Text inputs: kill red focus border */
input:focus, textarea:focus, select:focus{
  outline: none !important;
  border-color: var(--cv-accent) !important;
  box-shadow: 0 0 0 3px var(--cv-accent-soft) !important;
}
/* Download button */
[data-testid="stDownloadButton"] button:focus,
[data-testid="stDownloadButton"] button:active{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
  border: 1px solid var(--cv-hairline) !important;
  outline: none !important;
}

/* Global spring transitions on buttons/links */
button, a, [role="tab"]{
  transition:
    background-color .18s var(--ease-spring),
    box-shadow .20s var(--ease-spring),
    transform .16s var(--ease-spring),
    opacity .16s var(--ease-spring),
    color .16s var(--ease-spring) !important;
}
button:active{ transform: scale(0.97); }

/* ─── Streamlit sidebar (Career OS nav) → frosted glass ─── */
[data-testid="stSidebar"]{
  background: var(--cv-bg-sidebar) !important;
  backdrop-filter: saturate(1.6) blur(22px) !important;
  -webkit-backdrop-filter: saturate(1.6) blur(22px) !important;
  border-right: 1px solid var(--cv-hairline) !important;
}

/* ─── Left rail inside the page (JD + chat) ─── */
.cos-group-label{
  display:block;
  font-size:11px;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.08em;
  color:var(--cv-fg-secondary);
  margin:20px 0 8px 0;
}
.cos-group-label:first-child{ margin-top:0; }

.cos-left-rule{
  display:block;
  border-top:1px solid var(--cv-hairline);
  margin:20px 0;
}

/* Gap-only divider: layering via whitespace */
.cos-left-gap{ display:block; height:20px; }
.cv-item-gap{ display:block; height:18px; }

/* Text areas: remove harsh borders, reveal on hover */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input{
  background: var(--cv-bg-subtle) !important;
  border: 1px solid transparent !important;
  border-radius: var(--r-md) !important;
  color: var(--cv-fg-primary) !important;
  transition: background-color .15s var(--ease-spring), border-color .15s var(--ease-spring) !important;
}
[data-testid="stTextArea"] textarea:hover,
[data-testid="stTextInput"] input:hover{
  background: var(--cv-bg-hover) !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus{
  background: var(--cv-bg-paper) !important;
  border-color: var(--cv-accent) !important;
  box-shadow: 0 0 0 3px var(--cv-accent-soft) !important;
}
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder{
  color: var(--cv-fg-tertiary) !important;
}

/* Primary button = solid accent */
button[kind="primary"]{
  background: var(--cv-accent) !important;
  color: var(--cv-accent-text) !important;
  border: none !important;
  border-radius: var(--r-sm) !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
button[kind="primary"]:hover{
  background: #2947E6 !important;
  transform: translateY(-0.5px);
}
button[kind="primary"]:disabled{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-tertiary) !important;
}

/* Secondary button in left rail = subtle ghost */
button[kind="secondary"]{
  background: transparent !important;
  color: var(--cv-fg-primary) !important;
  border: 1px solid var(--cv-hairline) !important;
  border-radius: var(--r-sm) !important;
  box-shadow: none !important;
  font-weight: 500 !important;
}
button[kind="secondary"]:hover{
  background: var(--cv-bg-hover) !important;
  border-color: var(--cv-hairline) !important;
}

/* ─── A4 Paper (canvas) ─── */
/* Anchor targets the st.container(border=True) that hosts the canvas paper. */
div[data-testid="element-container"]:has(.cos-canvas-paper-anchor){
  display:none !important; height:0 !important; margin:0 !important; padding:0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-paper-anchor){
  background: var(--cv-bg-paper) !important;
  max-width: 860px !important;
  margin: 16px auto 48px auto !important;
  padding: 56px 64px 64px !important;
  border-radius: var(--r-lg) !important;
  border: none !important;
  box-shadow: var(--shadow-paper) !important;
  box-sizing: border-box !important;
}
/* Inner wrapper: remove default border */
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-paper-anchor) > div{
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] .cos-canvas-paper-anchor) div[data-testid="element-container"]{
  margin-bottom: 0 !important;
}

/* ─── Canvas typography: left-aligned, weight-driven ─── */
h1.cv-name{
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.18;
  margin: 0 0 4px 0;
  color: var(--cv-fg-primary);
  text-align: left;
}
.cv-contact{
  font-size: 12.5px;
  color: var(--cv-fg-secondary);
  margin: 0 0 20px 0;
  line-height: 1.4;
  text-align: left;
}
h2.cv-section{
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--cv-fg-primary);
  margin: 22px 0 8px 0;
  padding: 0;
  border: none;
}
.cv-item-head{
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px;
  font-size: 13px;
  margin: 6px 0 2px 0;
  color: var(--cv-fg-primary);
  line-height: 1.3;
}
.cv-item-title{ font-weight: 600; }
.cv-item-role{ font-weight: 400; color: var(--cv-fg-primary); margin-left: 8px; }
.cv-item-meta{
  color: var(--cv-fg-secondary);
  font-size: 11.5px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.cv-bullet-read{
  font-size: 13px;
  line-height: 1.5;
  color: var(--cv-fg-primary);
  margin: 2px 0;
}
ul.cv-bullets{
  margin: 0;
  padding-left: 18px;
  list-style: none;
}
ul.cv-bullets li{
  font-size: 13px;
  line-height: 1.5;
  margin: 3px 0;
  color: var(--cv-fg-primary);
  position: relative;
}
ul.cv-bullets li::before{
  content: "";
  position: absolute;
  left: -12px; top: 0.56em;
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--cv-fg-tertiary);
}
.cv-skill-row{
  font-size: 13px;
  line-height: 1.5;
  color: var(--cv-fg-primary);
  margin: 3px 0;
}
.cv-skill-label{ font-weight: 600; margin-right: 6px; }
.cv-edu-row{
  display: flex; justify-content: space-between; gap: 12px;
  font-size: 13px;
  margin: 4px 0 2px 0;
  color: var(--cv-fg-primary);
}

/* Inline edit pane (subtle gray card, not harsh) */
.cv-edit-pane{
  margin: 6px 0 10px 0;
  padding: 8px 10px;
  border-radius: var(--r-md);
  background: var(--cv-bg-subtle);
  border: 1px solid var(--cv-hairline);
}

/* ─── Bullet row: hover reveals actions ─── */
/* Hide the inline anchor spans */
div[data-testid="element-container"]:has(.cos-bullet-actions-anchor),
div[data-testid="element-container"]:has(.cos-section-ai-anchor){
  display:none !important; height:0 !important; margin:0 !important; padding:0 !important;
}

/* Default: action buttons in bullet rows are dim (opacity 0 until row hover) */
div[data-testid="stHorizontalBlock"]:has(.cos-bullet-actions-anchor) div[data-testid="column"] button{
  opacity: 0;
  pointer-events: none;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--cv-fg-secondary) !important;
  min-width: 0 !important;
  height: 26px !important;
  min-height: 26px !important;
  padding: 0 6px !important;
  border-radius: var(--r-sm) !important;
  font-size: 12px !important;
  line-height: 1 !important;
  font-weight: 500 !important;
}
/* First (text) column never has an action button — rule is scoped via :has(button). */
div[data-testid="stHorizontalBlock"]:has(.cos-bullet-actions-anchor):hover div[data-testid="column"] button,
div[data-testid="stHorizontalBlock"]:has(.cos-bullet-actions-anchor):focus-within div[data-testid="column"] button{
  opacity: 1;
  pointer-events: auto;
}
div[data-testid="stHorizontalBlock"]:has(.cos-bullet-actions-anchor) div[data-testid="column"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}
div[data-testid="stHorizontalBlock"]:has(.cos-bullet-actions-anchor) div[data-testid="column"] button:disabled{
  color: var(--cv-fg-tertiary) !important;
}

/* Project/Internship item head: hover reveals "改信息" */
div[data-testid="stHorizontalBlock"]:has(.cv-item-head) div[data-testid="column"] button{
  opacity: 0; pointer-events: none;
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: var(--cv-fg-secondary) !important;
  height: 24px !important; min-height: 24px !important;
  padding: 0 8px !important; font-size: 11.5px !important; font-weight: 500 !important;
  border-radius: var(--r-sm) !important;
}
div[data-testid="stHorizontalBlock"]:has(.cv-item-head):hover div[data-testid="column"] button,
div[data-testid="stHorizontalBlock"]:has(.cv-item-head):focus-within div[data-testid="column"] button{
  opacity: 1; pointer-events: auto;
}
div[data-testid="stHorizontalBlock"]:has(.cv-item-head) div[data-testid="column"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}

/* AI 重写本段 = soft pill on section title row, hover-revealed */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="element-container"] .cos-section-ai-anchor){
  /* keep rule focus */
}
div[data-testid="stHorizontalBlock"]:has(h2.cv-section) div[data-testid="column"] button{
  opacity: 0; pointer-events: none;
  min-width: 92px !important;
  height: 26px !important; min-height: 26px !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  background: var(--cv-bg-subtle) !important;
  color: var(--cv-fg-secondary) !important;
  border: none !important; box-shadow: none !important;
  font-size: 11.5px !important; font-weight: 500 !important;
}
div[data-testid="stHorizontalBlock"]:has(h2.cv-section):hover div[data-testid="column"] button,
div[data-testid="stHorizontalBlock"]:has(h2.cv-section):focus-within div[data-testid="column"] button{
  opacity: 1; pointer-events: auto;
}
div[data-testid="stHorizontalBlock"]:has(h2.cv-section) div[data-testid="column"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}

/* Profile block: same hover pattern */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-bullet-read) div[data-testid="column"] button{
  opacity: 0; pointer-events: none;
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: var(--cv-fg-secondary) !important;
  height: 24px !important; min-height: 24px !important;
  padding: 0 8px !important; font-size: 11.5px !important;
  border-radius: var(--r-sm) !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-bullet-read):hover div[data-testid="column"] button,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-bullet-read):focus-within div[data-testid="column"] button{
  opacity: 1; pointer-events: auto;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-bullet-read) div[data-testid="column"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}
/* Skills rows: same */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-skill-row) div[data-testid="column"] button{
  opacity: 0; pointer-events: none;
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: var(--cv-fg-secondary) !important;
  height: 24px !important; min-height: 24px !important;
  padding: 0 8px !important; font-size: 11.5px !important;
  border-radius: var(--r-sm) !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-skill-row):hover div[data-testid="column"] button,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-skill-row):focus-within div[data-testid="column"] button{
  opacity: 1; pointer-events: auto;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > div > div.cv-skill-row) div[data-testid="column"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}

/* Popover trigger ("编辑基本信息") = small neutral pill */
[data-testid="stPopover"] button{
  height: 24px !important; min-height: 24px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  background: var(--cv-bg-subtle) !important;
  color: var(--cv-fg-secondary) !important;
  border: none !important; box-shadow: none !important;
  font-size: 11.5px !important; font-weight: 500 !important;
}
[data-testid="stPopover"] button:hover{
  background: var(--cv-bg-hover) !important;
  color: var(--cv-fg-primary) !important;
}

/* ─── Chat bubbles ─── */
.cos-chat-msg{
  padding: 8px 12px;
  border-radius: 16px;
  margin: 4px 0;
  line-height: 1.5;
  font-size: 13px;
  max-width: 92%;
  word-wrap: break-word;
}
.cos-chat-user{
  background: var(--cv-accent);
  color: var(--cv-accent-text);
  border-bottom-right-radius: 4px;
  margin-left: auto;
}
.cos-chat-bot{
  background: var(--cv-bg-subtle);
  color: var(--cv-fg-primary);
  border-bottom-left-radius: 4px;
  margin-right: auto;
}
.cos-chat-role{
  display: none;
}
.cos-chat-empty{
  display: block;
  padding: 40px 16px;
  color: var(--cv-fg-tertiary);
  font-size: 12.5px;
  text-align: center;
  line-height: 1.6;
}

/* Chat input */
[data-testid="stChatInput"]{
  margin-top: 8px;
}
[data-testid="stChatInput"] textarea{
  background: var(--cv-bg-subtle) !important;
  border: 1px solid transparent !important;
  border-radius: 20px !important;
  color: var(--cv-fg-primary) !important;
  padding: 10px 14px !important;
  font-size: 13px !important;
}
[data-testid="stChatInput"] textarea:focus{
  background: var(--cv-bg-paper) !important;
  border-color: var(--cv-accent) !important;
  box-shadow: 0 0 0 3px var(--cv-accent-soft) !important;
}
[data-testid="stChatInput"] textarea::placeholder{
  color: var(--cv-fg-tertiary) !important;
}

/* Undo badge */
.cos-undo-badge{
  display: inline-block;
  padding: 2px 10px;
  background: var(--cv-accent-soft);
  color: var(--cv-accent);
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  line-height: 1.5;
}

/* Canvas error (subtle banner) */
.cos-canvas-error{
  max-width: 820px; margin: 0 auto 10px auto;
  padding: 10px 14px;
  border-left: 3px solid #d92d20;
  border-radius: var(--r-md);
  background: #fff2f1;
  color: #3a3a3c;
  font-size: 12.5px; line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

/* Preview thumbnail */
.cos-preview-thumb img{
  max-width: 220px !important;
  max-height: 300px !important;
  object-fit: contain !important;
  border: 1px solid var(--cv-hairline) !important;
  border-radius: var(--r-sm) !important;
  background: var(--cv-bg-paper) !important;
}
.cos-empty-preview{
  display: flex;
  height: 320px;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--cv-hairline);
  border-radius: var(--r-md);
  background: var(--cv-bg-subtle);
  color: var(--cv-fg-tertiary);
  font-size: 12.5px;
}

/* Top action strip (保存/历史/深度评估) */
.cos-top-actions{
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 0 0 8px 0;
}

/* st.alert boxes: soften to match the canvas palette */
div[data-testid="stAlert"]{
  border-radius: var(--r-md) !important;
  border: none !important;
  box-shadow: 0 0 0 1px var(--cv-hairline) inset !important;
}

/* Remove default h5 (###### AI 对话修改) noise */
.stMarkdown h5{
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--cv-fg-secondary) !important;
  margin: 20px 0 8px 0 !important;
}

/* Dialog polish */
[data-testid="stDialog"] > div{
  border-radius: var(--r-lg) !important;
  background: var(--cv-bg-paper) !important;
}

/* Expander chevron quieter */
[data-testid="stExpander"] summary{
  font-size: 12.5px !important;
  color: var(--cv-fg-secondary) !important;
  font-weight: 500 !important;
}
[data-testid="stExpander"] summary:hover{
  color: var(--cv-fg-primary) !important;
}

/* Hide the bulky download_button default border, go flat */
[data-testid="stDownloadButton"] button{
  border-radius: var(--r-sm) !important;
  font-weight: 500 !important;
}

/* Caption tone-down */
.stCaption, [data-testid="stCaptionContainer"]{
  color: var(--cv-fg-secondary) !important;
  font-size: 11.5px !important;
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


def render_basics_header(
    basics: dict[str, Any],
    education: list[dict[str, Any]] | None = None,
) -> None:
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


def group_label(text: str) -> None:
    """12px uppercase group header for the left rail."""
    st.markdown(f'<span class="cos-group-label">{esc(text)}</span>', unsafe_allow_html=True)
