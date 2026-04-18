"""AI 简历生成 — 选择 JD，一键生成定制简历和求职信。"""

import streamlit as st
import yaml
import json
from config import settings
from models.database import query, execute
from components.ui import page_header, section_title, divider, empty_state_rich, apple_section_heading, alert_success, alert_info, alert_warning, alert_danger

page_header(
    "AI 简历生成",
    subtitle="选一个岗位，我来为你调整措辞和经历顺序",
    right_text="主简历",
    right_page="pages/master_resume.py",
)

if not settings.has_anthropic_key:
    empty_state_rich(
        title="还没配置 API",
        description="AI 生成简历需要连接 Claude API。\n去设置里填入 Key，之后会自动记住。",
        primary_action=("前往设置", "pages/settings_page.py"),
    )
    st.stop()

# ── 检查主简历 ──────────────────────────────────────────────
resume_path = settings.master_resume_full_path
if not resume_path.exists():
    empty_state_rich(
        title="还没有主简历",
        description="AI 生成定制简历需要一份底稿。\n几分钟就能完成，之后所有定制版本都基于它。",
        primary_action=("创建主简历", "pages/master_resume.py"),
    )
    st.stop()

resume_data = yaml.safe_load(resume_path.read_text(encoding="utf-8"))
if not resume_data or not resume_data.get("experience"):
    empty_state_rich(
        title="主简历还不完整",
        description="底稿需要至少一段工作经历，AI 才能据此定制。\n去主简历页面补完后再回来。",
        primary_action=("完善主简历", "pages/master_resume.py"),
    )
    st.stop()

# ── JD 选择 ─────────────────────────────────────────────────
jds = query("SELECT id, company, title, raw_text, parsed_json, fit_score FROM job_descriptions ORDER BY created_at DESC")
if not jds:
    empty_state_rich(
        title="还没有目标岗位",
        description="先添加一个岗位描述，AI 会基于它调整你的简历。",
        primary_action=("添加 JD", "pages/jd_input.py"),
    )
    st.stop()

# 标注来源（从岗位池同步的 vs 手动添加的）
jd_options = {}
for r in jds:
    src = "岗位池" if r.get("notes") and "岗位池#" in r["notes"] else "手动"
    label = f"[{src}] #{r['id']} — {r['company']} / {r['title']}" + (f" (匹配 {r['fit_score']}%)" if r['fit_score'] else "")
    jd_options[label] = r

# 如果从岗位池跳转过来，预选对应JD
preselect_idx = 0
target_jd = st.session_state.pop("target_jd_id", None)
if target_jd:
    for i, (_, r) in enumerate(jd_options.items()):
        if r["id"] == target_jd:
            preselect_idx = i
            break

selected_label = st.selectbox("选择目标职位", list(jd_options.keys()), index=preselect_idx)
selected_jd = jd_options[selected_label]

# ── 显示 JD 匹配信息 ────────────────────────────────────────
if selected_jd["fit_score"]:
    score = selected_jd["fit_score"]
    color = "green" if score >= 70 else "orange" if score >= 40 else "red"
    st.markdown(f"匹配度: :{color}[**{score}%**]")

if selected_jd["parsed_json"]:
    parsed = json.loads(selected_jd["parsed_json"])
    skills_req = parsed.get("skills_required", [])
    if skills_req:
        st.caption(f"要求技能: {', '.join(skills_req[:10])}")

# ── 生成选项 ────────────────────────────────────────────────
with st.expander("高级选项", expanded=False):
    temperature = st.slider("创造性（温度）", 0.3, 1.0, 0.7, 0.05,
                            help="越高越有创意，越低越保守稳定")
    include_cover = st.checkbox("同时生成求职信", value=True)

# ── 生成按钮 ────────────────────────────────────────────────
if st.button("生成定制简历", type="primary", use_container_width=True):
    from services.ai_engine import generate_tailored_resume, parse_jd, calculate_fit_score

    jd_raw = selected_jd["raw_text"]

    from services.ai_engine import AIError

    # 如果还没解析过 JD，先解析
    if selected_jd["parsed_json"]:
        jd_parsed = json.loads(selected_jd["parsed_json"])
    else:
        with st.spinner("正在解析职位描述..."):
            try:
                jd_parsed = parse_jd(jd_raw)
            except AIError as e:
                alert_danger(f"JD 解析失败：{e}")
                st.stop()
            except Exception as e:
                alert_danger(f"JD 解析异常：{e}")
                st.stop()
            if jd_parsed:
                fit = calculate_fit_score(jd_parsed)
                execute(
                    "UPDATE job_descriptions SET parsed_json=?, skills_required=?, skills_preferred=?, fit_score=?, experience_min=?, experience_max=? WHERE id=?",
                    (json.dumps(jd_parsed, ensure_ascii=False),
                     json.dumps(jd_parsed.get("skills_required", []), ensure_ascii=False),
                     json.dumps(jd_parsed.get("skills_preferred", []), ensure_ascii=False),
                     fit,
                     jd_parsed.get("experience_min"),
                     jd_parsed.get("experience_max"),
                     selected_jd["id"]),
                )

    # 生成简历
    with st.spinner("正在调用 Claude 生成定制简历（约 15-30 秒，如代理较慢可能更久）..."):
        try:
            result = generate_tailored_resume(
                jd_raw_text=jd_raw,
                jd_parsed=jd_parsed,
                resume_data=resume_data,
                temperature=temperature,
                include_cover_letter=include_cover,
            )
        except AIError as e:
            alert_danger(str(e))
            alert_info("如果持续失败，可以在「设置」页面更换 API 端点或检查 Key 是否有效。")
            st.stop()
        except Exception as e:
            alert_danger(f"生成失败: {e}")
            st.stop()

    if "error" in result:
        alert_danger(result["error"])
        st.stop()

    # 保存到数据库
    version = query(
        "SELECT COALESCE(MAX(version), 0) + 1 as v FROM generated_resumes WHERE jd_id = ?",
        (selected_jd["id"],)
    )[0]["v"]

    resume_id = execute(
        """INSERT INTO generated_resumes (jd_id, resume_md, cover_letter_md, achievements_used, model_used, prompt_hash, version)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (selected_jd["id"],
         result["resume_md"],
         result.get("cover_letter_md", ""),
         json.dumps(result.get("achievements_used", []), ensure_ascii=False),
         settings.claude_model,
         result.get("prompt_hash", ""),
         version),
    )

    # 更新 JD 状态
    execute("UPDATE job_descriptions SET status = 'resume_generated' WHERE id = ? AND status = 'bookmarked'",
            (selected_jd["id"],))

    alert_success(f"简历已生成！版本 v{version}，已保存。")

    # 展示结果
    tab_resume, tab_cover, tab_eval = st.tabs(["定制简历", "求职信", "深度评估"])

    with tab_resume:
        st.markdown(result["resume_md"])
        # PDF 下载
        try:
            from services.pdf_export import markdown_to_pdf
            pdf_path = markdown_to_pdf(result["resume_md"])
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "下载 PDF 简历",
                    data=f.read(),
                    file_name=f"{selected_jd['company']}_{selected_jd['title']}_简历.pdf",
                    mime="application/pdf",
                )
        except Exception as e:
            st.caption(f"PDF 导出失败: {e}（请确认已安装 weasyprint）")

    with tab_cover:
        if result.get("cover_letter_md"):
            st.markdown(result["cover_letter_md"])
        else:
            alert_info("未生成求职信。")

    with tab_eval:
        # 深度评估
        with st.spinner("正在生成 5 段式深度评估..."):
            try:
                from services.ai_engine import deep_evaluate
                resume_summary = yaml.dump(resume_data, allow_unicode=True, default_flow_style=False)[:3000]
                eval_md = deep_evaluate(jd_raw, resume_summary)
                st.markdown(eval_md)
            except Exception as e:
                alert_warning(f"深度评估生成失败: {e}")

# ── 历史版本 ────────────────────────────────────────────────
divider()
apple_section_heading("历史生成记录")

history = query(
    """SELECT gr.id, gr.jd_id, gr.version, gr.model_used, gr.created_at,
              jd.company, jd.title
       FROM generated_resumes gr
       JOIN job_descriptions jd ON gr.jd_id = jd.id
       ORDER BY gr.created_at DESC LIMIT 20"""
)

if history:
    for row in history:
        with st.expander(f"v{row['version']} — {row['company']} / {row['title']}  ({row['created_at'][:10]})"):
            full = query("SELECT resume_md, cover_letter_md FROM generated_resumes WHERE id = ?", (row["id"],))
            if full:
                st.markdown(full[0]["resume_md"])
                if full[0]["cover_letter_md"]:
                    divider()
                    st.markdown("**求职信:**")
                    st.markdown(full[0]["cover_letter_md"])
else:
    st.caption("暂无生成记录。")
