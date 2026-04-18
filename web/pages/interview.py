"""面试准备 — 模拟面试题 + 公司速查表（合并页面）。"""

import streamlit as st
import json
import yaml
from config import settings
from models.database import query, execute
from components.ui import page_header, section_title, divider, empty_state_rich, alert_success, alert_danger

page_header(
    "模拟面试 & 速查表",
    subtitle="用 AI 模拟面试，也把公司情报准备好",
    right_text="题库",
    right_page="pages/interview_prep.py",
)

if not settings.has_anthropic_key:
    empty_state_rich(
        title="还没配置 API",
        description="面试模拟需要连接 Claude API。\n去设置里填入 Key，之后会自动记住。",
        primary_action=("前往设置", "pages/settings_page.py"),
    )
    st.stop()

# ── JD 选择 ─────────────────────────────────────────────────
jds = query("SELECT id, company, title, raw_text FROM job_descriptions ORDER BY created_at DESC")
if not jds:
    empty_state_rich(
        title="准备面试前，先选一个岗位",
        description="模拟面试和公司速查都会基于这个岗位定制。",
        primary_action=("添加 JD", "pages/jd_input.py"),
    )
    st.stop()

jd_options = {f"#{r['id']} — {r['company']} / {r['title']}": r for r in jds}
selected_label = st.selectbox("选择目标职位", list(jd_options.keys()))
selected_jd = jd_options[selected_label]

# ── 加载简历摘要 ────────────────────────────────────────────
resume_path = settings.master_resume_full_path
resume_summary = ""
if resume_path.exists():
    data = yaml.safe_load(resume_path.read_text(encoding="utf-8"))
    if data:
        meta = data.get("meta", {})
        exps = []
        for exp in data.get("experience", []):
            top_ach = [a["text"] for a in exp.get("achievements", [])[:3]]
            exps.append(f"{exp.get('title','')} @ {exp.get('company','')}：{'；'.join(top_ach)}")
        skills_flat = []
        for items in data.get("skills", {}).values():
            skills_flat.extend(items)
        resume_summary = f"姓名: {meta.get('name','')}\n技能: {', '.join(skills_flat[:15])}\n经历: " + "\n".join(exps)

# ── 两个功能 Tab ────────────────────────────────────────────
tab_questions, tab_cheatsheet = st.tabs(["模拟面试", "公司速查"])

# ── 模拟面试题 ──────────────────────────────────────────────
with tab_questions:
    st.markdown("根据 JD 和你的简历，生成针对性的面试题和答题框架。")

    # 查看已有记录
    existing = query("SELECT questions_json, created_at FROM interview_prep WHERE jd_id = ? ORDER BY created_at DESC LIMIT 1",
                     (selected_jd["id"],))

    if st.button("生成面试准备", type="primary", key="gen_questions"):
        from services.ai_engine import generate_interview_prep
        with st.spinner("正在生成面试题（约 20-30 秒）..."):
            try:
                result = generate_interview_prep(
                    jd_raw_text=selected_jd["raw_text"],
                    resume_summary=resume_summary,
                    company=selected_jd["company"],
                )
            except Exception as e:
                alert_danger(f"生成失败: {e}")
                result = None

        if result and "error" not in result:
            # 保存
            execute(
                "INSERT INTO interview_prep (jd_id, questions_json) VALUES (?, ?)",
                (selected_jd["id"], json.dumps(result, ensure_ascii=False)),
            )
            alert_success("面试准备材料已生成并保存！")
            existing = [{"questions_json": json.dumps(result, ensure_ascii=False)}]
        elif result:
            alert_danger(result.get("error", "未知错误"))

    # 展示结果
    if existing and existing[0]["questions_json"]:
        qdata = json.loads(existing[0]["questions_json"])
        categories = {
            "technical": "技术深度题",
            "behavioral": "行为面试题 (STAR)",
            "system_design": "系统设计题",
            "culture_fit": "文化匹配题",
            "reverse_interview": "反向提问（你问面试官）",
        }
        from components.ui import apple_section_heading
        for key, label in categories.items():
            questions = qdata.get(key, [])
            if questions:
                apple_section_heading(label)
                for i, q in enumerate(questions, 1):
                    if isinstance(q, dict):
                        with st.expander(f"Q{i}: {q.get('question', '')}"):
                            if q.get("why"):
                                st.markdown(f"**为什么会问:** {q['why']}")
                            if q.get("answer_framework"):
                                st.markdown(f"**答题框架:** {q['answer_framework']}")
                            if q.get("pitfalls"):
                                st.markdown(f"**避坑指南:** {q['pitfalls']}")
                    else:
                        st.markdown(f"- {q}")

# ── 公司速查表 ──────────────────────────────────────────────
with tab_cheatsheet:
    st.markdown("生成目标公司的一页纸面试速查表。")

    existing_cs = query("SELECT cheatsheet_md, created_at FROM interview_prep WHERE jd_id = ? AND cheatsheet_md IS NOT NULL ORDER BY created_at DESC LIMIT 1",
                        (selected_jd["id"],))

    if st.button("生成公司速查表", type="primary", key="gen_cheatsheet"):
        from services.ai_engine import generate_cheatsheet
        with st.spinner(f"正在调研 {selected_jd['company']}..."):
            try:
                cheatsheet = generate_cheatsheet(
                    company=selected_jd["company"],
                    role=selected_jd["title"],
                    resume_summary=resume_summary,
                )
            except Exception as e:
                alert_danger(f"生成失败: {e}")
                cheatsheet = None

        if cheatsheet:
            # 保存（更新或插入）
            if existing_cs:
                execute("UPDATE interview_prep SET cheatsheet_md = ? WHERE jd_id = ? AND cheatsheet_md IS NOT NULL",
                        (cheatsheet, selected_jd["id"]))
            else:
                execute("INSERT INTO interview_prep (jd_id, cheatsheet_md) VALUES (?, ?)",
                        (selected_jd["id"], cheatsheet))
            alert_success("速查表已生成！")
            existing_cs = [{"cheatsheet_md": cheatsheet}]

    if existing_cs and existing_cs[0]["cheatsheet_md"]:
        st.markdown(existing_cs[0]["cheatsheet_md"])
    else:
        st.caption("暂无速查表，点击上方按钮生成。")
