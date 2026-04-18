"""浏览 JD — 表格视图，支持过滤、搜索、详情、AI 解析和删除。"""

import streamlit as st
import json
from models.database import query, execute
from components.ui import page_header, badge, divider, empty_state, alert_success, alert_info, alert_warning, alert_danger

page_header("浏览职位描述", subtitle="查看已抓取的所有 JD")

# ═══════════════════════════════════════════════════════════════
# 过滤器
# ═══════════════════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)

STATUS_CN = {
    "全部": "全部",
    "bookmarked": "已收藏",
    "resume_generated": "已生成简历",
    "applied": "已投递",
    "follow_up": "跟进中",
    "interview": "面试中",
    "offer": "已拿 Offer",
    "rejected": "被拒绝",
    "withdrawn": "已放弃",
}
STATUS_VARIANT = {
    "bookmarked": "muted",
    "resume_generated": "info",
    "applied": "info",
    "follow_up": "warning",
    "interview": "success",
    "offer": "success",
    "rejected": "danger",
    "withdrawn": "muted",
}

with col1:
    status_options = list(STATUS_CN.keys())
    status_filter = st.selectbox("状态", status_options, format_func=lambda x: STATUS_CN[x])
with col2:
    company_filter = st.text_input("公司（模糊搜索）")
with col3:
    channel_filter = st.text_input("渠道类型", placeholder="如：飞书招聘")
with col4:
    sort_by = st.selectbox("排序", ["最新添加", "最早添加", "匹配度 ↓", "公司 A-Z"])

# ═══════════════════════════════════════════════════════════════
# 查询
# ═══════════════════════════════════════════════════════════════
sql = "SELECT id, company, title, location, status, fit_score, source_url, notes, created_at FROM job_descriptions WHERE 1=1"
params = []

if status_filter != "全部":
    sql += " AND status = ?"
    params.append(status_filter)
if company_filter:
    sql += " AND company LIKE ?"
    params.append(f"%{company_filter}%")
if channel_filter:
    sql += " AND notes LIKE ?"
    params.append(f"%{channel_filter}%")

sort_map = {
    "最新添加": "created_at DESC",
    "最早添加": "created_at ASC",
    "匹配度 ↓": "COALESCE(fit_score, 0) DESC",
    "公司 A-Z": "company ASC",
}
sql += f" ORDER BY {sort_map[sort_by]}"

rows = query(sql, tuple(params))

if not rows:
    alert_info("没有找到职位描述。")
    if st.button("前往添加 JD", type="primary"):
        st.switch_page("pages/jd_input.py")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# 表格列表
# ═══════════════════════════════════════════════════════════════
st.caption(f"共 {len(rows)} 条记录")

# 表头
header_cols = st.columns([2.5, 2, 1.5, 1.5, 1, 1.5])
header_cols[0].markdown("**岗位**")
header_cols[1].markdown("**公司**")
header_cols[2].markdown("**渠道类型**")
header_cols[3].markdown("**适配简历**")
header_cols[4].markdown("**状态**")
header_cols[5].markdown("**操作**")
divider()

for row in rows:
    cols = st.columns([2.5, 2, 1.5, 1.5, 1, 1.5])

    # 岗位
    with cols[0]:
        st.markdown(f"**{row['title']}**  \n<span style='font-size:12px;color:#6e6e73'>{row['location'] or ''}</span>", unsafe_allow_html=True)

    # 公司
    with cols[1]:
        st.markdown(row['company'])

    # 渠道类型（从 notes 字段提取）
    with cols[2]:
        notes = row.get("notes", "") or ""
        if "渠道:" in notes:
            channel = notes.split("渠道:")[1].strip().split("\n")[0]
        elif "渠道：" in notes:
            channel = notes.split("渠道：")[1].strip().split("\n")[0]
        elif row.get("source_url"):
            # 根据 URL 推断
            url = row["source_url"]
            if "mokahr.com" in url:
                channel = "官网(Moka)"
            elif "feishu.cn" in url:
                channel = "飞书招聘"
            elif "zhipin.com" in url:
                channel = "Boss直聘"
            elif "lagou.com" in url:
                channel = "拉勾"
            elif "liepin.com" in url:
                channel = "猎聘"
            else:
                channel = "其他"
        else:
            channel = "手动添加"

        st.markdown(
            f'<span style="color:#6e6e73;font-size:13px">{channel}</span>',
            unsafe_allow_html=True,
        )

    # 适配简历（匹配度）
    with cols[3]:
        score = row.get("fit_score")
        if score is not None and score > 0:
            if score >= 70:
                st.markdown(badge(f"{score:.0f}% 高匹配", "success"), unsafe_allow_html=True)
            elif score >= 40:
                st.markdown(badge(f"{score:.0f}% 中等", "warning"), unsafe_allow_html=True)
            else:
                st.markdown(badge(f"{score:.0f}% 较低", "danger"), unsafe_allow_html=True)
        else:
            # 快速关键词匹配
            try:
                from services.jd_scraper import calculate_quick_fit
                jd_row = query("SELECT raw_text FROM job_descriptions WHERE id = ?", (row["id"],))
                if jd_row and jd_row[0]["raw_text"]:
                    quick_score = calculate_quick_fit(jd_row[0]["raw_text"])
                    if quick_score > 0:
                        st.caption(f"~{quick_score:.0f}% (预估)")
                    else:
                        st.caption("待评估")
                else:
                    st.caption("待评估")
            except Exception:
                st.caption("待评估")

    # 状态
    with cols[4]:
        status_label = {
            "bookmarked": "收藏", "resume_generated": "已生成", "applied": "已投递",
            "follow_up": "跟进", "interview": "面试", "offer": "Offer",
            "rejected": "拒绝", "withdrawn": "放弃",
        }.get(row["status"], row["status"])
        st.markdown(badge(status_label, STATUS_VARIANT.get(row["status"], "muted")), unsafe_allow_html=True)

    # 操作
    with cols[5]:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("详情", key=f"v_{row['id']}", help="查看详情"):
                if st.session_state.get("detail_jd_id") == row["id"]:
                    del st.session_state["detail_jd_id"]
                else:
                    st.session_state["detail_jd_id"] = row["id"]
                st.rerun()
        with btn_col2:
            if st.button("删除", key=f"d_{row['id']}", help="删除"):
                st.session_state["confirm_delete_id"] = row["id"]

    # 内联详情面板（紧跟在该行下方展开）
    if st.session_state.get("detail_jd_id") == row["id"]:
        detail = query("SELECT * FROM job_descriptions WHERE id = ?", (row["id"],))
        if detail:
            d = detail[0]
            with st.container(border=True):
                st.markdown(f"##### {d['company']} — {d['title']}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**地点:** {d['location'] or '未知'}")
                    st.markdown(f"**状态:** {STATUS_CN.get(d['status'], d['status'])}")
                    if d['fit_score']:
                        st.markdown(f"**匹配度:** {d['fit_score']}%")
                with col_b:
                    if d['source_url']:
                        url = d['source_url']
                        # 标注链接类型
                        link_label = "直达链接" if any(k in url for k in ["/position/", "/job/", "jobid=", "/apply/", "referral/"]) else "门户入口"
                        st.markdown(f"**来源:** {link_label}  \n[{url[:50]}{'...' if len(url)>50 else ''}]({url})")
                    st.markdown(f"**添加时间:** {d['created_at']}")

                if d.get("parsed_json"):
                    parsed = json.loads(d["parsed_json"])
                    req = parsed.get("skills_required", [])
                    pref = parsed.get("skills_preferred", [])
                    if req:
                        st.markdown(f"**必须技能:** {', '.join(req)}")
                    if pref:
                        st.markdown(f"**加分技能:** {', '.join(pref)}")

                with st.expander("查看 JD 原文"):
                    st.text(d["raw_text"])

                dc1, dc2, dc3 = st.columns(3)
                with dc1:
                    if not d.get("parsed_json"):
                        if st.button("AI 解析", key=f"parse_{row['id']}"):
                            from services.ai_engine import parse_jd, calculate_fit_score, AIError
                            with st.spinner("解析中..."):
                                try:
                                    parsed = parse_jd(d["raw_text"])
                                    if parsed:
                                        fit = calculate_fit_score(parsed)
                                        execute(
                                            "UPDATE job_descriptions SET parsed_json=?, skills_required=?, skills_preferred=?, fit_score=?, experience_min=?, experience_max=? WHERE id=?",
                                            (json.dumps(parsed, ensure_ascii=False),
                                             json.dumps(parsed.get("skills_required", []), ensure_ascii=False),
                                             json.dumps(parsed.get("skills_preferred", []), ensure_ascii=False),
                                             fit, parsed.get("experience_min"), parsed.get("experience_max"), row["id"]),
                                        )
                                        alert_success(f"匹配度: {fit}%")
                                        st.rerun()
                                except AIError as e:
                                    alert_danger(str(e))
                with dc2:
                    if st.button("生成简历", key=f"gen_{row['id']}"):
                        st.session_state["target_jd_id"] = row["id"]
                        st.switch_page("pages/resume_tailor.py")
                with dc3:
                    if st.button("收起", key=f"close_{row['id']}"):
                        del st.session_state["detail_jd_id"]
                        st.rerun()

    divider()


# ═══════════════════════════════════════════════════════════════
# 批量 AI 解析按钮
# ═══════════════════════════════════════════════════════════════
unparsed = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE parsed_json IS NULL")
unparsed_count = unparsed[0]["c"] if unparsed else 0

if unparsed_count > 0:
    divider()
    if st.button(f"批量 AI 解析未评分的 JD（{unparsed_count} 条）", key="batch_parse"):
        unparsed_rows = query("SELECT id, raw_text FROM job_descriptions WHERE parsed_json IS NULL LIMIT 10")
        progress = st.progress(0)
        from services.ai_engine import parse_jd, calculate_fit_score
        for i, r in enumerate(unparsed_rows):
            try:
                parsed = parse_jd(r["raw_text"])
                if parsed:
                    fit = calculate_fit_score(parsed)
                    execute(
                        "UPDATE job_descriptions SET parsed_json=?, skills_required=?, skills_preferred=?, fit_score=?, experience_min=?, experience_max=? WHERE id=?",
                        (json.dumps(parsed, ensure_ascii=False),
                         json.dumps(parsed.get("skills_required", []), ensure_ascii=False),
                         json.dumps(parsed.get("skills_preferred", []), ensure_ascii=False),
                         fit,
                         parsed.get("experience_min"),
                         parsed.get("experience_max"),
                         r["id"]),
                    )
            except Exception as e:
                st.caption(f"JD #{r['id']} 解析失败: {e}")
            progress.progress((i + 1) / len(unparsed_rows))
        alert_success(f"批量解析完成！")
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# 删除确认
# ═══════════════════════════════════════════════════════════════
if "confirm_delete_id" in st.session_state:
    del_id = st.session_state["confirm_delete_id"]
    alert_warning(f"确定要删除 JD #{del_id} 吗？此操作不可撤销。")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("确认删除", key="danger_confirm_del"):
            execute("DELETE FROM job_descriptions WHERE id = ?", (del_id,))
            del st.session_state["confirm_delete_id"]
            alert_success("已删除。")
            st.rerun()
    with c2:
        if st.button("取消"):
            del st.session_state["confirm_delete_id"]
            st.rerun()


# (详情面板已改为内联显示在每行下方)
