"""
简历在线编辑 & JD 定制
~~~~~~~~~~~~~~~~~~~~~~~~~~~
三栏交互：
  左：JD 输入 / 历史版本
  中：分段编辑器（profile / projects / internships / skills）
  右：实时 PDF 预览 + 下载

数据流：
  resume_master → tailor(jd) → content_json(session) → renderer → PDF bytes
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

from config import settings
from services import resume_renderer, resume_tailor
from services.ai_engine import AIError
from components.ui import page_header, section_title, divider, score_hero_card, alert_success, alert_info, alert_warning, alert_danger

DB_PATH = settings.db_full_path

page_header("简历定制 & 在线编辑", subtitle="在线微调生成版本")

if not settings.has_anthropic_key:
    alert_danger("Claude API Key 未配置，请前往 **设置** 页面。")
    st.stop()


# ── 读 master ────────────────────────────────────────────
def load_master() -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM resume_master ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
    }


def flatten_master_for_render(master: dict) -> dict:
    """把 profile pool 折叠成默认文本，得到 renderer 直接可用的扁平结构。"""
    profile = master["profile"]
    if isinstance(profile, dict) and "pool" in profile:
        default_id = profile.get("default")
        text = next(
            (p["text"] for p in profile["pool"] if p["id"] == default_id),
            profile["pool"][0]["text"],
        )
    else:
        text = profile
    return {
        "basics": master["basics"],
        "profile": text,
        "projects": master["projects"],
        "internships": master["internships"],
        "skills": master["skills"],
        "education": master["education"],
    }


master = load_master()
if not master:
    alert_danger("resume_master 表为空。请先执行 `python scripts/seed_resume_master.py`。")
    st.stop()


# ── Session state ────────────────────────────────────────
if "tailor_data" not in st.session_state:
    st.session_state.tailor_data = flatten_master_for_render(master)
if "tailor_meta" not in st.session_state:
    st.session_state.tailor_meta = {}
if "tailor_jd" not in st.session_state:
    st.session_state.tailor_jd = ""


# ── 布局：三栏 ──────────────────────────────────────────
col_left, col_mid, col_right = st.columns([1.0, 1.8, 1.4])

# ═══ 左栏：JD 输入 + 历史版本 ═══
with col_left:
    st.markdown("##### 目标 JD")

    # 岗位池下拉 —— 关联 job_descriptions，有 JD 的自动带入
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = conn.execute(
        '''SELECT id, "公司" AS company, "岗位名称" AS position,
                  "等级" AS level, link_type, 链接 AS url,
                  jd_fetch_mode, jd_status, jd_last_error
           FROM jobs_pool ORDER BY id DESC LIMIT 80'''
    ).fetchall()

    # 预先构建 jd_map: 优先用 notes 中的 岗位池#id 精确关联，fallback 到 (company,title) 模糊匹配
    jd_map: dict[int, str] = {}
    all_jds = conn.execute(
        "SELECT company, title, raw_text, notes FROM job_descriptions WHERE raw_text IS NOT NULL"
    ).fetchall()

    # 建 notes 索引: pool_id -> raw_text
    notes_index: dict[int, str] = {}
    for jd in all_jds:
        notes = jd["notes"] or ""
        import re as _re
        m = _re.search(r"岗位池#(\d+)", notes)
        if m:
            notes_index[int(m.group(1))] = jd["raw_text"] or ""

    for j in jobs:
        # 1. notes ID 精确匹配
        txt = notes_index.get(j["id"], "")
        # 2. fallback: company + title 模糊匹配
        if not txt:
            for jd in all_jds:
                if (jd["company"] or "").strip() == (j["company"] or "").strip() and \
                   (jd["title"] or "").strip() == (j["position"] or "").strip():
                    txt = jd["raw_text"] or ""
                    break
        if txt and len(txt.strip()) >= 200 and not txt.startswith("Company:"):
            jd_map[j["id"]] = txt.strip()
    conn.close()

    # 五档状态：已抓 / 待Chrome / 可自动 / 手动 / 黑名单
    def _icon(j) -> str:
        if j["id"] in jd_map:
            return "[已抓]"
        mode = j["jd_fetch_mode"] or "auto"
        status = j["jd_status"] or "pending"
        if mode == "blocked":
            return "[黑名单]"
        if mode == "manual":
            return "[手动]"
        if mode == "browser":
            return "[待Chrome]"
        if mode == "auto":
            return "[失败]" if status == "failed" else "[待抓]"
        return "[?]"

    def _fmt_job(j) -> str:
        return f"{_icon(j)} #{j['id']} [{j['level'] or '-'}] {j['company']} / {j['position']}"

    job_options = ["（手动粘贴 JD）"] + [_fmt_job(j) for j in jobs]
    job_id_by_label = {_fmt_job(j): j["id"] for j in jobs}
    job_meta_by_id = {j["id"]: j for j in jobs}

    choice = st.selectbox(
        "从岗位池选（状态已标注：已抓 / 可自动 / 待Chrome / 手动 / 黑名单）",
        job_options,
        key="job_choice",
    )

    prev = st.session_state.get("_last_job_choice")
    if choice != prev:
        st.session_state._last_job_choice = choice
        if choice == "（手动粘贴 JD）":
            pass
        else:
            jid = job_id_by_label.get(choice)
            if jid in jd_map:
                st.session_state.tailor_jd = jd_map[jid]
                st.rerun()
            else:
                st.session_state.tailor_jd = ""
                st.rerun()

    # 当前选中岗位的状态提示
    if choice != "（手动粘贴 JD）":
        jid = job_id_by_label.get(choice)
        jmeta = job_meta_by_id.get(jid)
        if jmeta is None:
            pass
        elif jid in jd_map:
            alert_success(f"已关联 JD（{len(jd_map[jid])} 字，adapter 抓取）")
        else:
            mode = jmeta["jd_fetch_mode"] or "auto"
            if mode == "blocked":
                alert_danger("黑名单公司（字节/蚂蚁/腾讯/网易），不建议投递")
            elif mode == "manual":
                alert_warning(
                    "此岗位需手动获取 JD\n\n"
                    "邮箱投递 / 纯门户列表页 / 链接失效。到原链接复制 JD 后粘贴到下方。"
                )
            elif mode == "browser":
                alert_info(
                    "此岗位需 Chrome MCP 抓取\n\n"
                    f"原链接：{jmeta['url']}\n\n"
                    "SPA 页面 Python 抓不到。方式二选一：\n"
                    "① 在 Claude 对话里说「用 Chrome MCP 抓岗位池 #"
                    f"{jid} 的 JD」让我来抓；② 手动复制粘贴到下方。"
                )
            elif mode == "auto":
                err = jmeta["jd_last_error"] or ""
                if err:
                    alert_danger(f"自动抓取失败：{err[:120]}")
                else:
                    alert_info("此岗位在自动抓取队列，尚未处理。可到终端跑 `python scripts/jd_worker.py run`")

    jd_text = st.text_area(
        "JD 原文",
        value=st.session_state.tailor_jd,
        height=220,
        placeholder="粘贴 JD 全文...",
        key="jd_textarea",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        go = st.button("生成定制版", type="primary", use_container_width=True)
    with col_b:
        reset = st.button("重置为主简历", use_container_width=True)

    if reset:
        st.session_state.tailor_data = flatten_master_for_render(master)
        st.session_state.tailor_meta = {}
        st.session_state.tailor_jd = ""
        st.rerun()

    if go and jd_text.strip():
        with st.spinner("正在分析 JD 并重写简历..."):
            try:
                tailored = resume_tailor.tailor_resume(master, jd_text)
                meta = tailored.pop("_meta", {})
                st.session_state.tailor_data = tailored
                st.session_state.tailor_meta = meta
                st.session_state.tailor_jd = jd_text
                # 显示校验警告（硬错会进 except 分支）
                v = meta.get("validation", {})
                warn_count = len(v.get("warnings", []))
                if warn_count:
                    alert_warning(f"完成 · 匹配度 {meta.get('match_score', '?')} · {warn_count} 条校验警告（见右栏）")
                else:
                    alert_success(f"完成 · 匹配度 {meta.get('match_score', '?')} · 校验全通过")
                st.rerun()
            except AIError as e:
                alert_danger(f"AI 调用失败：{e}")
            except Exception as e:
                # T6 ValidationError 走这里，渲染红色 banner + diff
                from services.resume_validator import ValidationError
                if isinstance(e, ValidationError):
                    st.session_state.tailor_validation_error = e.report.as_dict()
                    alert_danger(f"硬规则校验失败：{len(e.report.hard_errors)} 条硬错 · 未写入定制版")
                    with st.expander("查看违规明细", expanded=True):
                        for err in e.report.hard_errors:
                            st.markdown(
                                f"- **[{err['rule']}]** `{err['location']}` — {err['message']}\n\n"
                                f"  期望：`{err['expected']}`\n\n  实际：`{err['actual']}`"
                            )
                        if e.report.warnings:
                            st.markdown("---")
                            st.markdown("**警告**：")
                            for w in e.report.warnings:
                                st.caption(f"[{w['rule']}] {w['location']} — {w['message']}")
                else:
                    alert_danger(f"失败：{e}")

    # 历史版本
    st.markdown("---")
    st.markdown("##### 历史版本")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    versions = conn.execute(
        """SELECT id, version_name, target_role, match_score, created_at
           FROM resume_versions ORDER BY created_at DESC LIMIT 10"""
    ).fetchall()
    conn.close()
    if not versions:
        st.caption("暂无")
    else:
        for v in versions:
            if st.button(
                f"#{v['id']} {v['version_name']} · {v['match_score']}分",
                key=f"v_{v['id']}",
                use_container_width=True,
            ):
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT content_json FROM resume_versions WHERE id = ?",
                    (v["id"],),
                ).fetchone()
                conn.close()
                st.session_state.tailor_data = json.loads(row["content_json"])
                st.rerun()


# ═══ 中栏：分段编辑器 ═══
with col_mid:
    st.markdown("##### 在线编辑")

    data = st.session_state.tailor_data
    meta = st.session_state.tailor_meta

    if meta:
        alert_info(
            f"**匹配度 {meta.get('match_score', '?')}** · "
            f"{meta.get('change_notes', '')}"
        )

    # Basics
    with st.expander("基本信息", expanded=False):
        data["basics"]["target_role"] = st.text_input(
            "求职意向", value=data["basics"].get("target_role", "")
        )
        data["basics"]["city"] = st.text_input(
            "期望城市", value=data["basics"].get("city", "")
        )

    # Profile
    with st.expander("个人总结", expanded=True):
        data["profile"] = st.text_area(
            "profile",
            value=data["profile"],
            height=120,
            label_visibility="collapsed",
        )
        if st.button("仅重写此段", key="rw_profile"):
            if not st.session_state.tailor_jd:
                alert_warning("请先在左栏粘贴 JD")
            else:
                with st.spinner("重写中..."):
                    try:
                        intent = meta.get("jd_intent") or resume_tailor.extract_jd_intent(
                            st.session_state.tailor_jd
                        )
                        data["profile"] = resume_tailor.rewrite_section(
                            data["profile"], intent
                        )
                        st.rerun()
                    except AIError as e:
                        alert_danger(str(e))

    # Projects
    with st.expander("项目经历", expanded=True):
        for p_idx, p in enumerate(data["projects"]):
            st.markdown(f"**{p['company']}** — {p['date']}")
            p["role"] = st.text_input(
                "职位", value=p["role"], key=f"proj_role_{p_idx}"
            )
            for b_idx, b in enumerate(p["bullets"]):
                p["bullets"][b_idx] = st.text_area(
                    f"bullet {b_idx + 1}",
                    value=b,
                    key=f"proj_{p_idx}_b_{b_idx}",
                    height=68,
                    label_visibility="collapsed",
                )

    # Internships
    with st.expander("实习经历", expanded=True):
        for i_idx, i in enumerate(data["internships"]):
            st.markdown(f"**{i['company']}** — {i['date']}")
            i["role"] = st.text_input(
                "职位", value=i["role"], key=f"intern_role_{i_idx}"
            )
            for b_idx, b in enumerate(i["bullets"]):
                i["bullets"][b_idx] = st.text_area(
                    f"bullet {b_idx + 1}",
                    value=b,
                    key=f"intern_{i_idx}_b_{b_idx}",
                    height=68,
                    label_visibility="collapsed",
                )

    # Skills
    with st.expander("技能证书", expanded=False):
        for s_idx, s in enumerate(data["skills"]):
            cols = st.columns([1, 4])
            with cols[0]:
                s["label"] = st.text_input(
                    "标签", value=s["label"], key=f"skill_l_{s_idx}",
                    label_visibility="collapsed",
                )
            with cols[1]:
                s["text"] = st.text_input(
                    "内容", value=s["text"], key=f"skill_t_{s_idx}",
                    label_visibility="collapsed",
                )

    st.session_state.tailor_data = data


# ═══ 右栏：实时预览 + 深度评估 ═══
with col_right:
    tab_preview, tab_eval = st.tabs(["实时预览", "深度评估"])

with tab_eval:
    from services import resume_evaluator
    if "eval_data" not in st.session_state:
        st.session_state.eval_data = None

    c_btn, c_cache = st.columns([1, 1])
    with c_btn:
        run_eval = st.button("深度评估", type="primary", use_container_width=True,
                             disabled=not st.session_state.tailor_jd.strip())
    with c_cache:
        if st.button("读缓存", use_container_width=True,
                     disabled=not st.session_state.tailor_jd.strip()):
            cached = resume_evaluator.load_latest_for_jd(st.session_state.tailor_jd)
            if cached:
                st.session_state.eval_data = cached
                st.toast("已加载上次评估")
            else:
                alert_warning("此 JD 无历史评估")

    if run_eval:
        with st.spinner("跑深度评估中..."):
            try:
                ev = resume_evaluator.deep_evaluate(
                    st.session_state.tailor_jd,
                    st.session_state.tailor_data,
                    st.session_state.tailor_meta.get("jd_intent"),
                )
                st.session_state.eval_data = ev
                resume_evaluator.save_evaluation(
                    st.session_state.tailor_jd,
                    ev,
                    target_role=st.session_state.tailor_data["basics"].get("target_role", ""),
                )
                st.toast("评估完成 + 已落库")
            except Exception as e:
                alert_danger(f"评估失败：{e}")

    ev = st.session_state.eval_data
    if ev:
        score = ev.get("overall_score", 0)
        verdict = ev.get("one_line_verdict", "")
        score_hero_card(score, verdict=verdict)

        # A 匹配分析
        with st.expander("A · 匹配分析（逐条 JD 要求）", expanded=True):
            sa = ev.get("section_a_match", {})
            for req in sa.get("requirements", []):
                icon = {"match": "OK", "weak": "弱", "miss": "缺"}.get(req.get("status"), "?")
                st.markdown(f"{icon} **{req.get('requirement', '')}**")
                if req.get("evidence"):
                    st.caption(f"证据：「{req['evidence']}」 · {req.get('note', '')}")
                elif req.get("note"):
                    st.caption(req["note"])

        # B Gap
        with st.expander("B · Gap 分析"):
            sb = ev.get("section_b_gap", {})
            if sb.get("critical_gaps"):
                st.markdown("**硬缺口**")
                for g in sb["critical_gaps"]:
                    st.markdown(f"- {g}")
            if sb.get("soft_gaps"):
                st.markdown("**软缺口**")
                for g in sb["soft_gaps"]:
                    st.markdown(f"- {g}")
            if sb.get("bridgeable"):
                st.markdown("**可弥补**")
                for g in sb["bridgeable"]:
                    st.markdown(f"- {g}")

        # C 改写建议
        with st.expander("C · 简历改写建议"):
            sc = ev.get("section_c_resume_advice", {})
            if sc.get("strengthen"):
                st.markdown("**强化**")
                for s in sc["strengthen"]:
                    st.markdown(f"- {s}")
            if sc.get("downplay"):
                st.markdown("**弱化**")
                for s in sc["downplay"]:
                    st.markdown(f"- {s}")
            if sc.get("add_keywords"):
                st.markdown("**补关键词**: " + "、".join(sc["add_keywords"]))

        # D 预测题
        with st.expander("D · 预测面试题（5 道）"):
            sd = ev.get("section_d_interview_qa", {})
            for i, q in enumerate(sd.get("questions", []), 1):
                st.markdown(f"**Q{i}. {q.get('q','')}**")
                if q.get("why"):
                    st.caption(f"问法原因：{q['why']}")
                if q.get("answer_hint"):
                    st.markdown(f"> 回答要点：{q['answer_hint']}")
                st.markdown("")

        # E 策略
        with st.expander("E · 投递策略"):
            se = ev.get("section_e_strategy", {})
            rows = [
                ("推荐渠道", se.get("recommended_channel")),
                ("最佳时机", se.get("best_timing")),
                ("竞争激烈度", se.get("competition_level")),
                ("内推角度", se.get("referral_angle")),
                ("风险提示", se.get("risk_warning")),
            ]
            for k, v in rows:
                if v:
                    st.markdown(f"**{k}**：{v}")
    else:
        st.caption("先在左栏输入 JD 并生成定制版，再点「深度评估」")


with tab_preview:

    try:
        pdf_bytes = resume_renderer.render_pdf_bytes(st.session_state.tailor_data)

        # 转 PNG 预览
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(pdf_bytes)
            tmp_pdf = Path(tf.name)

        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(tmp_pdf), dpi=110, first_page=1, last_page=1)
            if images:
                st.image(images[0], use_column_width=True)
        except Exception:
            # pdf2image 不可用则用 pdftoppm 回退
            import subprocess
            png_prefix = tmp_pdf.with_suffix("")
            subprocess.run(
                ["pdftoppm", "-png", "-r", "110", str(tmp_pdf), str(png_prefix)],
                check=False,
            )
            png_file = Path(str(png_prefix) + "-1.png")
            if png_file.exists():
                st.image(str(png_file), use_column_width=True)
            else:
                st.caption("（预览不可用，请直接下载 PDF 查看）")

        st.download_button(
            "下载 PDF",
            data=pdf_bytes,
            file_name=f"{st.session_state.tailor_data['basics'].get('name', 'resume')}_简历_{st.session_state.tailor_data['basics'].get('target_role', '定制版')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

        # 保存为版本
        st.markdown("---")
        v_name = st.text_input("版本命名", value="", placeholder="如：MiniMax-增长")
        if st.button("保存此版本", use_container_width=True):
            if not v_name.strip():
                alert_warning("请输入版本名")
            else:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    """INSERT INTO resume_versions
                       (master_id, target_role, version_name, content_json, match_score)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        master["id"],
                        st.session_state.tailor_data["basics"].get("target_role"),
                        v_name.strip(),
                        json.dumps(st.session_state.tailor_data, ensure_ascii=False),
                        st.session_state.tailor_meta.get("match_score", 0),
                    ),
                )
                conn.commit()
                conn.close()
                alert_success(f"已保存：{v_name}")
                st.rerun()

    except Exception as e:
        alert_danger(f"预览渲染失败：{e}")
