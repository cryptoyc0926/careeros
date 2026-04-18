"""岗位池 — 紧凑视图 + 快速操作 + JD录入 + 链接编辑 + 一键处理。"""

import streamlit as st
import pandas as pd
import math
import json
import yaml
from models.database import query, execute, sync_job_to_jd, get_jd_id_for_job, has_resume_for_jd
from config import settings
from components.ui import (
    badge, tier_badge, status_badge, jd_status_badge,
    page_header, section_title, divider, empty_state,
    summary_card_hero, soft_stat_card, apple_section_heading,
    alert_success, alert_info, alert_warning, alert_danger,
    SP_5,
)


# ── 数据加载 ─────────────────────────────────────────────────

@st.cache_data(ttl=5)
def _load_all():
    rows = query("SELECT * FROM jobs_pool ORDER BY 匹配分 DESC")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["status"] = df["status"].fillna("NEW")
    return df


def _apply_filters(df, priorities, statuses, keyword):
    mask = pd.Series(True, index=df.index)
    if priorities:
        mask &= df["等级"].isin(priorities)
    if statuses:
        mask &= df["status"].isin(statuses)
    if keyword:
        kw = keyword.lower()
        mask &= (
            df["公司"].str.lower().str.contains(kw, na=False)
            | df["岗位名称"].str.lower().str.contains(kw, na=False)
            | df["城市"].str.lower().str.contains(kw, na=False)
        )
    return df[mask].reset_index(drop=True)


# ── 页面头 ───────────────────────────────────────────────────

df_all = _load_all()
if df_all.empty:
    empty_state("", "岗位池为空", "运行 job-scanner 添加岗位")
    st.stop()

active = df_all[df_all["status"] != "已排除"]

# 统计已录JD和已生成简历
jd_count = 0
resume_count = 0
for _, r in active.iterrows():
    jd_id = get_jd_id_for_job(r["id"])
    if jd_id:
        jd_count += 1
        if has_resume_for_jd(jd_id):
            resume_count += 1

_n_new   = len(active[active["status"] == "NEW"])
_n_p0    = len(active[active["等级"] == "P0"])
_n_app   = len(df_all[df_all["status"] == "已投递"])

page_header(
    "岗位池",
    subtitle="今天最值得优先处理的岗位都在这里",
    right_text="添加 JD",
    right_page="pages/jd_input.py",
)

# ── 统计（1 主卡 + 5 次卡，与首页一致）────────────────────────
main_col, side_col = st.columns([1, 1.4], gap="large")
with main_col:
    summary_card_hero(
        value=_n_new,
        label="待处理岗位",
        hint=f"共 {len(active)} 个有效岗位" if len(active) else "",
    )
with side_col:
    s1, s2, s3, s4, s5 = st.columns(5, gap="small")
    with s1: soft_stat_card(_n_p0, "P0 重点")
    with s2: soft_stat_card(_n_app, "已投递")
    with s3: soft_stat_card(len(active), "有效岗位")
    with s4: soft_stat_card(jd_count, "已录 JD")
    with s5: soft_stat_card(resume_count, "已生成简历")

st.markdown(f'<div style="height:{SP_5}"></div>', unsafe_allow_html=True)

# ── JD 抓取状态面板 ───────────────────────────────────────
with st.expander("JD 抓取状态", expanded=False):
    mode_counts = active.groupby(["jd_fetch_mode", "jd_status"]).size().to_dict() if "jd_fetch_mode" in active.columns else {}

    def _cnt(mode, status=None):
        if status:
            return mode_counts.get((mode, status), 0)
        return sum(v for (m, _), v in mode_counts.items() if m == mode)

    jc1, jc2, jc3, jc4, jc5 = st.columns(5)
    with jc1: soft_stat_card(_cnt("auto", "fetched"), "已抓")
    with jc2: soft_stat_card(_cnt("auto", "pending"), "auto 待跑")
    with jc3: soft_stat_card(_cnt("browser"), "待 Chrome")
    with jc4: soft_stat_card(_cnt("manual"), "手动")
    with jc5: soft_stat_card(_cnt("blocked"), "黑名单")

    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("重新分类全部", use_container_width=True):
        from services.jd_fetcher import classify_mode
        rows = query('SELECT id, "链接", "公司" FROM jobs_pool')
        for r in rows:
            mode = classify_mode(r.get("链接") or "", r.get("公司") or "")
            execute("UPDATE jobs_pool SET jd_fetch_mode=? WHERE id=?", (mode, r["id"]))
        st.cache_data.clear()
        alert_success("已重新分类")
        st.rerun()

    if bc2.button("抓取 auto 队列", use_container_width=True, type="primary"):
        from services.jd_fetcher import fetch_and_save
        pending = query(
            """SELECT id, "链接" AS url, "公司" AS company, "岗位名称" AS title FROM jobs_pool
               WHERE jd_fetch_mode='auto'
                 AND (jd_status IS NULL OR jd_status IN ('pending','failed'))
                 AND "链接" LIKE 'http%'
               ORDER BY id DESC LIMIT 20"""
        )
        if not pending:
            alert_info("auto 队列空")
        else:
            prog = st.progress(0, text=f"正在抓 {len(pending)} 条...")
            ok = fail = 0
            for i, r in enumerate(pending, 1):
                try:
                    res = fetch_and_save(r["id"], r["url"])
                    if res.ok:
                        ok += 1
                    else:
                        fail += 1
                except Exception:
                    fail += 1
                prog.progress(i / len(pending), text=f"{i}/{len(pending)} · 成功 {ok} 失败 {fail}")
            st.cache_data.clear()
            alert_success(f"完成 · 成功 {ok} · 失败 {fail}")
            st.rerun()

    if bc3.button("Chrome 抓取提示", use_container_width=True):
        browser_rows = query(
            """SELECT id, "公司" AS company, "岗位名称" AS title, "链接" AS url
               FROM jobs_pool WHERE jd_fetch_mode='browser' AND (jd_status='pending' OR jd_status IS NULL)
               ORDER BY id DESC LIMIT 10"""
        )
        if browser_rows:
            alert_info(
                "需 Chrome MCP 的 10 条（复制下方清单到 Claude 对话里，让我批量抓）：\n\n"
                + "\n".join(f"- #{r['id']} {r['company']} / {r['title']} — {r['url']}" for r in browser_rows)
            )
        else:
            alert_info("browser 队列空")

# ── 筛选栏 ──────────────────────────────────────────────────

fc1, fc2, fc3 = st.columns([2, 2, 3])
with fc1:
    sel_pri = st.multiselect("优先级", ["P0", "P1", "P2"], default=["P0", "P1", "P2"], key="fp")
with fc2:
    sel_sta = st.multiselect("状态", ["NEW", "已投递", "已排除"], default=["NEW", "已投递"], key="fs")
with fc3:
    search = st.text_input("搜索公司/岗位/城市", key="fk", placeholder="如：MiniMax、增长、上海")

df = _apply_filters(df_all, sel_pri, sel_sta, search)

if df.empty:
    alert_info("当前筛选无结果。")
    st.stop()

# ── 分页 ─────────────────────────────────────────────────────

PAGE_SIZE = 20
total_pages = max(1, math.ceil(len(df) / PAGE_SIZE))

vc1, vc2, vc3 = st.columns([2, 4, 2])
with vc1:
    view = st.radio("视图", ["紧凑列表", "表格"], horizontal=True, label_visibility="collapsed")
with vc3:
    page = st.number_input(f"页码 (共{total_pages}页·{len(df)}条)", min_value=1, max_value=total_pages, value=1, key="page")

start = (page - 1) * PAGE_SIZE
end = min(start + PAGE_SIZE, len(df))
df_page = df.iloc[start:end]

# ── 紧凑列表视图 ────────────────────────────────────────────

if view == "紧凑列表":
    for _, row in df_page.iterrows():
        job_id = row["id"]
        company = row.get("公司", "")
        position = row.get("岗位名称", "")
        city = row.get("城市", "")
        priority = row.get("等级", "")
        score = row.get("匹配分", 0)
        link = row.get("链接", "")
        action = row.get("今日行动", "")
        status = row.get("status", "NEW")
        link_type = row.get("link_type", "🔶门户")

        # 检查是否已录JD
        jd_id = get_jd_id_for_job(job_id)
        has_jd = jd_id is not None
        has_resume = has_resume_for_jd(jd_id) if has_jd else False

        pri_variant = {"P0": "danger", "P1": "warning", "P2": "success"}.get(priority, "muted")

        with st.container(border=True):
            # 主信息行
            r1, r2, r3, r4, r5 = st.columns([3, 0.6, 1, 1.2, 0.8])
            with r1:
                # 状态徽章
                badges_html = badge(priority or "—", pri_variant) + f" <strong>{company}</strong> — {position}"
                if has_resume:
                    badges_html += " " + badge("已生成简历", "success")
                elif has_jd:
                    badges_html += " " + badge("已录 JD", "info")
                cred = row.get("credibility", "")
                if cred and "高" in cred:
                    badges_html += " " + badge("可信度高", "success")
                elif cred and "低" in cred:
                    badges_html += " " + badge("可信度低", "danger")
                st.markdown(badges_html, unsafe_allow_html=True)
                st.caption(f"{city}　{link_type}　分数:{int(score) if score else 0}")
            with r2:
                if link:
                    st.markdown(f"[打开]({link})")
            with r3:
                if action:
                    short = action[:30] + "…" if len(action) > 30 else action
                    st.caption(short)
            with r4:
                # 操作按钮
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if status == "NEW":
                        if st.button("标记已投递", key=f"a{job_id}", help="把状态改成「已投递」"):
                            execute("UPDATE jobs_pool SET status='已投递', updated_at=datetime('now','localtime') WHERE id=?", (job_id,))
                            st.cache_data.clear()
                            st.rerun()
                    elif status == "已投递":
                        if st.button("取消投递", key=f"r{job_id}", help="撤回投递状态"):
                            execute("UPDATE jobs_pool SET status='NEW', updated_at=datetime('now','localtime') WHERE id=?", (job_id,))
                            st.cache_data.clear()
                            st.rerun()
                with bc2:
                    if status != "已排除":
                        if st.button("排除", key=f"x{job_id}", help="不想投递这个岗位"):
                            execute("UPDATE jobs_pool SET status='已排除', updated_at=datetime('now','localtime') WHERE id=?", (job_id,))
                            st.cache_data.clear()
                            st.rerun()
                with bc3:
                    if not has_jd:
                        if st.button("录入 JD", key=f"jd{job_id}", help="粘贴职位描述原文"):
                            st.session_state[f"show_jd_input_{job_id}"] = True
                    elif not has_resume:
                        if st.button("生成简历", key=f"gen{job_id}", help="AI 按此 JD 定制简历"):
                            st.session_state["target_jd_id"] = jd_id
                            st.switch_page("pages/generate.py")
                    elif has_resume:
                        st.caption("已完成")
            with r5:
                # 一键处理 — 始终可见
                if has_resume:
                    st.caption("已生成")
                else:
                    if st.button("一键处理", key=f"pipe{job_id}", help="粘贴JD→解析→打分→生成简历→PDF", type="primary"):
                        if has_jd:
                            st.session_state[f"run_pipeline_{job_id}"] = True
                        else:
                            st.session_state[f"show_jd_input_{job_id}"] = True
                            st.session_state[f"auto_pipeline_{job_id}"] = True

            # JD 录入展开区
            if st.session_state.get(f"show_jd_input_{job_id}"):
                auto_mode = st.session_state.get(f"auto_pipeline_{job_id}", False)
                label = f"粘贴 {company} - {position} 的 JD 原文" + ("（粘贴后点一键处理）" if auto_mode else "")
                jd_text = st.text_area(
                    label,
                    height=150, key=f"jdtext_{job_id}",
                    placeholder="从招聘网站复制 JD 全文粘贴到这里..."
                )
                jd_c1, jd_c2, jd_c3 = st.columns(3)
                with jd_c1:
                    if st.button("仅保存 JD", key=f"savejd_{job_id}"):
                        if jd_text and len(jd_text.strip()) > 20:
                            new_jd_id = sync_job_to_jd(job_id, jd_text.strip())
                            alert_success(f"已录入！JD #{new_jd_id}")
                            st.session_state.pop(f"show_jd_input_{job_id}", None)
                            st.session_state.pop(f"auto_pipeline_{job_id}", None)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            alert_warning("JD 内容太短，请粘贴完整的职位描述。")
                with jd_c2:
                    if st.button("保存并一键处理", key=f"savepipe_{job_id}", type="primary"):
                        if jd_text and len(jd_text.strip()) > 20:
                            new_jd_id = sync_job_to_jd(job_id, jd_text.strip())
                            st.session_state.pop(f"show_jd_input_{job_id}", None)
                            st.session_state.pop(f"auto_pipeline_{job_id}", None)
                            st.cache_data.clear()
                            # 直接在这里跑 pipeline，不 rerun（避免 session 丢失）
                            resume_path = settings.master_resume_full_path
                            if not resume_path.exists():
                                alert_danger("主简历文件不存在，请先在「主简历」页面创建。")
                            else:
                                resume_data = yaml.safe_load(resume_path.read_text(encoding="utf-8"))
                                if not resume_data or not resume_data.get("experience"):
                                    alert_danger("主简历内容为空或缺少工作经历。")
                                else:
                                    jd_clean = jd_text.strip()
                                    with st.spinner(f"一键处理中：{company} - {position}（解析JD → 打分 → 生成简历，约30秒）..."):
                                        try:
                                            from services.ai_engine import auto_pipeline, AIError
                                            result = auto_pipeline(jd_raw_text=jd_clean, resume_data=resume_data)
                                            if "error" in result:
                                                alert_danger(result["error"])
                                            else:
                                                jd_parsed = result["jd_parsed"]
                                                execute(
                                                    "UPDATE job_descriptions SET parsed_json=?, fit_score=?, status='resume_generated' WHERE id=?",
                                                    (json.dumps(jd_parsed, ensure_ascii=False), result["fit_score"], new_jd_id),
                                                )
                                                version = query(
                                                    "SELECT COALESCE(MAX(version),0)+1 as v FROM generated_resumes WHERE jd_id=?",
                                                    (new_jd_id,)
                                                )[0]["v"]
                                                execute(
                                                    """INSERT INTO generated_resumes (jd_id, resume_md, cover_letter_md, achievements_used, model_used, prompt_hash, version)
                                                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                                    (new_jd_id, result["resume_md"], result.get("cover_letter_md", ""),
                                                     json.dumps(result.get("achievements_used", []), ensure_ascii=False),
                                                     settings.claude_model, result.get("prompt_hash", ""), version),
                                                )
                                                alert_success(f"完成！匹配分: {result['fit_score']}%，简历 v{version} 已保存")
                                                with st.expander("查看生成的简历", expanded=True):
                                                    st.markdown(result["resume_md"])
                                                    try:
                                                        from services.pdf_export import markdown_to_pdf
                                                        pdf_path = markdown_to_pdf(result["resume_md"])
                                                        with open(pdf_path, "rb") as f:
                                                            st.download_button(
                                                                "下载 PDF",
                                                                data=f.read(),
                                                                file_name=f"{company}_{position}_简历.pdf",
                                                                mime="application/pdf",
                                                                key=f"pdf_new_{job_id}",
                                                            )
                                                    except Exception as e:
                                                        st.caption(f"PDF 导出失败: {e}")
                                                if result.get("cover_letter_md"):
                                                    with st.expander("求职信"):
                                                        st.markdown(result["cover_letter_md"])
                                                st.cache_data.clear()
                                        except Exception as e:
                                            alert_danger(f"一键处理失败: {e}")
                        else:
                            alert_warning("JD 内容太短，请粘贴完整的职位描述。")
                with jd_c3:
                    if st.button("取消", key=f"canceljd_{job_id}"):
                        st.session_state.pop(f"show_jd_input_{job_id}", None)
                        st.session_state.pop(f"auto_pipeline_{job_id}", None)
                        st.rerun()

            # 一键处理流程
            if st.session_state.get(f"run_pipeline_{job_id}"):
                if not has_jd:
                    alert_warning("请先录入 JD 再使用一键处理。")
                    del st.session_state[f"run_pipeline_{job_id}"]
                else:
                    # 读取 JD 原文
                    jd_row = query("SELECT raw_text FROM job_descriptions WHERE id=?", (jd_id,))
                    if jd_row and jd_row[0]["raw_text"]:
                        resume_path = settings.master_resume_full_path
                        if not resume_path.exists():
                            alert_danger("主简历文件不存在，请先在「主简历」页面创建。")
                        else:
                            resume_data = yaml.safe_load(resume_path.read_text(encoding="utf-8"))
                            if not resume_data or not resume_data.get("experience"):
                                alert_danger("主简历内容为空或缺少工作经历。")
                            else:
                                with st.spinner(f"一键处理中：{company} - {position}（解析JD → 打分 → 生成简历，约30秒）..."):
                                    try:
                                        from services.ai_engine import auto_pipeline, AIError
                                        result = auto_pipeline(
                                            jd_raw_text=jd_row[0]["raw_text"],
                                            resume_data=resume_data,
                                        )
                                        if "error" in result:
                                            alert_danger(result["error"])
                                        else:
                                            # 保存解析结果
                                            jd_parsed = result["jd_parsed"]
                                            execute(
                                                "UPDATE job_descriptions SET parsed_json=?, fit_score=?, status='resume_generated' WHERE id=?",
                                                (json.dumps(jd_parsed, ensure_ascii=False), result["fit_score"], jd_id),
                                            )
                                            # 保存简历
                                            version = query(
                                                "SELECT COALESCE(MAX(version),0)+1 as v FROM generated_resumes WHERE jd_id=?",
                                                (jd_id,)
                                            )[0]["v"]
                                            execute(
                                                """INSERT INTO generated_resumes (jd_id, resume_md, cover_letter_md, achievements_used, model_used, prompt_hash, version)
                                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                                (jd_id, result["resume_md"], result.get("cover_letter_md", ""),
                                                 json.dumps(result.get("achievements_used", []), ensure_ascii=False),
                                                 settings.claude_model, result.get("prompt_hash", ""), version),
                                            )
                                            alert_success(f"完成！匹配分: {result['fit_score']}%，简历 v{version} 已保存")

                                            # 展示简历 + PDF 下载
                                            with st.expander("查看生成的简历", expanded=True):
                                                st.markdown(result["resume_md"])
                                                try:
                                                    from services.pdf_export import markdown_to_pdf
                                                    pdf_path = markdown_to_pdf(result["resume_md"])
                                                    with open(pdf_path, "rb") as f:
                                                        st.download_button(
                                                            "下载 PDF",
                                                            data=f.read(),
                                                            file_name=f"{company}_{position}_简历.pdf",
                                                            mime="application/pdf",
                                                            key=f"pdf_{job_id}",
                                                        )
                                                except Exception as e:
                                                    st.caption(f"PDF 导出失败: {e}")

                                            if result.get("cover_letter_md"):
                                                with st.expander("求职信"):
                                                    st.markdown(result["cover_letter_md"])

                                            st.cache_data.clear()
                                    except Exception as e:
                                        alert_danger(f"一键处理失败: {e}")
                    else:
                        alert_danger("JD 原文为空。")
                    if f"run_pipeline_{job_id}" in st.session_state:
                        del st.session_state[f"run_pipeline_{job_id}"]

            # 链接编辑展开区
            if st.session_state.get(f"show_edit_{job_id}"):
                new_link = st.text_input("更新链接", value=link, key=f"editlink_{job_id}")
                new_action = st.text_input("更新今日行动", value=action or "", key=f"editact_{job_id}")
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("保存", key=f"savedit_{job_id}"):
                        # 自动推断 link_type
                        lt = "🔶门户"
                        nl = (new_link or "").lower()
                        if nl.startswith("mailto:") or ("@" in nl and "/" not in nl):
                            lt = "📧邮件"
                        elif any(p in nl for p in ["/job/", "/jobs/", "/position/", "jobid=", "/apply/", "linkedin.com/jobs/view/"]):
                            lt = "直达"
                        elif "feishu.cn/s/" in nl:
                            lt = "🔶内推入口"
                        execute(
                            "UPDATE jobs_pool SET 链接=?, 今日行动=?, link_type=?, updated_at=datetime('now','localtime') WHERE id=?",
                            (new_link, new_action, lt, job_id),
                        )
                        del st.session_state[f"show_edit_{job_id}"]
                        st.cache_data.clear()
                        st.rerun()
                with ec2:
                    if st.button("取消", key=f"canceldit_{job_id}"):
                        del st.session_state[f"show_edit_{job_id}"]
                        st.rerun()

    # 底部工具栏
    divider()
    tb1, tb2, tb3, tb4 = st.columns(4)
    with tb1:
        if st.button("编辑模式", key="toggle_edit"):
            for _, row in df_page.iterrows():
                st.session_state[f"show_edit_{row['id']}"] = not st.session_state.get(f"show_edit_{row['id']}", False)
            st.rerun()
    with tb2:
        if st.button("批量 Ghost 检测", key="batch_ghost"):
            st.session_state["show_ghost_batch"] = True
    with tb3:
        if st.button("消息模板", key="show_outreach"):
            st.session_state["show_outreach"] = True
    with tb4:
        st.caption(f"第 {start+1}–{end} 条，共 {len(df)} 条")

    # Ghost Job 批量检测面板
    if st.session_state.get("show_ghost_batch"):
        st.markdown("---")
        st.markdown("##### Ghost Job 批量检测")
        ghost_jobs = [r for _, r in df_page.iterrows() if get_jd_id_for_job(r["id"])]
        if not ghost_jobs:
            alert_info("当前页面没有已录入JD的岗位，请先录入JD。")
        else:
            sel_ghost = st.multiselect(
                "选择要检测的岗位",
                [f"{r['公司']} — {r['岗位名称']}" for r in ghost_jobs],
                default=[f"{r['公司']} — {r['岗位名称']}" for r in ghost_jobs[:5]],
                key="ghost_sel",
            )
            if st.button("开始检测", key="run_ghost"):
                from services.ai_engine import ghost_check
                for label in sel_ghost:
                    matched = [r for r in ghost_jobs if f"{r['公司']} — {r['岗位名称']}" == label]
                    if not matched:
                        continue
                    r = matched[0]
                    jd_id = get_jd_id_for_job(r["id"])
                    jd_row = query("SELECT raw_text FROM job_descriptions WHERE id=?", (jd_id,))
                    if not jd_row or not jd_row[0]["raw_text"]:
                        continue
                    with st.spinner(f"检测 {r['公司']}..."):
                        try:
                            result = ghost_check(jd_row[0]["raw_text"], r["公司"])
                            cred_map = {"高": "高", "中": "中", "低": "低"}
                            cred = cred_map.get(result.get("credibility", "中"), "中")
                            execute(
                                "UPDATE jobs_pool SET credibility=?, updated_at=datetime('now','localtime') WHERE id=?",
                                (cred, r["id"]),
                            )
                            risk = result.get("risk_type", "未知")
                            signals = "、".join(result.get("signals", []))
                            st.markdown(f"**{r['公司']}**: {cred} — {risk}　({signals})")
                        except Exception as e:
                            alert_warning(f"{r['公司']}: 检测失败 ({e})")
                st.cache_data.clear()

        if st.button("关闭", key="close_ghost"):
            del st.session_state["show_ghost_batch"]
            st.rerun()

    # 消息模板面板
    if st.session_state.get("show_outreach"):
        st.markdown("---")
        st.markdown("##### 消息模板生成")
        from services.outreach_templates import get_all_templates
        active_jobs = df_page[df_page["status"] != "已排除"]
        sel_company = st.selectbox(
            "选择公司",
            active_jobs["公司"].unique().tolist(),
            key="outreach_company",
        )
        job_for_company = active_jobs[active_jobs["公司"] == sel_company].iloc[0]
        position_name = job_for_company["岗位名称"]

        templates = get_all_templates(sel_company, position_name)

        ot1, ot2 = st.columns(2)
        with ot1:
            st.markdown("**Boss直聘**")
            for i, msg in enumerate(templates["boss"]):
                st.code(msg, language=None)
            st.markdown("**脉脉**")
            for msg in templates["maimai"]:
                st.code(msg, language=None)
        with ot2:
            st.markdown("**邮件**")
            for msg in templates["email"]:
                st.code(msg, language=None)
            st.markdown("**内推请求**")
            for msg in templates["referral"]:
                st.code(msg, language=None)

        if st.button("关闭", key="close_outreach"):
            del st.session_state["show_outreach"]
            st.rerun()

# ── 表格视图 ─────────────────────────────────────────────────

else:
    display_cols = ["公司", "岗位名称", "城市", "等级", "匹配分", "link_type",
                    "链接", "今日行动", "status", "方向分类", "来源平台", "招聘类型"]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "链接": st.column_config.LinkColumn("链接", display_text="打开", width="small"),
            "匹配分": st.column_config.NumberColumn("匹配分", format="%.0f", width="small"),
            "等级": st.column_config.TextColumn("等级", width="small"),
            "link_type": st.column_config.TextColumn("链接类型", width="small"),
            "status": st.column_config.TextColumn("状态", width="small"),
        },
    )
