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
    return {
        "id": row["id"],
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
    }


def save_master(m: dict) -> None:
    # 先备份
    bak = Path(str(DB_PATH) + f".bak_before_master_save")
    try:
        bak.write_bytes(Path(DB_PATH).read_bytes())
    except Exception:
        pass

    conn = sqlite3.connect(DB_PATH)
    payload = (
        json.dumps(m["basics"], ensure_ascii=False),
        json.dumps(m["profile"], ensure_ascii=False),
        json.dumps(m["projects"], ensure_ascii=False),
        json.dumps(m["internships"], ensure_ascii=False),
        json.dumps(m["skills"], ensure_ascii=False),
        json.dumps(m["education"], ensure_ascii=False),
    )
    if m.get("id"):
        conn.execute(
            """UPDATE resume_master
               SET basics_json=?, profile_json=?, projects_json=?,
                   internships_json=?, skills_json=?, education_json=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (*payload, m["id"]),
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
    right_page="pages/generate.py",
)

# session state 初始化
if "master_data" not in st.session_state:
    st.session_state.master_data = load_master()

m = st.session_state.master_data

top_col1, top_col2, top_col3 = st.columns([1, 1, 3])
with top_col1:
    if st.button("重新加载", use_container_width=True):
        st.session_state.master_data = load_master()
        st.rerun()
with top_col2:
    if st.button("保存全部", type="primary", use_container_width=True):
        save_master(st.session_state.master_data)
        alert_success("已写入数据库")
        st.session_state.master_data = load_master()
        st.rerun()
with top_col3:
    st.caption(f"DB: `{Path(DB_PATH).name}` · record_id: {m.get('id') or '（新建）'}")

divider()

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
    st.markdown("上传 PDF / DOCX / TXT 简历，**AI 会自动识别并填入下方各个 tab 的字段**，你只需校对和微调。")
    f = st.file_uploader("选择文件", type=["pdf", "docx", "txt", "md"])
    if f:
        st.caption(f"{f.name}  |  {f.size:,} 字节")
        with st.spinner("提取文本..."):
            text = extract_resume_text(f)
        if text:
            alert_success(f"文本提取完成（{len(text):,} 字符）。点下面按钮让 AI 结构化。")

            col_ai, _ = st.columns([1, 3])
            with col_ai:
                if st.button("🤖 AI 智能解析并填入字段", type="primary", key="ai_parse_resume",
                             disabled=not settings.has_anthropic_key,
                             help="AI 识别姓名/经历/项目/技能/教育后自动填到各 tab；耗费约 1-2 次 API 调用"):
                    try:
                        from services.resume_parser import parse_resume_text
                        with st.spinner("AI 解析中（约 10-30 秒）..."):
                            parsed = parse_resume_text(text)
                        # 把解析结果写入 session_state.master_data（让其他 tab 能读到）
                        _existing = st.session_state.get("master_data", {}) or {}
                        st.session_state.master_data = {
                            "id":          _existing.get("id"),
                            "basics":      parsed["basics"],
                            "profile":     {"pool": [{"id": "default", "tags": [], "text": parsed["profile"] or ""}], "default": "default"},
                            "projects":    parsed["projects"],
                            "internships": parsed["internships"],
                            "skills":      parsed["skills"],
                            "education":   parsed["education"],
                        }
                        alert_success(
                            f"✓ AI 解析完成。识别到 "
                            f"{len(parsed['projects'])} 个项目 · "
                            f"{len(parsed['internships'])} 段实习 · "
                            f"{len(parsed['skills'])} 类技能 · "
                            f"{len(parsed['education'])} 段教育。"
                            f"切到其他 tab 检查内容，**最后点顶部「保存全部」才会真正落库**。"
                        )
                        st.rerun()
                    except Exception as e:
                        alert_danger(f"解析失败：{type(e).__name__}: {e}")

            if not settings.has_anthropic_key:
                st.caption("⚠️ 需要先在「系统设置」填 API Key 才能启用 AI 解析。")

            with st.expander("查看原始提取文本", expanded=False):
                st.text_area("提取内容（只读）", value=text, height=300, disabled=True, label_visibility="collapsed")


# ── 底部全局提示 ────────────────────────────────────────────
divider()
st.caption(
    "页面上的所有修改在内存里。**点顶部「保存全部」才会落库**。"
    " 保存前如需放弃改动，点「重新加载」。"
)
