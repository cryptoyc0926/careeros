"""Pipeline — 求职申请看板追踪。"""

import streamlit as st
import pandas as pd
from models.database import query, execute
from services.job_filter import filter_excluded_rows
from components.ui import (
    page_header, section_title, divider, badge, empty_state,
    kanban_column_card, kanban_empty, alert_success, alert_info,
    TEXT_MUTED, SP_2,
)

page_header("申请进度追踪", subtitle="每个岗位走到哪一步了")

# ── 看板视图（包含所有 8 种状态）───────────────────────────
STATUS_CONFIG = [
    ("bookmarked",       "已收藏",     "muted"),
    ("resume_generated", "已生成简历", "info"),
    ("applied",          "已投递",     "info"),
    ("follow_up",        "跟进中",     "warning"),
    ("interview",        "面试中",     "success"),
    ("offer",            "已拿 Offer", "success"),
    ("rejected",         "已拒绝",     "danger"),
    ("withdrawn",        "已放弃",     "muted"),
]

# 分两行展示：活跃状态 + 终态
active_statuses = STATUS_CONFIG[:6]
terminal_statuses = STATUS_CONFIG[6:]

# 活跃状态行（6 列看板）
cols = st.columns(len(active_statuses))
for col, (status, label, variant) in zip(cols, active_statuses):
    with col:
        rows = query(
            "SELECT id, company, title FROM job_descriptions WHERE status = ? ORDER BY updated_at DESC",
            (status,),
        )
        rows = filter_excluded_rows(rows, company_key="company")
        # 列头：badge + 数量
        st.markdown(
            badge(label, variant) +
            f' <span style="font-size:11px;color:{TEXT_MUTED};margin-left:4px">{len(rows)}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="height:{SP_2}"></div>', unsafe_allow_html=True)
        for r in rows:
            kanban_column_card(r["company"], r["title"])
        if not rows:
            kanban_empty()

# 终态行（已拒/已放弃，折叠显示）
with st.expander(f"终态记录（已拒绝 / 已放弃）", expanded=False):
    t_cols = st.columns(len(terminal_statuses))
    for col, (status, label, variant) in zip(t_cols, terminal_statuses):
        with col:
            rows = query(
                "SELECT id, company, title FROM job_descriptions WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            )
            rows = filter_excluded_rows(rows, company_key="company")
            st.markdown(badge(label, variant) + f' <span style="color:{TEXT_MUTED};font-size:11px">{len(rows)}</span>', unsafe_allow_html=True)
            for r in rows[:5]:
                st.caption(f"{r['company']} — {r['title']}")

# ── 状态更新器 ──────────────────────────────────────────────
divider()
section_title("更新申请状态")

all_jds = query("SELECT id, company, title, status FROM job_descriptions ORDER BY updated_at DESC")
all_jds = filter_excluded_rows(all_jds, company_key="company")
if all_jds:
    jd_map = {f"#{r['id']} — {r['company']} / {r['title']} [{r['status']}]": r["id"] for r in all_jds}
    col_sel, col_status, col_btn = st.columns([4, 3, 1.5])

    with col_sel:
        selected = st.selectbox("选择 JD", list(jd_map.keys()), label_visibility="collapsed")
    with col_status:
        new_status = st.selectbox("新状态", [s[0] for s in STATUS_CONFIG], label_visibility="collapsed",
                                  format_func=lambda x: {s[0]: s[1] for s in STATUS_CONFIG}.get(x, x))
    with col_btn:
        if st.button("更新", type="primary", use_container_width=True):
            execute("UPDATE job_descriptions SET status = ? WHERE id = ?", (new_status, jd_map[selected]))
            alert_success("已更新！")
            st.rerun()
else:
    alert_info("还没有职位描述。")
