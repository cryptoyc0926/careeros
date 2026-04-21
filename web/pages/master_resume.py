"""主简历 — 直接读写 DB `resume_master` 表（单一真相源）。

架构说明：
    - DB 表 `resume_master` 是唯一权威数据源
    - `web/data/master_resume.yaml` 已归档为只读种子文件，不再参与渲染
    - 本页所有修改直接落库，定制简历/PDF 渲染立即生效
"""

from __future__ import annotations

import io
import json
import sqlite3
import hashlib
from pathlib import Path

import streamlit as st

from config import settings
from components.ui import page_header, section_title, divider, alert_success, alert_danger

DB_PATH = settings.db_full_path


# ═══════════════════════════════════════════════════════════════
# 文件解析（上传简历 tab 仍然有用，保留）
# ═══════════════════════════════════════════════════════════════
def extract_resume_text(uploaded_file) -> str:
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith(".txt") or name.endswith(".md"):
        for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return file_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return file_bytes.decode("utf-8", errors="replace")

    if name.endswith(".pdf"):
        pdf_stream = io.BytesIO(file_bytes)
        for mod_name in ("pdfplumber", "pdfminer", "PyPDF2"):
            try:
                if mod_name == "pdfplumber":
                    import pdfplumber
                    with pdfplumber.open(pdf_stream) as pdf:
                        return "\n\n".join((p.extract_text() or "") for p in pdf.pages).strip()
                if mod_name == "pdfminer":
                    from pdfminer.high_level import extract_text
                    pdf_stream.seek(0)
                    return extract_text(pdf_stream).strip()
                if mod_name == "PyPDF2":
                    from PyPDF2 import PdfReader
                    pdf_stream.seek(0)
                    return "\n\n".join((p.extract_text() or "") for p in PdfReader(pdf_stream).pages).strip()
            except ImportError:
                continue
            except Exception:
                pdf_stream.seek(0)
                continue
        alert_danger("PDF 解析失败，请安装 `pdfplumber`、`pdfminer.six` 或 `PyPDF2`")
        return ""

    if name.endswith(".docx"):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(file_bytes))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            alert_danger(f"DOCX 解析失败：{e}")
            return ""

    alert_danger(f"不支持的文件格式：{name}")
    return ""


# ═══════════════════════════════════════════════════════════════
# DB 读写
# ═══════════════════════════════════════════════════════════════
def load_master() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM resume_master ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not row:
        return {
            "id": None,
            "basics": {"name": "", "phone": "", "email": "", "target_role": "",
                       "city": "", "availability": "", "photo": ""},
            "profile": {"pool": [{"id": "default", "tags": [], "text": ""}], "default": "default"},
            "projects": [],
            "internships": [],
            "skills": [],
            "education": [],
        }
    # 兼容老库：新列可能不存在
    keys = row.keys() if hasattr(row, "keys") else []
    docx_blob = row["original_docx_blob"] if "original_docx_blob" in keys else None
    docx_name = row["original_docx_filename"] if "original_docx_filename" in keys else None
    return {
        "id": row["id"],
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
        "original_docx_blob": docx_blob,
        "original_docx_filename": docx_name,
    }


def save_master(m: dict) -> None:
    # 先备份
    bak = Path(str(DB_PATH) + f".bak_before_master_save")
    try:
        bak.write_bytes(Path(DB_PATH).read_bytes())
    except Exception:
        pass

    conn = sqlite3.connect(DB_PATH)
    # 检测新列是否存在（幂等兼容未 migrate 的老库）
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(resume_master)").fetchall()}
    has_docx_cols = "original_docx_blob" in existing_cols and "original_docx_filename" in existing_cols

    # DOCX blob 优先从 session_state 的 _pending_docx_blob 拉，其次沿用 m 里现有的
    pending_blob = st.session_state.get("_pending_docx_blob")
    pending_name = st.session_state.get("_pending_docx_name")
    docx_blob = pending_blob if pending_blob is not None else m.get("original_docx_blob")
    docx_name = pending_name if pending_name else m.get("original_docx_filename")

    payload = (
        json.dumps(m["basics"], ensure_ascii=False),
        json.dumps(m["profile"], ensure_ascii=False),
        json.dumps(m["projects"], ensure_ascii=False),
        json.dumps(m["internships"], ensure_ascii=False),
        json.dumps(m["skills"], ensure_ascii=False),
        json.dumps(m["education"], ensure_ascii=False),
    )
    if m.get("id"):
        if has_docx_cols:
            conn.execute(
                """UPDATE resume_master
                   SET basics_json=?, profile_json=?, projects_json=?,
                       internships_json=?, skills_json=?, education_json=?,
                       original_docx_blob=COALESCE(?, original_docx_blob),
                       original_docx_filename=COALESCE(?, original_docx_filename),
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (*payload, docx_blob, docx_name, m["id"]),
            )
        else:
            conn.execute(
                """UPDATE resume_master
                   SET basics_json=?, profile_json=?, projects_json=?,
                       internships_json=?, skills_json=?, education_json=?,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (*payload, m["id"]),
            )
    else:
        if has_docx_cols:
            conn.execute(
                """INSERT INTO resume_master
                   (basics_json, profile_json, projects_json,
                    internships_json, skills_json, education_json,
                    original_docx_blob, original_docx_filename)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (*payload, docx_blob, docx_name),
            )
        else:
            conn.execute(
                """INSERT INTO resume_master
                   (basics_json, profile_json, projects_json,
                    internships_json, skills_json, education_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                payload,
            )
    conn.commit()
    conn.close()

    # 落库后清掉 pending bytes 避免后续重复写入
    if pending_blob is not None:
        st.session_state.pop("_pending_docx_blob", None)
        st.session_state.pop("_pending_docx_name", None)


def clear_tailor_state_after_master_change() -> None:
    """主简历变更后清空定制页缓存，避免继续使用旧经历/旧 PDF。"""
    for key in (
        "tailor_data",
        "tailor_meta",
        "tailor_jd",
        "_tailor_preview_key",
        "_tailor_preview_pdf",
        "_tailor_master_signature",
        "eval_data",
    ):
        st.session_state.pop(key, None)


# ═══════════════════════════════════════════════════════════════
# 工具：bullets 列表 ↔ 多行文本互转（编辑时更方便）
# ═══════════════════════════════════════════════════════════════
def bullets_to_text(bullets: list[str]) -> str:
    return "\n".join(bullets or [])


def text_to_bullets(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


# ═══════════════════════════════════════════════════════════════
# 页面
# ═══════════════════════════════════════════════════════════════
page_header(
    "主简历",
    subtitle="维护你的底稿，让每次定制都更轻松",
    right_text="生成简历",
    right_page="pages/resume_tailor.py",
)

# session state 初始化
if "master_data" not in st.session_state:
    st.session_state.master_data = load_master()

m = st.session_state.master_data

top_col1, top_col2, top_col3, top_col4 = st.columns([1, 1, 1.2, 2.5])
with top_col1:
    if st.button("重新加载", use_container_width=True):
        st.session_state.master_data = load_master()
        st.rerun()
with top_col2:
    if st.button("保存全部", type="primary", use_container_width=True):
        save_master(st.session_state.master_data)
        clear_tailor_state_after_master_change()
        st.session_state.master_data = load_master()
        st.session_state["_just_saved"] = True
        st.rerun()
with top_col3:
    # 导出当前主简历为 JSON
    _export_payload = {
        "schema": "careeros.resume_master",
        "exported_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "data": st.session_state.master_data,
    }
    st.download_button(
        "导出 JSON",
        data=json.dumps(_export_payload, ensure_ascii=False, indent=2),
        file_name=f"master_resume_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
        help="把当前主简历导出为 JSON 文件，下次可在「系统设置 → 数据备份」里导入",
    )
with top_col4:
    # 当前数据摘要
    n_proj = len(m.get("projects") or [])
    n_intern = len(m.get("internships") or [])
    n_skills = len(m.get("skills") or [])
    n_edu = len(m.get("education") or [])
    name = (m.get("basics") or {}).get("name", "") or "（未填）"
    summary = f"姓名：{name} · {n_proj} 项目 / {n_intern} 实习 / {n_skills} 技能 / {n_edu} 教育"
    st.caption(f"DB: `{Path(DB_PATH).name}` · record_id: {m.get('id') or '（新建）'} · {summary}")

# 保存成功提示（在 rerun 后显示）
if st.session_state.pop("_just_saved", False):
    n_proj = len(m.get("projects") or [])
    n_intern = len(m.get("internships") or [])
    alert_success(
        f"✓ 已写入数据库（record_id: {m.get('id')}）· "
        f"{n_proj} 项目 · {n_intern} 实习 · {len(m.get('skills') or [])} 技能 · {len(m.get('education') or [])} 教育。"
        f"现在去「**在线定制编辑**」可以用这份主简历生成定制版。"
    )

divider()

# ── 原 PDF 预览（上传后的参照）─────────────────────────────
if st.session_state.get("uploaded_pdf_bytes"):
    import base64 as _b64
    pdf_name = st.session_state.get("uploaded_pdf_name", "resume.pdf")
    pdf_bytes = st.session_state["uploaded_pdf_bytes"]
    _b64_data = _b64.b64encode(pdf_bytes).decode()
    with st.expander(f"📄 原简历 PDF 预览（{pdf_name} · {len(pdf_bytes):,} 字节）· 点击展开", expanded=False):
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{_b64_data}" '
            f'width="100%" height="600px" style="border:1px solid rgba(29,29,31,0.08);border-radius:14px"></iframe>',
            unsafe_allow_html=True,
        )
        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("清除 PDF 缓存", key="clear_pdf_cache"):
                st.session_state.pop("uploaded_pdf_bytes", None)
                st.session_state.pop("uploaded_pdf_name", None)
                st.rerun()

tab_basics, tab_profile, tab_projects, tab_intern, tab_skills, tab_edu, tab_upload = st.tabs(
    ["基本信息", "个人总结", "项目经历", "实习经历", "技能证书", "教育背景", "上传文件"]
)


# ── 基本信息 ────────────────────────────────────────────────
with tab_basics:
    b = m["basics"]
    c1, c2 = st.columns(2)
    b["name"] = c1.text_input("姓名", value=b.get("name", ""))
    b["phone"] = c2.text_input("电话", value=b.get("phone", ""))
    b["email"] = c1.text_input("邮箱", value=b.get("email", ""))
    b["photo"] = c2.text_input("照片文件名（templates 目录下，可留空）", value=b.get("photo", ""), placeholder="your_photo.png（可选）")
    b["target_role"] = c1.text_input("求职意向", value=b.get("target_role", ""))
    b["city"] = c2.text_input("期望城市", value=b.get("city", ""))
    b["availability"] = c1.text_input("到岗时间", value=b.get("availability", "随时"))


# ── 个人总结 ────────────────────────────────────────────────
with tab_profile:
    p = m["profile"]
    if not isinstance(p, dict) or "pool" not in p:
        # 旧结构兜底
        p = {"pool": [{"id": "default", "tags": [], "text": str(p or "")}], "default": "default"}
        m["profile"] = p

    pool = p.get("pool", [])
    if not pool:
        pool = [{"id": "default", "tags": [], "text": ""}]
        p["pool"] = pool

    default_id = p.get("default") or pool[0]["id"]
    ids = [item["id"] for item in pool]
    sel_idx = ids.index(default_id) if default_id in ids else 0

    sel_id = st.selectbox("编辑哪一版", ids, index=sel_idx, key="profile_sel")
    item = next((x for x in pool if x["id"] == sel_id), pool[0])

    c1, c2 = st.columns([2, 1])
    item["id"] = c1.text_input("版本 id", value=item.get("id", ""), key="profile_id")
    tags_text = c2.text_input("标签（逗号分隔）", value=", ".join(item.get("tags", [])), key="profile_tags")
    item["tags"] = [t.strip() for t in tags_text.split(",") if t.strip()]
    item["text"] = st.text_area(
        "正文（支持 <b>加粗</b> HTML 标签）",
        value=item.get("text", ""),
        height=200,
        key="profile_text",
    )

    c3, c4, c5 = st.columns(3)
    with c3:
        new_default = st.selectbox("默认版本", ids, index=ids.index(p.get("default", ids[0])) if p.get("default") in ids else 0, key="profile_default")
        p["default"] = new_default
    with c4:
        if st.button("新增版本", use_container_width=True):
            new_id = f"draft_{len(pool)+1}"
            pool.append({"id": new_id, "tags": [], "text": ""})
            st.rerun()
    with c5:
        if st.button("删除当前版本", use_container_width=True, disabled=len(pool) <= 1):
            p["pool"] = [x for x in pool if x["id"] != sel_id]
            if p["default"] == sel_id:
                p["default"] = p["pool"][0]["id"]
            st.rerun()


# ── 项目 / 实习 / 教育 通用编辑器 ───────────────────────────
def render_exp_editor(key: str, items: list[dict], label: str):
    if not items:
        items.append({"company": "", "role": "", "date": "", "bullets": []})

    for idx, it in enumerate(items):
        with st.expander(
            f"**{it.get('company') or '(未命名)'}** — {it.get('role', '')} · {it.get('date', '')}",
            expanded=False,
        ):
            c1, c2, c3 = st.columns([2, 2, 2])
            it["company"] = c1.text_input(
                "公司/项目" if key != "education" else "学校",
                value=it.get("company") or it.get("school", ""),
                key=f"{key}_company_{idx}",
            )
            it["role"] = c2.text_input(
                "职位/角色" if key != "education" else "专业",
                value=it.get("role") or it.get("major", ""),
                key=f"{key}_role_{idx}",
            )
            it["date"] = c3.text_input(
                "时间段（例：2023.06 - 2023.10）",
                value=it.get("date", ""),
                key=f"{key}_date_{idx}",
            )
            # education 需要映射回 school/major
            if key == "education":
                it["school"] = it["company"]
                it["major"] = it["role"]

            it["bullets"] = text_to_bullets(
                st.text_area(
                    "要点（每行一条，支持 <b>加粗</b> HTML）",
                    value=bullets_to_text(it.get("bullets", [])),
                    height=140,
                    key=f"{key}_bullets_{idx}",
                )
            )

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(f"删除这条", key=f"{key}_del_{idx}", use_container_width=True):
                    items.pop(idx)
                    st.rerun()
            with bc2:
                if idx > 0 and st.button(f"上移", key=f"{key}_up_{idx}", use_container_width=True):
                    items[idx - 1], items[idx] = items[idx], items[idx - 1]
                    st.rerun()

    if st.button(f"新增{label}", key=f"{key}_add", use_container_width=True):
        items.append({"company": "", "role": "", "date": "", "bullets": []})
        st.rerun()


with tab_projects:
    render_exp_editor("projects", m["projects"], "项目")

with tab_intern:
    render_exp_editor("internships", m["internships"], "实习")

with tab_edu:
    # 教育条目 DB 字段是 school/major，用 render_exp_editor 时用 company/role 映射
    for e in m["education"]:
        e.setdefault("company", e.get("school", ""))
        e.setdefault("role", e.get("major", ""))
    render_exp_editor("education", m["education"], "教育经历")


# ── 技能证书 ────────────────────────────────────────────────
with tab_skills:
    skills = m["skills"]
    for idx, s in enumerate(skills):
        c1, c2, c3 = st.columns([1, 4, 0.5])
        s["label"] = c1.text_input("类别", value=s.get("label", ""), key=f"skill_label_{idx}")
        s["text"] = c2.text_input("描述", value=s.get("text", ""), key=f"skill_text_{idx}")
        with c3:
            st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)
            if st.button("删除", key=f"skill_del_{idx}"):
                skills.pop(idx)
                st.rerun()
    if st.button("新增技能", use_container_width=True):
        skills.append({"label": "", "text": ""})
        st.rerun()


# ── 上传解析 ────────────────────────────────────────────────
with tab_upload:
    st.markdown(
        "上传 PDF / DOCX / TXT 简历，系统会**识别字段后自动填入下方 tab**。"
        "默认走「**规则解析**」（纯正则/关键词，不调 API · 秒出结果 · 0 费用）；"
        "结果不满意再点「AI 智能解析」用 Claude 兜底（需 API Key）。"
    )
    f = st.file_uploader("选择文件", type=["pdf", "docx", "txt", "md"])
    if f:
        st.caption(f"{f.name}  |  {f.size:,} 字节")
        # 保存原 PDF bytes 到 session_state 供顶部预览使用
        if f.name.lower().endswith(".pdf"):
            f.seek(0)
            st.session_state["uploaded_pdf_bytes"] = f.read()
            st.session_state["uploaded_pdf_name"] = f.name
            f.seek(0)
        # 保存 DOCX bytes 供 Phase 2 原版回写使用
        if f.name.lower().endswith(".docx"):
            f.seek(0)
            st.session_state["_pending_docx_blob"] = f.read()
            st.session_state["_pending_docx_name"] = f.name
            f.seek(0)
        with st.spinner("提取文本..."):
            text = extract_resume_text(f)
        if text:
            alert_success(f"文本提取完成（{len(text):,} 字符）。系统会先自动规则解析并保存；也可以手动重跑或用 AI 覆盖。")

            def _apply_parsed(parsed: dict, *, persist: bool = True) -> None:
                st.session_state["master_data"] = {
                    "id":          (st.session_state.get("master_data") or {}).get("id"),
                    "basics":      parsed["basics"],
                    "profile":     {"pool": [{"id": "default", "tags": [], "text": parsed.get("profile") or ""}], "default": "default"},
                    "projects":    parsed.get("projects") or [],
                    "internships": parsed.get("internships") or [],
                    "skills":      parsed.get("skills") or [],
                    "education":   parsed.get("education") or [],
                }
                clear_tailor_state_after_master_change()
                if persist:
                    save_master(st.session_state["master_data"])
                    st.session_state["master_data"] = load_master()

            def _parse_summary(parsed: dict) -> tuple[str, bool]:
                n_proj = len(parsed.get("projects", []))
                n_intern = len(parsed.get("internships", []))
                n_skills = len(parsed.get("skills", []))
                n_edu = len(parsed.get("education", []))
                name_ok = bool(parsed["basics"].get("name"))
                low_quality = (not name_ok) or (n_proj + n_intern == 0) or (n_edu == 0)
                summary = (
                    f"识别到 姓名「{parsed['basics'].get('name') or '未识别'}」· "
                    f"{n_proj} 个项目 · {n_intern} 段经历 · {n_skills} 类技能 · {n_edu} 段教育"
                )
                return summary, low_quality

            file_sig = hashlib.sha256(f"{f.name}:{f.size}:{text}".encode("utf-8")).hexdigest()
            if st.session_state.get("_resume_upload_auto_parse_sig") != file_sig:
                try:
                    from services.resume_rule_parser import parse_resume_text as rule_parse
                    parsed = rule_parse(text)
                    _apply_parsed(parsed)
                    summary, low_quality = _parse_summary(parsed)
                    st.session_state["_resume_upload_auto_parse_sig"] = file_sig
                    st.session_state["_resume_upload_auto_parse_message"] = (summary, low_quality)
                    st.rerun()
                except Exception as e:
                    alert_danger(f"自动规则解析失败：{type(e).__name__}: {e}")

            if st.session_state.get("_resume_upload_auto_parse_message"):
                summary, low_quality = st.session_state["_resume_upload_auto_parse_message"]
                if low_quality:
                    alert_warning(
                        f"自动规则解析识别率较低。{summary}。\n\n"
                        f"建议使用「AI 智能解析并保存」覆盖。"
                    )
                else:
                    alert_success(
                        f"自动规则解析完成并已写入数据库。{summary}。"
                        f"在线定制编辑会立即使用这份新主简历。"
                    )

            col_rule, col_ai = st.columns(2)

            # ── 规则解析（默认推荐 · 不用 API）──
            with col_rule:
                if st.button("重新规则解析并保存", type="primary", key="rule_parse_resume",
                             use_container_width=True,
                             help="纯正则 + 关键词识别，不调 API，瞬间出结果"):
                    try:
                        from services.resume_rule_parser import parse_resume_text as rule_parse
                        with st.spinner("规则解析中..."):
                            parsed = rule_parse(text)
                        _apply_parsed(parsed)

                        # 规则解析质量自检
                        summary, low_quality = _parse_summary(parsed)

                        if low_quality:
                            # 关键字段缺失 → 显著提示用户切到 AI 兜底
                            st.session_state["_rule_parse_low_quality"] = True
                            alert_warning(
                                f"规则解析识别率较低。{summary}。\n\n"
                                f"**建议点右侧「AI 智能解析」用 Claude 兜底**"
                                f"（规则解析对非标准格式简历覆盖有限）。"
                            )
                        else:
                            st.session_state["_rule_parse_low_quality"] = False
                            alert_success(
                                f"规则解析完成并已写入数据库。{summary}。"
                                f"现在去「在线定制编辑」会使用这份新主简历。"
                            )
                        st.rerun()
                    except Exception as e:
                        alert_danger(f"规则解析失败：{type(e).__name__}: {e}")

            # ── AI 解析（fallback · 规则没识别出再用）──
            with col_ai:
                if st.button("AI 智能解析并保存", key="ai_parse_resume",
                             use_container_width=True,
                             disabled=not settings.has_anthropic_key,
                             help="调 Claude 做结构化，对非标准简历更可靠，耗 1-2 次 API 调用"):
                    try:
                        from services.resume_parser import parse_resume_text as ai_parse
                        with st.spinner("AI 解析中（约 10-30 秒）..."):
                            parsed = ai_parse(text)
                        _apply_parsed(parsed)
                        alert_success(
                            f"AI 解析完成并已写入数据库。识别到 "
                            f"{len(parsed['projects'])} 个项目 · "
                            f"{len(parsed['internships'])} 段实习 · "
                            f"{len(parsed['skills'])} 类技能 · "
                            f"{len(parsed['education'])} 段教育。"
                        )
                        st.rerun()
                    except Exception as e:
                        alert_danger(f"AI 解析失败：{type(e).__name__}: {e}")

            if not settings.has_anthropic_key:
                st.caption("⚠️ AI 解析需要先在「系统设置」配 API Key；规则解析无需 Key，随时可用。")

            with st.expander("查看原始提取文本（debug 用）", expanded=False):
                st.text_area("提取内容（只读）", value=text, height=300, disabled=True, label_visibility="collapsed")


# ── 底部全局提示 ────────────────────────────────────────────
divider()
st.caption(
    "手动编辑字段后需点顶部「保存全部」落库；上传文件解析会自动保存。"
    " 如需放弃未保存的手动改动，点「重新加载」。"
)
