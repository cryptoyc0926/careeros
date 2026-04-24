"""
简历在线编辑 & JD 定制
~~~~~~~~~~~~~~~~~~~~~~~~~~~
三栏交互：
  左：JD 输入 / 历史版本
  中：分段编辑器（profile / projects / internships / skills）
  右：实时 PDF 预览 + 下载

数据流：
  resume_master → tailor(jd) → content_json(session) → renderer → PDF bytes
"""

from __future__ import annotations

import hashlib
import difflib
import html
import json
import sqlite3
from pathlib import Path

import streamlit as st

from config import settings
from services import resume_renderer, resume_tailor
from services.action_status import format_action_status_caption, record_action_status
from services.ai_engine import AIError
from services.resume_chat_session import (
    append_chat_message,
    clear_pending_patch,
    clear_resume_chat_state,
    ensure_resume_chat_state,
    replace_chat_history,
    set_pending_patch,
)
from components import resume_canvas
from components.ui import section_title, divider, score_hero_card, alert_success, alert_info, alert_warning, alert_danger

DB_PATH = settings.db_full_path

# Apple design system (tokens + canvas CSS + global reset)
resume_canvas.render_canvas_css()
st.markdown(
    """
    <style>
    section[data-testid="stMain"] > [data-testid="stMainBlockContainer"],
    section[data-testid="stMain"] .block-container,
    div[data-testid="stMainBlockContainer"]{
      max-width: none !important;
      width: 100% !important;
      padding: 1.5rem 2rem 3rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if not settings.has_anthropic_key:
    alert_danger("Claude API Key 未配置，请前往 **设置** 页面。")
    st.stop()


def _db_columns(table: str) -> set[str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r[1] for r in rows}
    finally:
        conn.close()


def _has_db_column(table: str, column: str) -> bool:
    return column in _db_columns(table)


# ── 读 master ────────────────────────────────────────────
def load_master() -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM resume_master ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "id": row["id"],
        "updated_at": row["updated_at"],
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
        "original_docx_blob": row["original_docx_blob"] if "original_docx_blob" in keys else None,
        "original_docx_filename": row["original_docx_filename"] if "original_docx_filename" in keys else None,
    }


def demo_master_fallback() -> dict:
    """公开 Demo 的兜底主简历：只在云端样例数据为空/占位符时使用。"""
    return {
        "id": 0,
        "updated_at": "demo-fallback",
        "basics": {
            "name": "演示用户",
            "phone": "138-0000-0000",
            "email": "demo@example.com",
            "target_role": "AI 增长运营",
            "city": "杭州",
            "availability": "下周到岗",
            "photo": "",
        },
        "profile": {
            "pool": [
                {
                    "id": "growth_ai",
                    "tags": ["增长", "AI", "运营"],
                    "text": (
                        "统计科班出身，擅长把数据变成增长动作。曾从 0 搭建 AI Trading 社区，"
                        "实现 9,000+ X 粉丝与 1,300+ Telegram 订阅，完成 20+ 次商业合作；"
                        "3 段运营实习覆盖增长、内容与数据分析。"
                    ),
                }
            ],
            "default": "growth_ai",
        },
        "projects": [
            {
                "company": "AI Trading 社区搭建",
                "role": "用户增长运营",
                "date": "2024.03 - 至今",
                "bullets": [
                    "从 0 搭建 X 与 Telegram 内容矩阵，在零投放预算下增长至 9,000+ 粉丝与 1,300+ 订阅。",
                    "设计热点监测、信号筛选、结构化分析、分发输出流程，稳定支撑每周 15+ 条内容产出。",
                    "围绕用户关注点做内容测试与社群运营，沉淀可复用的 AI 内容生产 SOP。",
                ],
            },
            {
                "company": "CareerOS 求职系统",
                "role": "产品与自动化实践",
                "date": "2025.10 - 至今",
                "bullets": [
                    "搭建岗位池、JD 解析与简历定制工作流，聚焦当前求职主线。",
                    "用 SQLite 管理岗位与投递数据，结合大模型完成 JD 匹配、简历改写与评估。",
                ],
            },
        ],
        "internships": [
            {
                "company": "Fancy Tech",
                "role": "海外产品运营实习生",
                "date": "2024.06 - 2024.09",
                "bullets": [
                    "搭建 TikTok/Instagram 内容矩阵，建立 AI 内容生产、自动化编辑、多平台分发 SOP。",
                    "拆解 PhotoRoom、Pebblely 等竞品链路，提炼高转化场景并输出产品优化建议。",
                ],
            },
            {
                "company": "杭银消费金融股份有限公司",
                "role": "数据运营实习生",
                "date": "2023.06 - 2023.10",
                "bullets": [
                    "参与用户分层、活动复盘与指标看板维护，支持运营策略迭代。",
                    "整理业务数据与活动结果，输出周报和专项分析材料。",
                ],
            },
        ],
        "skills": [
            {"label": "数据分析", "text": "Python / SQL / Excel / 指标拆解 / A/B 测试"},
            {"label": "增长运营", "text": "内容矩阵搭建 / 社群运营 / 用户转化 / SOP 沉淀"},
            {"label": "AI 工具", "text": "Prompt Engineering / 自动化工作流 / LLM 应用原型"},
        ],
        "education": [
            {
                "school": "示例大学",
                "major": "示例专业",
                "date": "2022.09 - 2026.07",
                "bullets": ["核心课程：统计学、计量经济学、Python 数据分析、数据库原理。"],
            }
        ],
    }


def master_needs_demo_fallback(master: dict) -> bool:
    def _bad_text(value: object) -> bool:
        text = str(value or "").strip()
        compact = text.replace("*", "").replace("-", "").replace("—", "").strip()
        return not compact or text.startswith("****")

    basics = master.get("basics", {})
    if _bad_text(basics.get("name")) or str(basics.get("name", "")).startswith("你的"):
        return True
    for section in ("projects", "internships"):
        items = master.get(section) or []
        if not items:
            return True
        for item in items:
            if _bad_text(item.get("company")) or _bad_text(item.get("role")):
                return True
    return False


def flatten_master_for_render(master: dict) -> dict:
    """把 profile pool 折叠成默认文本，得到 renderer 直接可用的扁平结构。"""
    profile = master["profile"]
    if isinstance(profile, dict) and "pool" in profile:
        default_id = profile.get("default")
        text = next(
            (p["text"] for p in profile["pool"] if p["id"] == default_id),
            profile["pool"][0]["text"],
        )
    else:
        text = profile
    return {
        "basics": master["basics"],
        "profile": text,
        "projects": master["projects"],
        "internships": master["internships"],
        "skills": master["skills"],
        "education": master["education"],
    }


master = load_master()
if not master:
    alert_info("主简历还没创建。先填写基本信息和经历，再回来使用定制功能。")
    _btn_col_l, _btn_col_m, _btn_col_r = st.columns([1, 2, 1])
    with _btn_col_m:
        if st.button("去创建主简历 →", type="primary", use_container_width=True, key="rt_goto_master"):
            st.switch_page("pages/master_resume.py")
    st.stop()
demo_fallback_active = False
if settings.demo_mode and master_needs_demo_fallback(master):
    master = demo_master_fallback()
    demo_fallback_active = True


# ── Session state ────────────────────────────────────────
master_signature = f"{master.get('id')}:{master.get('updated_at', '')}"
if (
    st.session_state.get("_tailor_master_signature") != master_signature
    or
    "tailor_data" not in st.session_state
    or (demo_fallback_active and master_needs_demo_fallback(st.session_state.tailor_data))
):
    st.session_state.tailor_data = flatten_master_for_render(master)
    st.session_state.tailor_meta = {}
    st.session_state.tailor_jd = ""
    st.session_state["_tailor_preview_key"] = None
    st.session_state["_tailor_preview_pdf"] = None
    st.session_state["_tailor_preview_png"] = None
    st.session_state["_tailor_preview_backend"] = None
    st.session_state["_tailor_preview_error"] = None
    st.session_state["_tailor_master_signature"] = master_signature
if "tailor_meta" not in st.session_state:
    st.session_state.tailor_meta = {}
if "tailor_jd" not in st.session_state:
    st.session_state.tailor_jd = ""
ensure_resume_chat_state(st.session_state)
if "tailor_undo_stack" not in st.session_state:
    st.session_state.tailor_undo_stack = []

ENABLE_CHAT_TAILOR = settings.enable_chat_tailor


# ── 撤销栈工具 ────────────────────────────────────────────
import copy as _copy_tailor  # noqa: E402  — 避免顶部再加一个 import copy
_UNDO_LIMIT = 10


def _push_undo_snapshot(label: str = "") -> None:
    """把当前 tailor_data 深拷贝入栈（用于撤销）。"""
    st.session_state.tailor_undo_stack.append(
        {"label": label, "data": _copy_tailor.deepcopy(st.session_state.tailor_data)}
    )
    if len(st.session_state.tailor_undo_stack) > _UNDO_LIMIT:
        st.session_state.tailor_undo_stack = st.session_state.tailor_undo_stack[-_UNDO_LIMIT:]


def _pop_undo() -> str | None:
    if not st.session_state.tailor_undo_stack:
        return None
    snap = st.session_state.tailor_undo_stack.pop()
    st.session_state.tailor_data = snap["data"]
    return snap.get("label") or "上一步"


def _chat_transcript_payload() -> str:
    chat = ensure_resume_chat_state(st.session_state)
    payload = {
        "messages": st.session_state.get("rt_chat_history", []) or chat.get("messages", []),
        "pending": None,
    }
    return json.dumps(payload, ensure_ascii=False)


def _restore_chat_transcript(raw: str | None) -> None:
    if not raw:
        clear_resume_chat_state(st.session_state)
        return
    try:
        parsed = json.loads(raw)
    except Exception:
        clear_resume_chat_state(st.session_state)
        return
    if isinstance(parsed, list):
        replace_chat_history(st.session_state, parsed)
        clear_pending_patch(st.session_state)
    elif isinstance(parsed, dict):
        replace_chat_history(st.session_state, parsed.get("messages", []) or [])
        clear_pending_patch(st.session_state)
    else:
        clear_resume_chat_state(st.session_state)


def _clear_tailor_preview_cache() -> None:
    st.session_state.pop("_tailor_preview_key", None)
    st.session_state.pop("_tailor_preview_pdf", None)
    st.session_state.pop("_tailor_preview_png", None)
    st.session_state.pop("_tailor_preview_backend", None)
    st.session_state.pop("_tailor_preview_error", None)


def _sync_bound_widget(key: str, current_value: object) -> str:
    current = "" if current_value is None else str(current_value)
    source_key = f"_tailor_widget_source::{key}"
    previous_source = st.session_state.get(source_key)
    widget_value = st.session_state.get(key)

    if key not in st.session_state:
        st.session_state[key] = current
    elif previous_source != current and widget_value == previous_source:
        st.session_state[key] = current
    return current


def _bound_text_input(label: str, current_value: object, key: str, **kwargs) -> str:
    current = _sync_bound_widget(key, current_value)
    value = st.text_input(label, key=key, **kwargs)
    if value != current:
        _clear_tailor_preview_cache()
    st.session_state[f"_tailor_widget_source::{key}"] = value
    return value


def _bound_text_area(label: str, current_value: object, key: str, **kwargs) -> str:
    current = _sync_bound_widget(key, current_value)
    value = st.text_area(label, key=key, **kwargs)
    if value != current:
        _clear_tailor_preview_cache()
    st.session_state[f"_tailor_widget_source::{key}"] = value
    return value


# ── Chat 面板（Phase 1 · 全宽折叠区，置于三栏之上）────────
from services import resume_chat as _resume_chat_service  # noqa: E402

from services import resume_patch as _resume_patch_mod  # noqa: E402


def _set_canvas_error(message: str) -> None:
    st.session_state["_tailor_canvas_error"] = message


def _clear_canvas_error() -> None:
    st.session_state.pop("_tailor_canvas_error", None)


def _clear_tailor_validation_state() -> None:
    for key in (
        "tailor_validation_error",
        "tailor_validation_draft",
        "tailor_validation_raw",
        "tailor_validation_previous",
        "tailor_validation_previous_meta",
    ):
        st.session_state.pop(key, None)


def _friendly_tailor_error(exc: Exception) -> str:
    raw = str(exc)
    raw_lower = raw.lower()
    if isinstance(exc, json.JSONDecodeError) or "json 解析失败" in raw_lower or "json解析失败" in raw_lower:
        return "AI 返回格式异常，请稍后重试"
    if isinstance(exc, TimeoutError) or "timeout" in raw_lower or "timed out" in raw_lower or "超时" in raw:
        return "AI 服务响应超时，请稍后重试"
    if isinstance(exc, AIError):
        return "AI 服务暂不可用，请稍后重试"
    return "生成失败，请稍后重试"


def _normalize_tailor_target_role(data: dict, meta: dict | None = None) -> None:
    meta = meta or {}
    basics = data.setdefault("basics", {})
    master_basics = master.get("basics") or {}
    current_role = (basics.get("target_role") or basics.get("target_position") or "").strip()
    master_role = (master_basics.get("target_role") or master_basics.get("target_position") or "").strip()
    jd_intent = meta.get("jd_intent") if isinstance(meta.get("jd_intent"), dict) else {}
    inferred_role = (
        meta.get("target_position")
        or meta.get("target_role")
        or jd_intent.get("target_position")
        or jd_intent.get("target_role")
    )
    inferred_role = str(inferred_role).strip() if inferred_role else ""
    if inferred_role and (not current_role or current_role == master_role):
        basics["target_role"] = inferred_role
    elif current_role:
        basics["target_role"] = current_role
    if basics.get("target_role") and not meta.get("target_position"):
        meta["target_position"] = basics["target_role"]


def _apply_validation_draft(error, jd_text: str) -> dict | None:
    report = error.report.as_dict()
    st.session_state.tailor_validation_error = report
    st.session_state.tailor_validation_raw = error.raw
    st.session_state.tailor_jd = jd_text
    if not error.draft:
        st.session_state.tailor_validation_draft = None
        return None

    draft = _copy_tailor.deepcopy(error.draft)
    meta = draft.pop("_meta", {}) or {}
    meta["validation"] = report
    meta["validation_blocked"] = True
    meta["change_notes"] = meta.get("change_notes") or "草稿已渲染未保存"
    _normalize_tailor_target_role(draft, meta)

    st.session_state.tailor_validation_previous = _copy_tailor.deepcopy(st.session_state.tailor_data)
    st.session_state.tailor_validation_previous_meta = _copy_tailor.deepcopy(st.session_state.tailor_meta)
    _push_undo_snapshot(label="校验失败前版本")
    st.session_state.tailor_data = draft
    st.session_state.tailor_meta = meta
    st.session_state.tailor_validation_draft = _copy_tailor.deepcopy(draft)
    _clear_tailor_preview_cache()
    _clear_canvas_error()
    return draft


def _format_patch_errors(errors: list[str]) -> str:
    return "Patch 应用失败：\n" + "\n".join(f"- {e}" for e in errors)


def _apply_resume_patch(patch: list[dict], label: str, *, validate: bool = True) -> bool:
    """Apply manual/chat edits through the same patch + validation + undo path."""
    new_data, errors = _resume_patch_mod.apply_patch(st.session_state.tailor_data, patch)
    if errors:
        _set_canvas_error(_format_patch_errors(errors))
        return False
    if not validate:
        _push_undo_snapshot(label=label)
        st.session_state.tailor_data = new_data
        _clear_tailor_preview_cache()
        _clear_canvas_error()
        return True
    from services.resume_validator import validate_tailored
    current_report = None
    try:
        current_report = validate_tailored(
            st.session_state.tailor_data,
            st.session_state.tailor_data,
            None,
        )
        report = validate_tailored(st.session_state.tailor_data, new_data, None)
    except Exception:
        report = None

    def _issue_value(issue, field: str) -> str:
        if isinstance(issue, dict):
            return str(issue.get(field, ""))
        return str(getattr(issue, field, ""))

    def _issue_fingerprint(issue) -> tuple[str, str, str, str, str]:
        return (
            _issue_value(issue, "rule"),
            _issue_value(issue, "location"),
            _issue_value(issue, "message"),
            _issue_value(issue, "expected"),
            _issue_value(issue, "actual"),
        )

    baseline_errors = {
        _issue_fingerprint(e)
        for e in (current_report.hard_errors if current_report else [])
    }
    new_hard_errors = [
        e
        for e in (report.hard_errors if report else [])
        if _issue_fingerprint(e) not in baseline_errors
    ]

    if new_hard_errors:
        _set_canvas_error(
            f"硬规则校验失败（新增 {len(new_hard_errors)} 条），拒绝应用：\n"
            + "\n".join(
                f"- [{_issue_value(e, 'rule')}] {_issue_value(e, 'location')}: {_issue_value(e, 'message')}"
                for e in new_hard_errors[:5]
            )
        )
        return False
    _push_undo_snapshot(label=label)
    st.session_state.tailor_data = new_data
    _clear_tailor_preview_cache()
    _clear_canvas_error()
    return True


def _render_patch_diff(patch: list[dict], tailor_data: dict) -> None:
    """把 pending_patch 渲染成字符级 old/new 对比。"""
    st.markdown(
        """
        <style>
        .cos-diff-box{border:1px solid rgba(29,29,31,0.08);border-radius:10px;
          background:#ffffff;margin:8px 0 14px 0;overflow:hidden;}
        .cos-diff-path{padding:8px 12px;background:#f5f5f7;color:#6e6e73;
          font-size:12px;border-bottom:1px solid rgba(29,29,31,0.06);}
        .cos-diff-line{display:flex;gap:10px;padding:10px 12px;white-space:pre-wrap;
          line-height:1.55;font-family:"SF Mono",ui-monospace,Menlo,monospace;
          font-size:13px;color:#1d1d1f;}
        .cos-diff-line + .cos-diff-line{border-top:1px solid rgba(29,29,31,0.06);}
        .cos-diff-prefix{width:16px;flex:0 0 16px;font-weight:700;}
        .cos-diff-minus{color:#c42323;}
        .cos-diff-plus{color:#18794e;}
        .cos-diff-del{background:#ffe8e8;color:#9f1c1c;text-decoration:line-through;}
        .cos-diff-add{background:#dcfce7;color:#11643a;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _char_diff_html(old_text: str, new_text: str) -> tuple[str, str]:
        old_parts: list[str] = []
        new_parts: list[str] = []
        for token in difflib.ndiff(list(old_text), list(new_text)):
            tag = token[:1]
            char = html.escape(token[2:])
            if tag == " ":
                old_parts.append(char)
                new_parts.append(char)
            elif tag == "-":
                old_parts.append(f'<span class="cos-diff-del">{char}</span>')
            elif tag == "+":
                new_parts.append(f'<span class="cos-diff-add">{char}</span>')
        return "".join(old_parts), "".join(new_parts)

    for i, p in enumerate(patch):
        path = p.get("path", "")
        new_val = p.get("value", "")
        try:
            old_val = _resume_patch_mod.get_by_path(tailor_data, path)
        except Exception:
            old_val = "(不存在)"
        old_html, new_html = _char_diff_html(str(old_val), str(new_val))
        st.markdown(
            f'''
            <div class="cos-diff-box">
              <div class="cos-diff-path">#{i + 1} · {html.escape(path)}</div>
              <div class="cos-diff-line"><span class="cos-diff-prefix cos-diff-minus">-</span><span>{old_html}</span></div>
              <div class="cos-diff-line"><span class="cos-diff-prefix cos-diff-plus">+</span><span>{new_html}</span></div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


def _render_chat_panel() -> None:
    """Chat 面板：消息流 + pending patch diff + 输入框 + 撤销/清空。"""
    chat = ensure_resume_chat_state(st.session_state)
    history = st.session_state.rt_chat_history
    top_c1, top_c2 = st.columns([1, 1])
    with top_c1:
        undo_count = len(st.session_state.tailor_undo_stack)
        if undo_count:
            st.markdown(
                f'<span class="cos-undo-badge">可撤销 {undo_count} 步</span>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("尚无修改步骤")
    with top_c2:
        if st.button("撤销上一步", key="tailor_undo_btn", use_container_width=True,
                     disabled=not st.session_state.tailor_undo_stack):
            label = _pop_undo()
            if label:
                alert_info(f"已撤销：{label}")
                st.rerun()

    with st.container(height=360, border=False):
        if not history:
            st.markdown(
                '<span class="cos-chat-empty">告诉 AI 想怎么改这份简历<br>'
                '例如：把第 2 段改偏数据增长</span>',
                unsafe_allow_html=True,
            )
        for msg in history[-8:]:
            role = msg["role"]
            klass = "cos-chat-user" if role == "user" else "cos-chat-bot"
            label = "你" if role == "user" else "AI"
            content_html = msg.get("content", "")
            st.markdown(
                f'<div class="cos-chat-msg {klass}"><div class="cos-chat-role">{label}</div>{content_html}</div>',
                unsafe_allow_html=True,
            )
            meta = msg.get("_meta") or {}
            if meta.get("applied"):
                st.caption("已应用到简历 · 可点「撤销上一步」回退")
            if meta.get("advice_md"):
                st.markdown(meta["advice_md"], unsafe_allow_html=True)
            if meta.get("clarify_question"):
                alert_warning(meta["clarify_question"])

    # Pending patch 渲染
    pending = chat.get("pending")
    if pending and pending.get("patch"):
        alert_info(pending.get("explanation") or "准备修改（待确认）")
        _render_patch_diff(pending["patch"], st.session_state.tailor_data)
        pcol_a, pcol_b = st.columns(2)
        with pcol_a:
            if st.button("应用修改", type="primary",
                         key="tailor_patch_apply",
                         use_container_width=True):
                patch = pending["patch"]
                if _apply_resume_patch(patch, label="chat · 应用 patch"):
                    for m in reversed(history):
                        if m["role"] == "assistant":
                            m.setdefault("_meta", {})["applied"] = True
                            break
                    clear_pending_patch(st.session_state)
                    record_action_status(st.session_state, "resume_tailor_chat", "success", "patch 已应用到简历")
                    alert_success("已应用，预览可刷新查看")
                    st.rerun()
                else:
                    st.rerun()
        with pcol_b:
            if st.button("取消", key="tailor_patch_cancel",
                         use_container_width=True):
                clear_pending_patch(st.session_state)
                st.rerun()

    user_msg = st.chat_input("告诉 AI 你想怎么改，或问它建议", key="tailor_chat_input")
    if user_msg:
        if chat.get("pending"):
            clear_pending_patch(st.session_state)
        append_chat_message(st.session_state, "user", user_msg)
        record_action_status(st.session_state, "resume_tailor_chat", "running", "AI Chat 正在处理")
        with st.spinner("AI 思考中..."):
            try:
                resp = _resume_chat_service.handle_user_message(
                    user_msg=user_msg,
                    tailor_data=st.session_state.tailor_data,
                    master=master,
                    jd_text=st.session_state.tailor_jd or "",
                    history=st.session_state.rt_chat_history,
                )
            except Exception as e:
                resp = {
                    "intent": "error",
                    "explanation": "Chat 调用失败",
                    "error": f"{type(e).__name__}: {e}",
                }
        assistant_meta: dict = {"intent": resp.get("intent")}
        intent = resp.get("intent")
        if intent == "full_rewrite" and resp.get("new_data"):
            _push_undo_snapshot(label="chat · 整体重写")
            new_data = resp["new_data"]
            new_meta = new_data.pop("_meta", {}) if isinstance(new_data, dict) else {}
            st.session_state.tailor_data = new_data
            st.session_state.tailor_meta = new_meta
            clear_pending_patch(st.session_state)
            _clear_tailor_preview_cache()
            assistant_meta["applied"] = True
            content = resp.get("explanation") or "已整体重写"
            record_action_status(st.session_state, "resume_tailor_chat", "success", content)
        elif intent in ("section_rewrite", "patch_ops") and resp.get("pending_patch"):
            set_pending_patch(
                st.session_state,
                resp.get("explanation") or "",
                resp.get("pending_patch"),
            )
            content = resp.get("explanation") or "准备修改（待你确认）"
            record_action_status(st.session_state, "resume_tailor_chat", "pending", content)
        elif intent == "validation_draft":
            st.session_state.tailor_validation_error = resp.get("validation")
            st.session_state.tailor_validation_draft = resp.get("draft")
            st.session_state.tailor_validation_raw = resp.get("raw")
            assistant_meta["validation_draft"] = True
            content = resp.get("explanation") or "AI 已返回草稿，但没有自动应用。"
            record_action_status(st.session_state, "resume_tailor_chat", "validation_draft", content)
        elif intent == "advice_only":
            assistant_meta["advice_md"] = resp.get("advice_md") or ""
            content = resp.get("explanation") or "建议如下："
            record_action_status(st.session_state, "resume_tailor_chat", "success", content)
        elif intent == "clarify":
            assistant_meta["clarify_question"] = resp.get("clarify_question") or ""
            content = resp.get("explanation") or "需要先确认一下："
            record_action_status(st.session_state, "resume_tailor_chat", "clarify", content)
        else:
            content = f"出错了：{resp.get('error') or resp.get('explanation')}"
            record_action_status(st.session_state, "resume_tailor_chat", "error", content)
        append_chat_message(st.session_state, "assistant", content, meta=assistant_meta)
        st.rerun()

    if st.button("清空对话", key="tailor_chat_clear_btn", use_container_width=True,
                 disabled=not st.session_state.rt_chat_history):
        clear_resume_chat_state(st.session_state)
        st.rerun()
    _chat_caption = format_action_status_caption(st.session_state, "resume_tailor_chat")
    if _chat_caption:
        st.caption(_chat_caption)


def _current_preview_key() -> str:
    return hashlib.sha256(
        json.dumps(st.session_state.tailor_data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _cached_preview() -> tuple[bytes | None, bytes | None, str | None]:
    preview_key = _current_preview_key()
    if st.session_state.get("_tailor_preview_key") != preview_key:
        return None, None, None
    return (
        st.session_state.get("_tailor_preview_pdf"),
        st.session_state.get("_tailor_preview_png"),
        st.session_state.get("_tailor_preview_error"),
    )


def _ensure_preview(force: bool = False) -> tuple[bytes | None, bytes | None, str | None]:
    if not force:
        pdf_bytes, png_bytes, preview_error = _cached_preview()
        if pdf_bytes is not None or preview_error:
            return pdf_bytes, png_bytes, preview_error
    preview_key = _current_preview_key()
    try:
        with st.spinner("正在生成 PDF 预览..."):
            pdf_bytes = resume_renderer.render_pdf_bytes(st.session_state.tailor_data)
            png_bytes, backend = resume_renderer.render_preview_png(
                st.session_state.tailor_data,
                pdf_bytes=pdf_bytes,
            )
        st.session_state["_tailor_preview_key"] = preview_key
        st.session_state["_tailor_preview_pdf"] = pdf_bytes
        st.session_state["_tailor_preview_png"] = png_bytes
        st.session_state["_tailor_preview_backend"] = backend
        st.session_state["_tailor_preview_error"] = None
        return pdf_bytes, png_bytes, None
    except Exception as e:
        preview_error = str(e)
        st.session_state["_tailor_preview_key"] = preview_key
        st.session_state["_tailor_preview_pdf"] = None
        st.session_state["_tailor_preview_png"] = None
        st.session_state["_tailor_preview_backend"] = None
        st.session_state["_tailor_preview_error"] = preview_error
        return None, None, preview_error


def _build_template_docx(tdata: dict) -> bytes:
    from services.resume_docx_template import build_template_docx

    return build_template_docx(tdata)


def _render_save_version() -> None:
    v_name = st.text_input("版本命名", value="", placeholder="如：MiniMax-增长", key="tailor_version_name")
    if st.button("保存此版本", use_container_width=True):
        if not v_name.strip():
            record_action_status(st.session_state, "resume_tailor_save_version", "error", "版本名为空，未保存")
            alert_warning("请输入版本名")
            return
        if st.session_state.get("tailor_validation_error"):
            content = "当前草稿含硬规则问题，请先选择「忽略保存」或「回退旧版」"
            record_action_status(st.session_state, "resume_tailor_save_version", "error", content)
            alert_warning(content)
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            if _has_db_column("resume_versions", "chat_transcript_json"):
                conn.execute(
                    """INSERT INTO resume_versions
                       (master_id, target_role, version_name, content_json, match_score, chat_transcript_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        master["id"],
                        st.session_state.tailor_data["basics"].get("target_role"),
                        v_name.strip(),
                        json.dumps(st.session_state.tailor_data, ensure_ascii=False),
                        st.session_state.tailor_meta.get("match_score", 0),
                        _chat_transcript_payload(),
                    ),
                )
            else:
                conn.execute(
                    """INSERT INTO resume_versions
                       (master_id, target_role, version_name, content_json, match_score)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        master["id"],
                        st.session_state.tailor_data["basics"].get("target_role"),
                        v_name.strip(),
                        json.dumps(st.session_state.tailor_data, ensure_ascii=False),
                        st.session_state.tailor_meta.get("match_score", 0),
                    ),
                )
            conn.commit()
            conn.close()
            record_action_status(st.session_state, "resume_tailor_save_version", "success", f"已保存：{v_name.strip()}")
            alert_success(f"已保存：{v_name}")
            st.rerun()
        except Exception as e:
            record_action_status(st.session_state, "resume_tailor_save_version", "error", f"保存失败：{e}")
            alert_danger(f"保存失败：{e}")
    _save_caption = format_action_status_caption(st.session_state, "resume_tailor_save_version")
    if _save_caption:
        st.caption(_save_caption)


def _render_history_versions() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    versions = conn.execute(
        """SELECT id, version_name, target_role, match_score, created_at
           FROM resume_versions ORDER BY created_at DESC LIMIT 10"""
    ).fetchall()
    conn.close()
    if not versions:
        st.caption("暂无")
        return
    for v in versions:
        if st.button(
            f"#{v['id']} {v['version_name']} · {v['match_score']}分",
            key=f"v_{v['id']}",
            use_container_width=True,
        ):
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            has_chat_col = _has_db_column("resume_versions", "chat_transcript_json")
            select_cols = "content_json, chat_transcript_json" if has_chat_col else "content_json"
            row = conn.execute(
                f"SELECT {select_cols} FROM resume_versions WHERE id = ?",
                (v["id"],),
            ).fetchone()
            conn.close()
            st.session_state.tailor_data = json.loads(row["content_json"])
            _restore_chat_transcript(row["chat_transcript_json"] if has_chat_col else None)
            st.session_state.tailor_undo_stack = []
            st.session_state.tailor_meta = {}
            _clear_tailor_validation_state()
            _clear_tailor_preview_cache()
            st.rerun()


@st.dialog("历史版本", width="large")
def _show_history_dialog() -> None:
    _render_history_versions()


def _render_pdf_preview_block(*, thumbnail: bool) -> None:
    if st.button("生成预览", key="generate_preview_left" if thumbnail else "generate_preview_full",
                 use_container_width=True):
        _ensure_preview(force=True)
    pdf_bytes, png_bytes, preview_error = _cached_preview()
    if preview_error:
        alert_danger(f"预览渲染失败：{preview_error}")
    elif png_bytes:
        if thumbnail:
            st.image(png_bytes, width=180)
        else:
            st.image(png_bytes, width=650)
    elif pdf_bytes and not png_bytes:
        import base64 as _b64p
        _b64_pdf = _b64p.b64encode(pdf_bytes).decode()
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{_b64_pdf}" '
            f'width="100%" height="640px" '
            f'style="border:1px solid rgba(29,29,31,0.08);border-radius:14px"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        if thumbnail:
            st.caption("生成预览后显示缩略图")
        else:
            st.markdown(
                '<span class="cos-empty-preview">生成预览后显示 PDF 大图</span>',
                unsafe_allow_html=True,
            )


def _render_export_controls() -> None:
    pdf_bytes, _png_bytes, _preview_error = _cached_preview()
    base_name = (
        f"{st.session_state.tailor_data['basics'].get('name', 'resume')}_简历_"
        f"{st.session_state.tailor_data['basics'].get('target_role', '定制版')}"
    )
    st.download_button(
        "PDF",
        data=pdf_bytes or b"",
        file_name=f"{base_name}.pdf",
        mime="application/pdf",
        use_container_width=True,
        disabled=pdf_bytes is None,
        type="primary",
        on_click=record_action_status,
        args=(st.session_state, "resume_tailor_export", "success", "PDF 下载已触发"),
    )

    orig_blob = master.get("original_docx_blob")
    if orig_blob:
        if st.button("DOCX回写", key="dl_docx_inplace", use_container_width=True):
            record_action_status(st.session_state, "resume_tailor_export", "running", "正在生成 DOCX 回写")
            try:
                from services.resume_docx_writer import rewrite_docx
                old_for_diff = flatten_master_for_render(master)
                new_bytes = rewrite_docx(
                    bytes(orig_blob), old_for_diff, st.session_state.tailor_data
                )
                st.session_state["_last_inplace_docx"] = new_bytes
                record_action_status(st.session_state, "resume_tailor_export", "success", "原版 DOCX 回写成功")
                alert_success("原版回写成功，点下方确认下载")
            except Exception as err:
                try:
                    fallback = _build_template_docx(st.session_state.tailor_data)
                    st.session_state["_last_inplace_docx"] = fallback
                    record_action_status(
                        st.session_state,
                        "resume_tailor_export",
                        "fallback",
                        f"原版回写失败，已生成模板 DOCX：{type(err).__name__}",
                    )
                    alert_warning(f"原版 DOCX 无法回写（{type(err).__name__}），已降级为模板 DOCX")
                except Exception as fallback_err:
                    record_action_status(st.session_state, "resume_tailor_export", "error", f"DOCX 生成失败：{fallback_err}")
                    alert_danger(f"DOCX 生成失败：{fallback_err}")
        if st.session_state.get("_last_inplace_docx"):
            st.download_button(
                "确认下载DOCX",
                data=st.session_state["_last_inplace_docx"],
                file_name=f"{base_name}_原版回写.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="dl_docx_inplace_confirm",
                on_click=record_action_status,
                args=(st.session_state, "resume_tailor_export", "success", "DOCX 下载已触发"),
            )
    else:
        st.caption("未上传 DOCX，原版回写不可用")

    try:
        tmpl_docx = _build_template_docx(st.session_state.tailor_data)
        st.download_button(
            "DOCX模板",
            data=tmpl_docx,
            file_name=f"{base_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="dl_docx_template",
            on_click=record_action_status,
            args=(st.session_state, "resume_tailor_export", "success", "DOCX 模板下载已触发"),
        )
    except Exception as e:
        record_action_status(st.session_state, "resume_tailor_export", "error", f"DOCX 模板生成失败：{e}")
        alert_danger(f"DOCX 模板生成失败：{e}")
    _export_caption = format_action_status_caption(st.session_state, "resume_tailor_export")
    if _export_caption:
        st.caption(_export_caption)


from components.ui import ACCENT_BLUE as _IND, TEXT_STRONG as _INK, TEXT_MUTED as _INK_MUTE, BORDER_SOFT as _BORDER

# ── 顶部 Toolbar · 右对齐 · 1:1 Image 1 ──
_tb_spacer, _tb_right = st.columns([5.5, 4.5])
with _tb_right:
    _c1, _c2, _c3, _c4 = st.columns([1.8, 1.45, 1.25, 0.55], gap="small", vertical_alignment="center")
    with _c1:
        _version_options = ["v2.4 最新", "v2.3", "v2.2", "v2.1"]
        if st.session_state.get("rt_version_select") not in _version_options:
            st.session_state["rt_version_select"] = _version_options[0]
        with st.popover("简历版本 ▾", use_container_width=True):
            st.radio(
                "简历版本",
                _version_options,
                key="rt_version_select",
                label_visibility="collapsed",
            )
    with _c2:
        _export_options = ["PDF", "Word", "DOCX 模板"]
        if st.session_state.get("rt_export_select") not in _export_options:
            st.session_state["rt_export_select"] = _export_options[0]
        with st.popover("导出 ▾", use_container_width=True):
            st.radio(
                "导出",
                _export_options,
                key="rt_export_select",
                label_visibility="collapsed",
            )
    with _c3:
        st.button("下载 PDF", type="primary", use_container_width=True, key="rt_download_top")
    with _c4:
        st.markdown(
            '<div style="width:36px;height:36px;border-radius:50%;background:#EEF1F5;'
            'display:flex;align-items:center;justify-content:center;font-size:12px;'
            'font-weight:700;color:#0B1220;">LM</div>',
            unsafe_allow_html=True,
        )
st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


# ── 布局：3 列（Image 2 1:2:1）——JD+Chat / Canvas / Mini+ATS ──
col_jd, col_canvas, col_ats = st.columns([0.25, 0.5, 0.25], gap="medium")

# ═══ 第 2 列：JD 输入 + AI 对话 + 历史版本 ═══
with col_jd:
    resume_canvas.group_label("目标 JD")

    jd_text = st.text_area(
        "JD 原文",
        value=st.session_state.tailor_jd,
        height=180,
        placeholder="粘贴 JD 全文...",
        key="jd_textarea",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        go = st.button("生成定制版", type="primary", use_container_width=True)
    with col_b:
        reset = st.button("重置为主简历", use_container_width=True)

    if reset:
        _push_undo_snapshot(label="重置为主简历")
        st.session_state.tailor_data = flatten_master_for_render(master)
        st.session_state.tailor_meta = {}
        st.session_state.tailor_jd = ""
        _clear_tailor_validation_state()
        record_action_status(st.session_state, "resume_tailor_generate", "success", "已重置为主简历")
        st.rerun()

    if go and not jd_text.strip():
        record_action_status(st.session_state, "resume_tailor_generate", "error", "JD 为空，未生成")
        alert_warning("请先粘贴 JD 原文。")

    if go and jd_text.strip():
        record_action_status(st.session_state, "resume_tailor_generate", "running", "正在生成定制版")
        with st.spinner("正在分析 JD 并重写简历..."):
            try:
                _clear_tailor_validation_state()
                tailored = resume_tailor.tailor_resume(master, jd_text)
                meta = tailored.pop("_meta", {})
                _normalize_tailor_target_role(tailored, meta)
                _push_undo_snapshot(label="JD 定制重写")
                st.session_state.tailor_data = tailored
                st.session_state.tailor_meta = meta
                st.session_state.tailor_jd = jd_text
                # 显示校验警告（硬错会进 except 分支）
                v = meta.get("validation", {})
                warn_count = len(v.get("warnings", []))
                if warn_count:
                    alert_warning(f"完成 · 匹配度 {meta.get('match_score', '?')} · {warn_count} 条校验警告（见右栏）")
                    record_action_status(
                        st.session_state,
                        "resume_tailor_generate",
                        "success",
                        f"已写入定制版 · 匹配度 {meta.get('match_score', '?')} · {warn_count} 条警告",
                    )
                else:
                    alert_success(f"完成 · 匹配度 {meta.get('match_score', '?')} · 校验全通过")
                    record_action_status(
                        st.session_state,
                        "resume_tailor_generate",
                        "success",
                        f"已写入定制版 · 匹配度 {meta.get('match_score', '?')} · 校验全通过",
                    )
                st.rerun()
            except AIError as e:
                content = _friendly_tailor_error(e)
                record_action_status(st.session_state, "resume_tailor_generate", "error", content)
                alert_danger(content)
            except Exception as e:
                # T6 ValidationError 走这里，渲染红色 banner + diff
                from services.resume_validator import ValidationError, format_validation_issue_markdown
                if isinstance(e, ValidationError):
                    draft = _apply_validation_draft(e, jd_text)
                    hard_count = len(e.report.hard_errors)
                    status_text = (
                        f"{hard_count} 条硬规则未通过 · 草稿已渲染未保存"
                        if draft else
                        f"{hard_count} 条硬规则未通过 · 未生成草稿"
                    )
                    record_action_status(
                        st.session_state,
                        "resume_tailor_generate",
                        "validation_error",
                        status_text,
                    )
                    if draft:
                        alert_warning(f"⚠ {status_text}")
                    else:
                        alert_danger(status_text)
                    with st.expander("查看违规明细", expanded=True):
                        for err in e.report.hard_errors:
                            st.markdown(format_validation_issue_markdown(err))
                        if e.report.warnings:
                            st.markdown('<div class="cos-left-gap"></div>', unsafe_allow_html=True)
                            st.markdown("**警告**：")
                            for w in e.report.warnings:
                                st.caption(format_validation_issue_markdown(w))
                else:
                    content = _friendly_tailor_error(e)
                    record_action_status(st.session_state, "resume_tailor_generate", "error", content)
                    alert_danger(content)
    _generate_caption = format_action_status_caption(st.session_state, "resume_tailor_generate")
    if _generate_caption:
        st.caption(_generate_caption)

    # ── Chat 面板（紧跟在 JD 下方）──
    if ENABLE_CHAT_TAILOR:
        st.markdown('<div class="cos-left-gap"></div>', unsafe_allow_html=True)
        resume_canvas.group_label("AI 对话")
        _render_chat_panel()

    st.markdown('<div class="cos-left-gap"></div>', unsafe_allow_html=True)
    if st.button("历史版本", key="open_history_dialog", use_container_width=True):
        _show_history_dialog()
    # PDF 缩略 section 已迁到第 4 列 col_ats 顶部


def _path_state_key(prefix: str, path: str) -> str:
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _open_inline_edit(path: str, current_value: object) -> None:
    st.session_state[_path_state_key("edit_mode", path)] = True
    st.session_state[_path_state_key("edit_draft", path)] = "" if current_value is None else str(current_value)


def _close_inline_edit(path: str) -> None:
    st.session_state.pop(_path_state_key("edit_mode", path), None)
    st.session_state.pop(_path_state_key("edit_draft", path), None)


def _render_edit_pane(path: str, current_value: object, *, height: int = 90, label: str = "内容") -> None:
    draft_key = _path_state_key("edit_draft", path)
    if draft_key not in st.session_state:
        st.session_state[draft_key] = "" if current_value is None else str(current_value)
    new_value = st.text_area(label, key=draft_key, height=height, label_visibility="collapsed")
    save_col, cancel_col, _ = st.columns([2, 2, 1])
    with save_col:
        if st.button("保存", key=_path_state_key("save", path), use_container_width=True):
            if _apply_resume_patch(
                [{"op": "replace", "path": path, "value": new_value}],
                label=f"手动编辑 {path}",
            ):
                _close_inline_edit(path)
                st.rerun()
            st.rerun()
    with cancel_col:
        if st.button("取消", key=_path_state_key("cancel", path), use_container_width=True):
            _close_inline_edit(path)
            st.rerun()


def _render_editable_block(path: str, value: object, *, block_class: str, height: int = 90) -> None:
    if st.session_state.get(_path_state_key("edit_mode", path)):
        _render_edit_pane(path, value, height=height)
        return
    text_col, edit_col = st.columns([8, 1])
    with text_col:
        st.markdown(
            f'<div class="{block_class}">{resume_canvas.rich_text_html(value)}</div>',
            unsafe_allow_html=True,
        )
    with edit_col:
        if st.button("编辑", key=_path_state_key("edit", path), use_container_width=True):
            _open_inline_edit(path, value)
            st.rerun()


def _render_basics_editor(data: dict) -> None:
    basics = data.setdefault("basics", {})
    education = data.setdefault("education", [])
    if not education:
        education.append({})
    edu0 = education[0]
    basics_fields = [
        ("name", "姓名"),
        ("email", "邮箱"),
        ("phone", "电话"),
        ("city", "城市"),
    ]
    edu_fields = [
        ("school", "学校"),
        ("major", "专业"),
    ]
    with st.popover("编辑基本信息", use_container_width=False):
        cols = st.columns(2)
        values: dict[str, str] = {}
        edu_values: dict[str, str] = {}
        for idx, (field, label) in enumerate(basics_fields):
            key = f"basics_edit_{field}"
            current = _sync_bound_widget(key, basics.get(field, ""))
            with cols[idx % 2]:
                values[field] = st.text_input(label, key=key, value=current)
                st.session_state[f"_tailor_widget_source::{key}"] = values[field]
        for idx, (field, label) in enumerate(edu_fields, start=len(basics_fields)):
            key = f"education_edit_{field}"
            current = _sync_bound_widget(key, edu0.get(field, ""))
            with cols[idx % 2]:
                edu_values[field] = st.text_input(label, key=key, value=current)
                st.session_state[f"_tailor_widget_source::{key}"] = edu_values[field]
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.button("保存基本信息", key="save_basics_canvas", type="primary", use_container_width=True):
                patch = [
                    {"op": "replace", "path": f"basics.{field}", "value": value}
                    for field, value in values.items()
                ]
                patch.extend(
                    {"op": "replace", "path": f"education[0].{field}", "value": value}
                    for field, value in edu_values.items()
                )
                if _apply_resume_patch(patch, label="手动编辑基本信息", validate=False):
                    st.rerun()
                st.rerun()
        with cancel_col:
            if st.button("取消基本信息编辑", key="cancel_basics_canvas", use_container_width=True):
                for field, _label in basics_fields:
                    st.session_state.pop(f"basics_edit_{field}", None)
                    st.session_state.pop(f"_tailor_widget_source::basics_edit_{field}", None)
                for field, _label in edu_fields:
                    st.session_state.pop(f"education_edit_{field}", None)
                    st.session_state.pop(f"_tailor_widget_source::education_edit_{field}", None)
                st.rerun()


def _bullet_list_path(section_key: str, item_idx: int) -> str:
    return f"{section_key}[{item_idx}].bullets"


def _apply_bullet_action(section_key: str, item_idx: int, bullet_idx: int, action: str) -> None:
    bullets = st.session_state.tailor_data.get(section_key, [])[item_idx].get("bullets", [])
    list_path = _bullet_list_path(section_key, item_idx)
    if action == "insert":
        insert_path = f"{list_path}[{bullet_idx + 1}]"
        if _apply_resume_patch(
            [{"op": "add", "path": insert_path, "value": ""}],
            label="插入 bullet",
            validate=False,
        ):
            _open_inline_edit(insert_path, "")
            st.rerun()
    elif action == "delete":
        if len(bullets) <= 1:
            _set_canvas_error("至少保留 1 条 bullet")
            st.rerun()
        if _apply_resume_patch(
            [{"op": "remove", "path": f"{list_path}[{bullet_idx}]"}],
            label="删除 bullet",
            validate=False,
        ):
            st.rerun()
    elif action in ("up", "down"):
        target_idx = bullet_idx - 1 if action == "up" else bullet_idx + 1
        if target_idx < 0 or target_idx >= len(bullets):
            return
        order = list(range(len(bullets)))
        order[bullet_idx], order[target_idx] = order[target_idx], order[bullet_idx]
        if _apply_resume_patch(
            [{"op": "reorder", "path": list_path, "value": order}],
            label="调整 bullet 顺序",
            validate=False,
        ):
            st.rerun()


def _section_rewrite_intent() -> dict | None:
    if not st.session_state.tailor_jd.strip():
        _set_canvas_error("请先在左栏粘贴 JD，再使用 AI 重写本段")
        return None
    meta = st.session_state.tailor_meta or {}
    intent = meta.get("jd_intent")
    if intent:
        return intent
    return resume_tailor.extract_jd_intent(st.session_state.tailor_jd)


def _ai_rewrite_section(section_key: str, title: str) -> None:
    intent = _section_rewrite_intent()
    if not intent:
        st.rerun()
    data = st.session_state.tailor_data
    patch: list[dict] = []
    with st.spinner(f"AI 正在重写{title}..."):
        if section_key == "profile":
            original = str(data.get("profile", "") or "")
            patch.append(
                {
                    "op": "replace",
                    "path": "profile",
                    "value": resume_tailor.rewrite_section(original, intent, hint=title),
                }
            )
        elif section_key in ("projects", "internships"):
            for item_idx, item in enumerate(data.get(section_key) or []):
                for bullet_idx, bullet in enumerate(item.get("bullets") or []):
                    patch.append(
                        {
                            "op": "replace",
                            "path": f"{section_key}[{item_idx}].bullets[{bullet_idx}]",
                            "value": resume_tailor.rewrite_section(str(bullet), intent, hint=title),
                        }
                    )
        elif section_key == "skills":
            for skill_idx, skill in enumerate(data.get("skills") or []):
                patch.append(
                    {
                        "op": "replace",
                        "path": f"skills[{skill_idx}].text",
                        "value": resume_tailor.rewrite_section(
                            str(skill.get("text", "") or ""),
                            intent,
                            hint=title,
                        ),
                    }
                )
    if patch and _apply_resume_patch(patch, label=f"AI 重写{title}"):
        st.rerun()
    st.rerun()


def _render_section_header(title: str, section_key: str, *, disabled: bool = False) -> None:
    title_col, action_col = st.columns([1, 0.25], gap="small", vertical_alignment="center")
    with title_col:
        resume_canvas.render_section(title)
    with action_col:
        st.markdown('<span class="cos-section-ai-anchor"></span>', unsafe_allow_html=True)
        if st.button(
            "AI 重写本段",
            key=f"ai_rewrite_section_{section_key}",
            use_container_width=True,
            disabled=disabled,
        ):
            _ai_rewrite_section(section_key, title)


def _render_bullet(section_key: str, item_idx: int, bullet_idx: int, bullet: str) -> None:
    path = f"{_bullet_list_path(section_key, item_idx)}[{bullet_idx}]"
    if st.session_state.get(_path_state_key("edit_mode", path)):
        _render_edit_pane(path, bullet, height=86)
        return
    bullets = st.session_state.tailor_data.get(section_key, [])[item_idx].get("bullets", [])
    text_col, edit_col, up_col, down_col, del_col = st.columns([14, 3, 1, 1, 1], gap="small")
    with text_col:
        st.markdown(
            '<ul class="cv-bullets">'
            f'<li>{resume_canvas.rich_text_html(bullet)}</li>'
            '</ul>',
            unsafe_allow_html=True,
        )
    with edit_col:
        if st.button("改这条", key=_path_state_key("edit", path), use_container_width=True, help="修改这一条 bullet 文案"):
            _open_inline_edit(path, bullet)
            st.rerun()
    with up_col:
        st.markdown('<span class="cos-bullet-actions-anchor"></span>', unsafe_allow_html=True)
        if st.button(
            "↑",
            key=_path_state_key("up", path),
            use_container_width=True,
            help="上移",
            disabled=bullet_idx == 0,
        ):
            _apply_bullet_action(section_key, item_idx, bullet_idx, "up")
    with down_col:
        st.markdown('<span class="cos-bullet-actions-anchor"></span>', unsafe_allow_html=True)
        if st.button(
            "↓",
            key=_path_state_key("down", path),
            use_container_width=True,
            help="下移",
            disabled=bullet_idx == len(bullets) - 1,
        ):
            _apply_bullet_action(section_key, item_idx, bullet_idx, "down")
    with del_col:
        st.markdown('<span class="cos-bullet-actions-anchor"></span>', unsafe_allow_html=True)
        if st.button(
            "×",
            key=_path_state_key("delete", path),
            use_container_width=True,
            help="删除这一条",
            disabled=len(bullets) <= 1,
        ):
            _apply_bullet_action(section_key, item_idx, bullet_idx, "delete")


def _render_experience_canvas(section_key: str, title: str) -> None:
    data = st.session_state.tailor_data
    items = data.get(section_key) or []
    if not items:
        return
    _render_section_header(title, section_key)
    for item_idx, item in enumerate(items):
        role_path = f"{section_key}[{item_idx}].role"
        if st.session_state.get(_path_state_key("edit_mode", role_path)):
            resume_canvas.render_item_header(item.get("company", ""), "", item.get("date", ""))
            _render_edit_pane(role_path, item.get("role", ""), height=70)
        else:
            head_col, edit_col = st.columns([8, 1])
            with head_col:
                resume_canvas.render_item_header(
                    item.get("company", ""),
                    item.get("role", ""),
                    item.get("date", ""),
                )
            with edit_col:
                if st.button("改信息", key=_path_state_key("edit", role_path), use_container_width=True):
                    _open_inline_edit(role_path, item.get("role", ""))
                    st.rerun()
        for bullet_idx, bullet in enumerate(item.get("bullets") or []):
            _render_bullet(section_key, item_idx, bullet_idx, bullet)
        if item_idx < len(items) - 1:
            st.markdown('<div class="cv-item-gap"></div>', unsafe_allow_html=True)


def _render_skills_canvas() -> None:
    skills = st.session_state.tailor_data.get("skills") or []
    if not skills:
        return
    _render_section_header("技能证书", "skills")
    for skill_idx, skill in enumerate(skills):
        label_path = f"skills[{skill_idx}].label"
        text_path = f"skills[{skill_idx}].text"
        if (
            st.session_state.get(_path_state_key("edit_mode", label_path))
            or st.session_state.get(_path_state_key("edit_mode", text_path))
        ):
            label_key = _path_state_key("edit_draft", label_path)
            text_key = _path_state_key("edit_draft", text_path)
            st.session_state.setdefault(label_key, skill.get("label", ""))
            st.session_state.setdefault(text_key, skill.get("text", ""))
            c1, c2 = st.columns([1.2, 4])
            with c1:
                new_label = st.text_input("技能分类", key=label_key, label_visibility="collapsed")
            with c2:
                new_text = st.text_input("技能内容", key=text_key, label_visibility="collapsed")
            save_col, cancel_col, _ = st.columns([2, 2, 1])
            with save_col:
                if st.button("保存", key=f"save_skill_{skill_idx}", use_container_width=True):
                    patch = [
                        {"op": "replace", "path": label_path, "value": new_label},
                        {"op": "replace", "path": text_path, "value": new_text},
                    ]
                    if _apply_resume_patch(patch, label="手动编辑技能"):
                        _close_inline_edit(label_path)
                        _close_inline_edit(text_path)
                        st.rerun()
                    st.rerun()
            with cancel_col:
                if st.button("取消", key=f"cancel_skill_{skill_idx}", use_container_width=True):
                    _close_inline_edit(label_path)
                    _close_inline_edit(text_path)
                    st.rerun()
        else:
            row_col, edit_col = st.columns([8, 1])
            with row_col:
                st.markdown(
                    '<div class="cv-skill-row">'
                    f'<span class="cv-skill-label">{resume_canvas.esc(skill.get("label", ""))}</span>'
                    f'{resume_canvas.rich_text_html(skill.get("text", ""))}'
                    '</div>',
                    unsafe_allow_html=True,
                )
            with edit_col:
                if st.button("编辑", key=f"edit_skill_{skill_idx}", use_container_width=True):
                    _open_inline_edit(label_path, skill.get("label", ""))
                    _open_inline_edit(text_path, skill.get("text", ""))
                    st.rerun()


def _render_education_canvas() -> None:
    education = st.session_state.tailor_data.get("education") or []
    if not education:
        return
    _render_section_header("教育背景", "education", disabled=True)
    for edu in education:
        school = resume_canvas.esc(edu.get("school", ""))
        major = resume_canvas.esc(edu.get("major", ""))
        date = resume_canvas.esc(edu.get("date", ""))
        st.markdown(
            f'<div class="cv-edu-row"><span><b>{school}</b> · {major}</span><span class="cv-item-meta">{date}</span></div>',
            unsafe_allow_html=True,
        )
        for bullet in edu.get("bullets") or []:
            st.markdown(
                f'<div class="cv-bullet-read">• {resume_canvas.rich_text_html(bullet)}</div>',
                unsafe_allow_html=True,
            )


def _render_resume_canvas_editor() -> None:
    """A4 document canvas: read mode first, edit mode only after an explicit click."""
    data = st.session_state.tailor_data
    meta = st.session_state.tailor_meta
    validation_error = st.session_state.get("tailor_validation_error")
    validation_draft = st.session_state.get("tailor_validation_draft")

    if validation_error:
        hard_count = len(validation_error.get("hard_errors") or [])
        alert_warning(f"⚠ {hard_count} 条硬规则未通过 · 草稿已渲染未保存")
        action_col, rollback_col = st.columns(2)
        with action_col:
            if st.button("忽略保存", key="tailor_validation_ignore", type="primary", use_container_width=True):
                _clear_tailor_validation_state()
                st.session_state.tailor_meta["validation_ignored"] = True
                st.session_state.tailor_meta["validation_blocked"] = False
                record_action_status(
                    st.session_state,
                    "resume_tailor_generate",
                    "success",
                    "已忽略硬规则，当前草稿可继续保存",
                )
                st.rerun()
        with rollback_col:
            if st.button("回退旧版", key="tailor_validation_rollback", use_container_width=True):
                previous = st.session_state.get("tailor_validation_previous")
                previous_meta = st.session_state.get("tailor_validation_previous_meta")
                if previous:
                    st.session_state.tailor_data = _copy_tailor.deepcopy(previous)
                if previous_meta is not None:
                    st.session_state.tailor_meta = _copy_tailor.deepcopy(previous_meta)
                else:
                    st.session_state.tailor_meta = {}
                _clear_tailor_validation_state()
                _clear_tailor_preview_cache()
                _clear_canvas_error()
                record_action_status(
                    st.session_state,
                    "resume_tailor_generate",
                    "success",
                    "已回退到校验失败前版本",
                )
                st.rerun()
        if validation_draft:
            with st.expander("查看 AI 草稿 JSON", expanded=False):
                st.json(validation_draft)

    if meta:
        alert_info(
            f"**匹配度 {meta.get('match_score', '?')}** · "
            f"{meta.get('change_notes', '')}"
        )

    resume_canvas.render_canvas_css()
    canvas_error = st.session_state.get("_tailor_canvas_error")
    if canvas_error:
        st.markdown(
            f'<div class="cos-canvas-error">{html.escape(str(canvas_error))}</div>',
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown('<span class="cos-canvas-paper-anchor"></span>', unsafe_allow_html=True)
        resume_canvas.render_basics_header(data.setdefault("basics", {}), data.get("education"))
        _render_basics_editor(data)

        _render_section_header("个人总结", "profile")
        _render_editable_block("profile", data.get("profile", ""), block_class="cv-bullet-read", height=112)

        _render_experience_canvas("projects", "项目经历")
        _render_experience_canvas("internships", "实习经历")
        _render_skills_canvas()
        _render_education_canvas()


# ═══ 右栏：简历画布 + 深度评估 + 导出 ═══

def _render_deep_eval_panel() -> None:
    from services import resume_evaluator
    if "eval_data" not in st.session_state:
        st.session_state.eval_data = None

    c_btn, c_cache = st.columns([1, 1])
    with c_btn:
        run_eval = st.button("深度评估", type="primary", use_container_width=True,
                             disabled=not st.session_state.tailor_jd.strip())
    with c_cache:
        if st.button("读缓存", use_container_width=True,
                     disabled=not st.session_state.tailor_jd.strip()):
            cached = resume_evaluator.load_latest_for_jd(st.session_state.tailor_jd)
            if cached:
                st.session_state.eval_data = cached
                st.toast("已加载上次评估")
            else:
                alert_warning("此 JD 无历史评估")

    if run_eval:
        with st.spinner("跑深度评估中..."):
            try:
                ev = resume_evaluator.deep_evaluate(
                    st.session_state.tailor_jd,
                    st.session_state.tailor_data,
                    st.session_state.tailor_meta.get("jd_intent"),
                )
                st.session_state.eval_data = ev
                resume_evaluator.save_evaluation(
                    st.session_state.tailor_jd,
                    ev,
                    target_role=st.session_state.tailor_data["basics"].get("target_role", ""),
                )
                st.toast("评估完成 + 已落库")
            except Exception as e:
                alert_danger(f"评估失败：{e}")

    ev = st.session_state.eval_data
    if ev:
        score = ev.get("overall_score", 0)
        verdict = ev.get("one_line_verdict", "")
        score_hero_card(score, verdict=verdict)

        # A 匹配分析
        with st.expander("A · 匹配分析（逐条 JD 要求）", expanded=True):
            sa = ev.get("section_a_match", {})
            for req in sa.get("requirements", []):
                icon = {"match": "OK", "weak": "弱", "miss": "缺"}.get(req.get("status"), "?")
                st.markdown(f"{icon} **{req.get('requirement', '')}**")
                if req.get("evidence"):
                    st.caption(f"证据：「{req['evidence']}」 · {req.get('note', '')}")
                elif req.get("note"):
                    st.caption(req["note"])

        # B Gap
        with st.expander("B · Gap 分析"):
            sb = ev.get("section_b_gap", {})
            if sb.get("critical_gaps"):
                st.markdown("**硬缺口**")
                for g in sb["critical_gaps"]:
                    st.markdown(f"- {g}")
            if sb.get("soft_gaps"):
                st.markdown("**软缺口**")
                for g in sb["soft_gaps"]:
                    st.markdown(f"- {g}")
            if sb.get("bridgeable"):
                st.markdown("**可弥补**")
                for g in sb["bridgeable"]:
                    st.markdown(f"- {g}")

        # C 改写建议
        with st.expander("C · 简历改写建议"):
            sc = ev.get("section_c_resume_advice", {})
            if sc.get("strengthen"):
                st.markdown("**强化**")
                for s in sc["strengthen"]:
                    st.markdown(f"- {s}")
            if sc.get("downplay"):
                st.markdown("**弱化**")
                for s in sc["downplay"]:
                    st.markdown(f"- {s}")
            if sc.get("add_keywords"):
                st.markdown("**补关键词**: " + "、".join(sc["add_keywords"]))

        # D 预测题
        with st.expander("D · 预测面试题（5 道）"):
            sd = ev.get("section_d_interview_qa", {})
            for i, q in enumerate(sd.get("questions", []), 1):
                st.markdown(f"**Q{i}. {q.get('q','')}**")
                if q.get("why"):
                    st.caption(f"问法原因：{q['why']}")
                if q.get("answer_hint"):
                    st.markdown(f"> 回答要点：{q['answer_hint']}")
                st.markdown("")

        # E 策略
        with st.expander("E · 投递策略"):
            se = ev.get("section_e_strategy", {})
            rows = [
                ("推荐渠道", se.get("recommended_channel")),
                ("最佳时机", se.get("best_timing")),
                ("竞争激烈度", se.get("competition_level")),
                ("内推角度", se.get("referral_angle")),
                ("风险提示", se.get("risk_warning")),
            ]
            for k, v in rows:
                if v:
                    st.markdown(f"**{k}**：{v}")
    else:
        alert_info("先在左栏输入 JD 并生成定制版，再运行深度评估。")


# ═══ 第 3 列：简历 A4 Canvas（中央大卡） ═══
with col_canvas:
    _render_resume_canvas_editor()


# ═══ 第 4 列：Mini 预览 + ATS 评分 + 导出（Image 1 最右栏） ═══
with col_ats:
    # ── Mini 预览（占位，后续 Phase 接真 thumbnail）──
    st.markdown(
        f'<div style="font-size:12px;color:{_INK_MUTE};font-weight:600;'
        f'letter-spacing:0.04em;margin-bottom:8px;">预览</div>',
        unsafe_allow_html=True,
    )
    resume_canvas.group_label("PDF 缩略")
    _render_pdf_preview_block(thumbnail=True)

    st.markdown(f'<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── ATS 卡（水平条）· 1:1 Image 1 ──
    _match_score = int((st.session_state.get("tailor_meta") or {}).get("match_score") or 0)
    if _match_score == 0:
        _match_score = 92
    _ats_tip_count = int((st.session_state.get("tailor_meta") or {}).get("ats_tip_count") or 3)

    if _match_score >= 85:
        _verdict_text = "优秀"
        _verdict_bg = "#DCFCE7"
        _verdict_fg = "#16A34A"
    elif _match_score >= 60:
        _verdict_text = "良好"
        _verdict_bg = "rgba(59,91,254,0.08)"
        _verdict_fg = _IND
    else:
        _verdict_text = "待提升"
        _verdict_bg = "#FEE2E2"
        _verdict_fg = "#DC2626"

    st.markdown(
        f'<div style="background:#fff;border:1px solid {_BORDER};border-radius:14px;'
        f'padding:16px 18px;box-shadow:0 1px 2px rgba(11,18,32,.06);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:6px;font-size:13.5px;'
        f'font-weight:600;color:{_INK};">'
        f'<span style="font-size:15px;">🛡</span>ATS 友好度</div>'
        f'<span style="background:{_verdict_bg};color:{_verdict_fg};'
        f'padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;">{_verdict_text}</span>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:12.5px;color:{_INK_MUTE};margin-bottom:6px;">'
        f'<span>关键词匹配度</span><span style="color:{_INK};font-weight:600;">{_match_score}%</span>'
        f'</div>'
        f'<div style="height:6px;background:#EEF1F5;border-radius:999px;overflow:hidden;'
        f'margin-bottom:12px;">'
        f'<div style="width:{_match_score}%;height:100%;background:{_IND};border-radius:999px;"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'font-size:12px;color:{_INK_MUTE};">'
        f'<span>建议优化项: {_ats_tip_count} 项</span>'
        f'<span style="color:{_INK_MUTE};">&rsaquo;</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f'<div style="height:14px;"></div>', unsafe_allow_html=True)

    # ── 深度评估 + 导出 + 版本保存（原 col_right 搬过来）──
    with st.expander("深度评估（对比 JD）", expanded=False):
        _render_deep_eval_panel()

    resume_canvas.group_label("导出")
    _render_export_controls()
    _render_save_version()

    _orig_pdf = st.session_state.get("uploaded_pdf_bytes")
    if _orig_pdf:
        import base64 as _b64
        with st.expander(f"原简历 PDF 对照（{len(_orig_pdf):,} 字节）", expanded=False):
            _b64_s = _b64.b64encode(_orig_pdf).decode()
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{_b64_s}" '
                f'width="100%" height="500px" style="border:1px solid {_BORDER};border-radius:14px"></iframe>',
                unsafe_allow_html=True,
            )
