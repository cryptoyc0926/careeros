"""Follow-up 多渠道跟进管理 — 紧急度排序 + 话术生成。"""

import streamlit as st
from datetime import datetime
from models.database import query, execute
from services.followup_engine import (
    get_pending_followups, generate_followup_message,
    CHANNEL_LABELS, URGENCY_LEVELS, URGENCY_VARIANT,
)
from components.ui import page_header, badge, divider, soft_stat_card, alert_success, alert_info, alert_warning

page_header("跟进管理", subtitle="该跟进的不会遗漏")

# ── 投递登记 ─────────────────────────────────────────────────
with st.expander("登记新投递", expanded=False):
    # 获取未投递的岗位
    jobs = query(
        "SELECT id, 公司, 岗位名称 FROM jobs_pool WHERE status='NEW' ORDER BY 匹配分 DESC"
    )
    if jobs:
        options = {f"{r['公司']} — {r['岗位名称']}": r for r in jobs}
        sel = st.selectbox("选择岗位", list(options.keys()))
        job = options[sel]

        rc1, rc2 = st.columns(2)
        with rc1:
            channel = st.selectbox("投递渠道", list(CHANNEL_LABELS.keys()),
                                   format_func=lambda x: CHANNEL_LABELS[x])
        with rc2:
            date = st.date_input("投递日期", value=datetime.now())

        if st.button("登记投递", type="primary"):
            execute(
                """UPDATE jobs_pool
                   SET status='已投递', applied_date=?, apply_channel=?,
                       followup_count=0, updated_at=datetime('now','localtime')
                   WHERE id=?""",
                (date.strftime("%Y-%m-%d"), channel, job["id"]),
            )
            alert_success(f"已登记：{job['公司']} — {job['岗位名称']} via {CHANNEL_LABELS[channel]}")
            st.rerun()
    else:
        alert_info("没有待投递的岗位。")

# ── 待跟进列表 ───────────────────────────────────────────────
divider()

pending = get_pending_followups()

if not pending:
    alert_info("暂无待跟进的岗位。投递后会自动出现在这里。")
    st.stop()

# 统计卡片
urgency_counts = {}
for p in pending:
    u = p["urgency"]
    urgency_counts[u] = urgency_counts.get(u, 0) + 1

cols = st.columns(4)
with cols[0]: soft_stat_card(urgency_counts.get("urgent", 0), "紧急")
with cols[1]: soft_stat_card(urgency_counts.get("overdue", 0), "逾期")
with cols[2]: soft_stat_card(urgency_counts.get("upcoming", 0), "即将")
with cols[3]: soft_stat_card(urgency_counts.get("waiting", 0), "等待")

divider()

# 跟进列表
for item in pending:
    job_id = item["id"]
    company = item["公司"]
    position = item["岗位名称"]
    channel = item.get("apply_channel", "")
    count = item.get("followup_count", 0) or 0
    days = item["days_elapsed"]

    with st.container(border=True):
        r1, r2, r3 = st.columns([3, 2, 1.5])
        with r1:
            urgency_badge = badge(item["urgency_label"], URGENCY_VARIANT.get(item.get("urgency"), "muted"))
            st.markdown(f"{urgency_badge} <strong>{company}</strong> — {position}", unsafe_allow_html=True)
            st.caption(
                f"{item.get('城市', '')}　|　"
                f"渠道: {item['channel_label']}　|　"
                f"投递: {item.get('applied_date', '?')}（{days}天前）　|　"
                f"已跟进: {count}次"
            )
        with r2:
            if item["days_until_next"] is not None:
                if item["days_until_next"] <= 0:
                    alert_warning(f"应在 D+{item['next_followup_day']} 跟进（已逾期 {abs(item['days_until_next'])} 天）")
                else:
                    alert_info(f"下次跟进：D+{item['next_followup_day']}（还有 {item['days_until_next']} 天）")
        with r3:
            if st.button("已跟进", key=f"fu_{job_id}"):
                execute(
                    """UPDATE jobs_pool
                       SET followup_count=?, last_followup=?,
                           updated_at=datetime('now','localtime')
                       WHERE id=?""",
                    (count + 1, datetime.now().strftime("%Y-%m-%d"), job_id),
                )
                st.rerun()

        # 话术建议
        msg = generate_followup_message(company, position, channel, count, days)
        st.code(msg, language=None)
