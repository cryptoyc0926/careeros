"""Career OS 首页 — 工作台前厅（Nature × Apple v4）。

结构（Appendix D）：
    A. Hero Intro        —— eyebrow + H1 + subtitle + 2 CTA（上下居中）
    B. 今天的进度        —— 1 主卡 + 3 次卡（叙事式，非平铺）
    C. 接下来做什么      —— 3 张横向任务卡
    D. 优先处理的岗位    —— P0 列表卡（无装饰边框）
    E. 常用入口          —— 1×3 大卡（无图标，带描述；已去重）
"""

import streamlit as st
from models.database import query
from components.ui import (
    hero_intro_block,
    apple_section_heading,
    summary_card_hero,
    soft_stat_card,
    task_action_card,
    feature_card,
    task_list_card,
)

# ═════════════════════════════════════════════════════════════
#  数据查询（与 v3 保持一致，结构改变不影响数据）
# ═════════════════════════════════════════════════════════════
try:
    jp_total   = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE COALESCE(status,'NEW') != '已排除'")[0]["c"]
    jp_p0      = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE 等级='P0' AND COALESCE(status,'NEW') != '已排除'")[0]["c"]
    jp_applied = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE status='已投递'")[0]["c"]
    jp_new     = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE COALESCE(status,'NEW')='NEW'")[0]["c"]
    jd_inter   = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE status='interview'")[0]["c"]
    jd_offer   = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE status='offer'")[0]["c"]
    p0_rows = query(
        "SELECT 公司, 岗位名称, 匹配分 FROM jobs_pool "
        "WHERE 等级='P0' AND COALESCE(status,'NEW')='NEW' "
        "ORDER BY 匹配分 DESC LIMIT 5"
    )
except Exception:
    jp_total = jp_p0 = jp_applied = jp_new = jd_inter = jd_offer = 0
    p0_rows = []


# ═════════════════════════════════════════════════════════════
#  A. Hero Intro（Appendix F.1 文案）
# ═════════════════════════════════════════════════════════════
hero_intro_block(
    eyebrow="Career OS · 2026 春招",
    title="把今天的时间，留给最值得投的岗位",
    subtitle="高优先机会、简历入口和下一步动作，都已经为你排好顺序。",
    primary=("查看今天的优先岗位", "pages/job_pool.py"),
    secondary=("看数据分析", "pages/analytics.py"),
)


# ═════════════════════════════════════════════════════════════
#  B. 今天的进度（叙事式 1 主 + 3 次）
# ═════════════════════════════════════════════════════════════
apple_section_heading("今天的进度")

main_col, side_col = st.columns([1, 1], gap="large")

with main_col:
    if jp_new > 0:
        main_hint = f"其中 {jp_p0} 个是 P0 重点机会" if jp_p0 else "随时处理都可以"
        summary_card_hero(value=jp_new, label="岗位待处理", hint=main_hint)
    else:
        summary_card_hero(value="0", label="全部处理完了",
                          hint="你清空了今天的待办，考虑扫新岗位")

with side_col:
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        soft_stat_card(jp_p0, "P0 岗位")
    with c2:
        soft_stat_card(jp_applied, "已投递")
    with c3:
        soft_stat_card(f"{jd_inter} / {jd_offer}", "面试 / Offer")


# ═════════════════════════════════════════════════════════════
#  C. 接下来做什么（3 张横向任务卡，每张真实入口）
# ═════════════════════════════════════════════════════════════
apple_section_heading("接下来做什么")

t1, t2, t3 = st.columns(3, gap="medium")
with t1:
    task_action_card(
        "处理 P0 岗位",
        f"今天有 {jp_p0} 个重点机会等你处理。" if jp_p0 else "暂时没有 P0 待处理，可扫新岗位。",
        "pages/job_pool.py",
    )
with t2:
    task_action_card(
        "更新主简历",
        "保持底稿最新，所有定制简历都从这里生长。",
        "pages/master_resume.py",
    )
with t3:
    task_action_card(
        "定制目标简历",
        "选一个岗位，把主简历改成更贴近 JD 的版本。",
        "pages/resume_tailor.py",
    )


# ═════════════════════════════════════════════════════════════
#  D. 优先处理的岗位（P0 列表卡）
# ═════════════════════════════════════════════════════════════
apple_section_heading("优先处理的岗位")

p0_items = [
    {
        "label": r["公司"],
        "meta":  r["岗位名称"],
        "score": int(r["匹配分"] or 0),
    }
    for r in p0_rows
]

task_list_card(
    "P0 待行动",
    p0_items,
    empty_text="当前没有 P0 岗位需要处理",
    right_badge=f"{jp_new} 待处理" if jp_new else "",
)

_s, view_col, _s2 = st.columns([3, 2, 3])
with view_col:
    if st.button("查看全部岗位", use_container_width=True, type="primary"):
        st.switch_page("pages/job_pool.py")


# ═════════════════════════════════════════════════════════════
#  E. 常用入口（1×3 大卡网格，无图标）
#     去除与"接下来做什么"重复的岗位池/主简历/跟进管理
# ═════════════════════════════════════════════════════════════
apple_section_heading("常用入口")

cards = [
    ("添加岗位 JD",  "把目标岗位录入系统，后续定制和分析都从这里开始", "pages/jd_input.py"),
    ("浏览 JD 库",   "集中查看已经保存的岗位描述和处理状态",          "pages/jd_browser.py"),
    ("数据分析",     "查看岗位池、投递结果和优先级分布",              "pages/analytics.py"),
]

row = st.columns(3, gap="medium")
for col, (t, d, p) in zip(row, cards):
    with col:
        feature_card(t, d, p)


# ═════════════════════════════════════════════════════════════
#  F. 底部弱信息
# ═════════════════════════════════════════════════════════════
from components.ui import app_footer
app_footer(f"Career OS v0.1.0 · 共 {jp_total} 个岗位")
