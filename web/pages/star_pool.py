"""STAR 素材池 · 审核 + CRUD 页面 (T3)

主要流程：
  1. 顶部「从主简历提取」按钮 → 一次性调 AI 打标签后入 pending 队列
  2. 三个 tab：待审核 / 已批准 / 新增手动
  3. 每条卡片：正文可编辑 / 标签多选 / 影响力选 / 批准-删除-保存
"""

from __future__ import annotations

import sqlite3
import streamlit as st
import json
from pathlib import Path

from config import settings
from services import star_pool
from services.star_pool import (
    StarItem, DIRECTION_TAGS, OUTCOME_TAGS, IMPACT_LEVELS,
    list_items, insert_item, update_item, delete_item,
    extract_from_master, stats,
)
from components.ui import page_header, section_title, divider, soft_stat_card, alert_success, alert_info, alert_danger

DB_PATH = settings.db_full_path


def load_master_dict() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM resume_master ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
    }


page_header("STAR 素材池", subtitle="把经历沉淀成故事，反复复用")

# ── 顶部统计 ───────────────────────────────────────
s = stats()
c1, c2, c3, c4, c5 = st.columns(5)
with c1: soft_stat_card(s["total"], "全部")
with c2: soft_stat_card(s["pending"], "待审核")
with c3: soft_stat_card(s["approved"], "已批准")
with c4: soft_stat_card(s["high"], "高影响")

with c5:
    if st.button("从主简历提取", use_container_width=True, type="primary"):
        master = load_master_dict()
        if not master:
            alert_danger("resume_master 为空")
        else:
            with st.spinner("AI 打标签中（每条 ~1s）..."):
                new_ids = extract_from_master(master, replace=False)
            alert_success(f"新增 {len(new_ids)} 条待审核")
            st.rerun()

divider()

tab_pending, tab_approved, tab_add = st.tabs(
    [f"待审核 ({s['pending']})", f"已批准 ({s['approved']})", "手动新增"]
)


def render_card(it: StarItem, key_prefix: str):
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.caption(f"**{it.source_type}** · {it.source_company or '(手动)'} · id={it.id} · 使用 {it.used_count} 次")
            new_text = st.text_area(
                "bullet 正文",
                value=it.bullet_text,
                height=80,
                key=f"{key_prefix}_text_{it.id}",
                label_visibility="collapsed",
            )
        with c2:
            new_impact = st.selectbox(
                "影响力",
                IMPACT_LEVELS,
                index=IMPACT_LEVELS.index(it.impact) if it.impact in IMPACT_LEVELS else 1,
                key=f"{key_prefix}_impact_{it.id}",
            )

        c3, c4 = st.columns(2)
        with c3:
            new_dir = st.multiselect(
                "岗位方向",
                DIRECTION_TAGS,
                default=[t for t in it.direction_tags if t in DIRECTION_TAGS],
                key=f"{key_prefix}_dir_{it.id}",
            )
        with c4:
            new_out = st.multiselect(
                "成果类型",
                OUTCOME_TAGS,
                default=[t for t in it.outcome_tags if t in OUTCOME_TAGS],
                key=f"{key_prefix}_out_{it.id}",
            )

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("保存", key=f"{key_prefix}_save_{it.id}", use_container_width=True):
                it.bullet_text = new_text
                it.impact = new_impact
                it.direction_tags = new_dir
                it.outcome_tags = new_out
                update_item(it)
                st.toast(f"已保存 #{it.id}")
                st.rerun()
        with b2:
            label = "取消批准" if it.approved else "批准"
            if st.button(label, key=f"{key_prefix}_appr_{it.id}", type="primary", use_container_width=True):
                it.bullet_text = new_text
                it.impact = new_impact
                it.direction_tags = new_dir
                it.outcome_tags = new_out
                it.approved = 0 if it.approved else 1
                update_item(it)
                st.rerun()
        with b3:
            if st.button("删除", key=f"{key_prefix}_del_{it.id}", use_container_width=True):
                delete_item(it.id)
                st.toast(f"已删除 #{it.id}")
                st.rerun()


# ── 待审核 ─────────────────────────────────────────
with tab_pending:
    pending = list_items(approved=0)
    if not pending:
        alert_info("队列空。点顶部「从主简历提取」生成，或手动新增。")
    else:
        for it in pending:
            render_card(it, "pending")

# ── 已批准 ─────────────────────────────────────────
with tab_approved:
    approved = list_items(approved=1)
    if not approved:
        alert_info("还没批准任何素材。")
    else:
        # 过滤器
        fc1, fc2, fc3 = st.columns(3)
        f_dir = fc1.multiselect("按岗位方向筛选", DIRECTION_TAGS, key="filter_dir")
        f_out = fc2.multiselect("按成果类型筛选", OUTCOME_TAGS, key="filter_out")
        f_imp = fc3.multiselect("按影响力筛选", IMPACT_LEVELS, key="filter_imp")

        for it in approved:
            if f_dir and not any(t in it.direction_tags for t in f_dir):
                continue
            if f_out and not any(t in it.outcome_tags for t in f_out):
                continue
            if f_imp and it.impact not in f_imp:
                continue
            render_card(it, "approved")

# ── 手动新增 ───────────────────────────────────────
with tab_add:
    with st.form("add_item_form"):
        txt = st.text_area("bullet 正文（支持 <b>数字</b> HTML）", height=100)
        c1, c2 = st.columns(2)
        src_type = c1.selectbox("来源类型", ["manual", "project", "internship"])
        src_company = c2.text_input("来源公司（可选）")
        c3, c4, c5 = st.columns(3)
        impact = c3.selectbox("影响力", IMPACT_LEVELS, index=1)
        dir_tags = c4.multiselect("岗位方向", DIRECTION_TAGS)
        out_tags = c5.multiselect("成果类型", OUTCOME_TAGS)
        auto_approve = st.checkbox("直接批准（跳过审核）", value=True)

        if st.form_submit_button("新增", type="primary", use_container_width=True):
            if not txt.strip():
                alert_danger("正文不能为空")
            else:
                new_id = insert_item(StarItem(
                    id=None,
                    bullet_text=txt.strip(),
                    source_type=src_type,
                    source_company=src_company,
                    direction_tags=dir_tags,
                    outcome_tags=out_tags,
                    impact=impact,
                    approved=1 if auto_approve else 0,
                    notes="manual",
                ))
                alert_success(f"新增 #{new_id}")
                st.rerun()
