"""面试准备 — STAR 故事库 + 八股文 + 群面题库 + 牛客面经搜索。"""

import streamlit as st
import json
from models.database import query, execute
from components.ui import page_header, section_title, divider, alert_success, alert_info, alert_warning, alert_danger

page_header("面试题库", subtitle="STAR · 八股 · 群面，按场景准备")

tab_star, tab_bagu, tab_group, tab_nowcoder = st.tabs([
    "STAR 故事库", "八股文", "群面题库", "牛客面经"
])

# ═══════════════════════════════════════════════════════════════
# STAR 故事库
# ═══════════════════════════════════════════════════════════════
with tab_star:
    st.caption("积累面试故事，按标签分类，跨岗位复用。")

    # 添加新故事
    with st.expander("添加新故事", expanded=False):
        title = st.text_input("故事标题", placeholder="如：从0搭建9K粉丝社媒矩阵")
        sc1, sc2 = st.columns(2)
        with sc1:
            situation = st.text_area("Situation（背景）", height=80, placeholder="当时的背景和挑战是什么？")
            action = st.text_area("Action（行动）", height=80, placeholder="你具体做了什么？")
        with sc2:
            task = st.text_area("Task（任务）", height=80, placeholder="你的目标和职责是什么？")
            result = st.text_area("Result（结果）", height=80, placeholder="取得了什么量化成果？")
        tags = st.text_input("标签（逗号分隔）", placeholder="增长,数据,AI,运营,社媒")

        if st.button("保存故事", type="primary"):
            if title and situation:
                tag_list = json.dumps([t.strip() for t in tags.split(",") if t.strip()], ensure_ascii=False)
                execute(
                    "INSERT INTO star_stories (title, situation, task, action, result, tags) VALUES (?,?,?,?,?,?)",
                    (title, situation, task, action, result, tag_list),
                )
                alert_success("故事已保存！")
                st.rerun()
            else:
                alert_warning("至少填写标题和 Situation。")

    # 展示已有故事
    stories = query("SELECT * FROM star_stories ORDER BY used_count DESC, created_at DESC")
    if stories:
        # 按标签筛选
        all_tags = set()
        for s in stories:
            try:
                for t in json.loads(s.get("tags", "[]")):
                    all_tags.add(t)
            except (json.JSONDecodeError, TypeError):
                pass
        if all_tags:
            sel_tags = st.multiselect("按标签筛选", sorted(all_tags))
        else:
            sel_tags = []

        for s in stories:
            try:
                story_tags = json.loads(s.get("tags", "[]"))
            except (json.JSONDecodeError, TypeError):
                story_tags = []

            if sel_tags and not any(t in sel_tags for t in story_tags):
                continue

            tag_str = " ".join(f"`{t}`" for t in story_tags) if story_tags else ""
            with st.expander(f"{s['title']}　{tag_str}　(使用{s.get('used_count', 0)}次)"):
                st.markdown(f"**S (背景):** {s.get('situation', '')}")
                st.markdown(f"**T (任务):** {s.get('task', '')}")
                st.markdown(f"**A (行动):** {s.get('action', '')}")
                st.markdown(f"**R (结果):** {s.get('result', '')}")
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("标记使用", key=f"use_{s['id']}"):
                        execute("UPDATE star_stories SET used_count=used_count+1 WHERE id=?", (s["id"],))
                        st.rerun()
                with bc2:
                    if st.button("删除", key=f"del_star_{s['id']}"):
                        execute("DELETE FROM star_stories WHERE id=?", (s["id"],))
                        st.rerun()
    else:
        alert_info("暂无故事。点击上方「添加新故事」开始积累。")


# ═══════════════════════════════════════════════════════════════
# 八股文题库
# ═══════════════════════════════════════════════════════════════
with tab_bagu:
    st.caption("运营/产品常见八股文，积累个性化答案。")

    with st.expander("添加八股题", expanded=False):
        bq = st.text_input("问题", placeholder="如：如何从0到1做用户增长？", key="bq")
        ba = st.text_area("答案", height=120, placeholder="你的个性化回答...", key="ba")
        bt = st.text_input("标签", placeholder="增长,运营,方法论", key="bt")

        if st.button("保存", key="save_bagu"):
            if bq:
                tag_list = json.dumps([t.strip() for t in bt.split(",") if t.strip()], ensure_ascii=False)
                execute(
                    "INSERT INTO interview_qa (category, question, answer, tags) VALUES ('bagu',?,?,?)",
                    (bq, ba, tag_list),
                )
                alert_success("已保存！")
                st.rerun()

    bagu_qs = query("SELECT * FROM interview_qa WHERE category='bagu' ORDER BY created_at DESC")
    if bagu_qs:
        for q_item in bagu_qs:
            try:
                qtags = json.loads(q_item.get("tags", "[]"))
            except (json.JSONDecodeError, TypeError):
                qtags = []
            tag_str = " ".join(f"`{t}`" for t in qtags)
            with st.expander(f"{q_item['question']}　{tag_str}"):
                if q_item.get("answer"):
                    st.markdown(q_item["answer"])
                else:
                    st.caption("暂无答案")
                if st.button("删除", key=f"del_bagu_{q_item['id']}"):
                    execute("DELETE FROM interview_qa WHERE id=?", (q_item["id"],))
                    st.rerun()
    else:
        alert_info("暂无八股题。")

    # AI 批量生成八股题
    if st.button("AI 生成常见运营八股题", key="gen_bagu"):
        from services.ai_engine import _call_claude, AIError
        with st.spinner("生成中..."):
            try:
                result = _call_claude(
                    system_prompt="你是运营岗位面试专家。生成15个最常见的运营/增长/产品运营面试八股题。"
                                  "严格按JSON数组格式输出：[{\"question\": \"...\", \"answer\": \"...\", \"tags\": [\"标签\"]}]"
                                  "每题answer控制在150字以内，针对应届生。",
                    user_prompt="生成15个AI增长运营方向最常考的八股题，覆盖：用户增长、数据分析、内容运营、社群运营、AB测试、活动运营。",
                    max_tokens=4096,
                    temperature=0.5,
                )
                text = result.strip()
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:-1])
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    items = json.loads(text[start:end])
                    count = 0
                    for item in items:
                        if item.get("question"):
                            execute(
                                "INSERT INTO interview_qa (category, question, answer, tags) VALUES ('bagu',?,?,?)",
                                (item["question"], item.get("answer", ""),
                                 json.dumps(item.get("tags", []), ensure_ascii=False)),
                            )
                            count += 1
                    alert_success(f"已生成 {count} 题！")
                    st.rerun()
            except Exception as e:
                alert_danger(f"生成失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 群面题库
# ═══════════════════════════════════════════════════════════════
with tab_group:
    st.caption("群面/无领导小组讨论常见话题 + 角色建议 + 发言框架。")

    with st.expander("添加群面题", expanded=False):
        gq = st.text_input("话题", placeholder="如：如何在校园内推广一款AI学习工具？", key="gq")
        ga = st.text_area("分析框架", height=120, placeholder="角色建议、发言要点、时间分配...", key="ga")

        if st.button("保存", key="save_group"):
            if gq:
                execute(
                    "INSERT INTO interview_qa (category, question, answer, tags) VALUES ('group',?,?,?)",
                    (gq, ga, "[]"),
                )
                alert_success("已保存！")
                st.rerun()

    group_qs = query("SELECT * FROM interview_qa WHERE category='group' ORDER BY created_at DESC")
    if group_qs:
        for q_item in group_qs:
            with st.expander(f"{q_item['question']}"):
                if q_item.get("answer"):
                    st.markdown(q_item["answer"])
                else:
                    st.caption("暂无分析")
                if st.button("删除", key=f"del_group_{q_item['id']}"):
                    execute("DELETE FROM interview_qa WHERE id=?", (q_item["id"],))
                    st.rerun()
    else:
        alert_info("暂无群面题。")

    if st.button("AI 生成群面题", key="gen_group"):
        from services.ai_engine import _call_claude
        with st.spinner("生成中..."):
            try:
                result = _call_claude(
                    system_prompt="你是群面面试专家。生成8个互联网/AI公司常见的无领导小组讨论题目。"
                                  "严格按JSON数组输出：[{\"question\": \"话题\", \"answer\": \"分析框架（含角色建议、关键论点、时间分配建议）\"}]"
                                  "每题answer在200字以内。",
                    user_prompt="生成8个AI/互联网公司校招群面常见话题，覆盖产品设计、市场策略、资源分配、伦理讨论等方向。",
                    max_tokens=4096,
                    temperature=0.5,
                )
                text = result.strip()
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:-1])
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    items = json.loads(text[start:end])
                    count = 0
                    for item in items:
                        if item.get("question"):
                            execute(
                                "INSERT INTO interview_qa (category, question, answer, tags) VALUES ('group',?,?,?)",
                                (item["question"], item.get("answer", ""), "[]"),
                            )
                            count += 1
                    alert_success(f"已生成 {count} 题！")
                    st.rerun()
            except Exception as e:
                alert_danger(f"生成失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 牛客面经搜索
# ═══════════════════════════════════════════════════════════════
with tab_nowcoder:
    st.caption("搜索牛客网面经，AI 提取高频面试题。")

    nc_company = st.text_input("输入公司名", placeholder="如：MiniMax、月之暗面、商汤")

    if st.button("搜索面经", type="primary", key="search_nc") and nc_company:
        from services.ai_engine import _call_claude

        with st.spinner(f"正在搜索 {nc_company} 运营面经并提取高频题..."):
            try:
                search_prompt = f"""请根据你的知识，列出 {nc_company} 运营/增长/产品运营岗位面试中最常被问到的面试题。

要求：
1. 尽量基于真实面经信息
2. 覆盖：一面技术题、二面业务题、HR面常见题
3. 标注每题的面试轮次和频率（高/中/低）

严格按 JSON 数组输出：
[{{"question": "问题", "round": "一面/二面/HR面", "frequency": "高/中/低", "answer_hint": "回答要点"}}]

输出10-15题。"""

                result = _call_claude(
                    system_prompt="你是校招面试信息专家，熟悉各大公司的面经。",
                    user_prompt=search_prompt,
                    max_tokens=4096,
                    temperature=0.5,
                )

                text = result.strip()
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:-1])
                start = text.find("[")
                end = text.rfind("]") + 1

                if start >= 0 and end > start:
                    items = json.loads(text[start:end])

                    alert_success(f"找到 {len(items)} 道面试题")

                    for i, item in enumerate(items):
                        freq_label = f"[{item.get('frequency', '')}]" if item.get("frequency") else ""
                        with st.expander(f"{freq_label} [{item.get('round', '')}] {item['question']}"):
                            if item.get("answer_hint"):
                                st.markdown(f"**回答要点:** {item['answer_hint']}")

                    # 一键入库
                    if st.button("全部加入题库", key="import_nc"):
                        count = 0
                        for item in items:
                            execute(
                                "INSERT INTO interview_qa (category, question, answer, source_jd, tags) VALUES ('bagu',?,?,?,?)",
                                (item["question"], item.get("answer_hint", ""),
                                 f"牛客面经-{nc_company}",
                                 json.dumps([nc_company, item.get("round", "")], ensure_ascii=False)),
                            )
                            count += 1
                        alert_success(f"已导入 {count} 题到八股文题库！")
                        st.rerun()
                else:
                    alert_warning("解析失败，请重试。")
                    st.code(result)
            except Exception as e:
                alert_danger(f"搜索失败: {e}")
