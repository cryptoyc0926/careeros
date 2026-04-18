"""
Career OS — 岗位池页面
展示和管理 jobs_pool 表的数据，支持投递状态跟踪
"""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

# 数据库路径（相对于 web/ 目录）
DB_PATH = Path(__file__).parent.parent / "data" / "career_os.db"


def get_jobs_df() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM jobs_pool ORDER BY match_score DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"数据库读取失败: {e}")
        return pd.DataFrame()


def update_status(job_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE jobs_pool SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
        (status, job_id)
    )
    conn.commit()
    conn.close()
    st.rerun()


def render():
    st.title("📊 岗位池")
    st.caption("数据来源: jobs_pool 表 | 每日由 job-scanner agent 自动更新")

    df = get_jobs_df()
    if df.empty:
        st.info("岗位池暂无数据。运行 job-scanner agent 后刷新页面。")
        return

    active = df[df['status'] != '已排除']

    # ── 顶部统计卡片 ──────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("总岗位", len(active))
    col2.metric("P0岗位", len(active[active['priority'] == 'P0']))
    col3.metric("✅具体链接", len(active[active.get('link_type', pd.Series()).str.contains('✅', na=False)]) if 'link_type' in active.columns else 0)
    col4.metric("已投递", len(df[df['status'] == '已投递']))
    avg_score = active['match_score'].mean() if 'match_score' in active.columns else 0
    col5.metric("平均匹配分", f"{avg_score:.0f}")

    st.divider()

    # ── 筛选工具栏 ────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        priority_filter = st.multiselect("优先级", ['P0', 'P1', 'P2'], default=['P0', 'P1'])
    with col_f2:
        status_filter = st.multiselect("状态", ['NEW', '已投递', '已排除'], default=['NEW'])
    with col_f3:
        show_all = st.checkbox("显示全部", value=False)

    # 应用筛选
    if not show_all:
        filtered = active[
            active['priority'].isin(priority_filter) &
            active['status'].isin(status_filter)
        ]
    else:
        filtered = df

    if filtered.empty:
        st.info("当前筛选条件下无岗位，请调整筛选。")
        return

    # ── 分 Tab 展示 ───────────────────────────────
    tab_list, tab_table = st.tabs(["卡片视图", "表格视图"])

    with tab_list:
        for _, row in filtered.iterrows():
            link_type = row.get('link_type', '🔶') if 'link_type' in row.index else '🔶'
            priority = row.get('priority', 'P2')
            score = row.get('match_score', 0)
            company = row.get('company', '?')
            position = row.get('position', '?')
            city = row.get('city', '')
            apply_url = row.get('apply_url', '') if 'apply_url' in row.index else ''
            referral_code = row.get('referral_code', '') if 'referral_code' in row.index else ''
            action = row.get('action_today', '') if 'action_today' in row.index else ''
            job_id = row.get('id', 0)

            # 优先级颜色
            priority_badge = {'P0': '🔴', 'P1': '🟡', 'P2': '🟢'}.get(priority, '⚪')

            with st.expander(
                f"{link_type} {priority_badge} **{company}** — {position}  |  📍{city}  |  💯{score}分"
            ):
                col_a, col_b = st.columns([3, 1])

                with col_a:
                    if apply_url and str(apply_url) not in ('', 'nan'):
                        if '@' in str(apply_url):
                            st.write(f"📧 **邮件直投**: `{apply_url}`")
                        else:
                            st.write(f"🔗 **链接**: [{str(apply_url)[:70]}...]({apply_url})")

                    if referral_code and str(referral_code) not in ('', 'nan'):
                        st.info(f"🎫 **内推码**: `{referral_code}`  — 投递时务必填写！")

                    if action and str(action) not in ('', 'nan'):
                        st.write(f"📌 **今日行动**: {action}")

                with col_b:
                    status = row.get('status', 'NEW')
                    if status == 'NEW':
                        if st.button("✅ 标记已投递", key=f"apply_{job_id}", use_container_width=True):
                            update_status(job_id, '已投递')
                        if st.button("❌ 排除", key=f"excl_{job_id}", use_container_width=True):
                            update_status(job_id, '已排除')
                    else:
                        st.success(f"状态: {status}")
                        if st.button("↩️ 重置", key=f"reset_{job_id}"):
                            update_status(job_id, 'NEW')

    with tab_table:
        display_cols = [c for c in ['company', 'position', 'city', 'priority', 'match_score',
                                     'link_type', 'status', 'apply_url'] if c in filtered.columns]
        st.dataframe(filtered[display_cols], use_container_width=True, height=500)


render()
