"""添加 JD — 粘贴文本、上传文件或输入链接自动抓取。"""

import streamlit as st
import json
import io
from datetime import datetime
from models.database import execute
from components.ui import page_header, section_title, divider, apple_section_heading, alert_success, alert_info, alert_warning, alert_danger


def extract_text_from_txt(file_bytes: bytes) -> str:
    """从 .txt 文件提取文本。"""
    for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return file_bytes.decode("utf-8", errors="replace")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从 .pdf 文件提取文本（按优先级尝试多个库）。"""
    text = ""
    pdf_stream = io.BytesIO(file_bytes)

    # 方案 1: pdfplumber
    if not text:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_stream) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(pages)
        except ImportError:
            pass
        except Exception:
            pdf_stream.seek(0)

    # 方案 2: pdfminer
    if not text:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            pdf_stream.seek(0)
            text = pdfminer_extract(pdf_stream)
        except ImportError:
            pass
        except Exception:
            pdf_stream.seek(0)

    # 方案 3: PyPDF2
    if not text:
        try:
            from PyPDF2 import PdfReader
            pdf_stream.seek(0)
            reader = PdfReader(pdf_stream)
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(pages)
        except ImportError:
            pass
        except Exception:
            pass

    if text and text.strip():
        return text.strip()

    alert_danger("PDF 解析失败。请安装：`pip install pdfplumber`")
    return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 .docx 文件提取文本。"""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        alert_danger("需要安装 python-docx：`pip install python-docx`")
        return ""
    except Exception as e:
        alert_danger(f"DOCX 解析失败：{e}")
        return ""


def extract_text(uploaded_file) -> str:
    """根据文件类型自动选择解析方式。"""
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    elif name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    else:
        alert_danger(f"不支持的文件格式：{name}")
        return ""


# ═══════════════════════════════════════════════════════════════
# 页面
# ═══════════════════════════════════════════════════════════════
page_header("添加 JD", subtitle="加一个新岗位到你的视野里")

tab_search, tab_url, tab_smart_paste, tab_paste, tab_upload = st.tabs([
    "🔍 关键词搜索（推荐）", "链接抓取", "智能粘贴", "手动粘贴", "上传文件",
])

# ── 关键词搜索 → 自动入库 ─────────────────────────────────
with tab_search:
    st.markdown(
        "输入关键词，AI 会全网搜索最新岗位，结构化后**批量入库到「岗位池」**。"
        "（依赖 Claude 的 web_search 能力，仅 Anthropic 官方 Provider 支持实时搜索；"
        "其他 provider 会 fallback 到模型训练数据推测）"
    )

    from config import settings as _settings_search

    _profile = _settings_search.user_profile or {}
    _career = _profile.get("career", {}) or {}
    _default_keywords = ", ".join(_career.get("jd_keywords", []) or _career.get("target_roles", []))

    sc1, sc2 = st.columns([2, 1])
    with sc1:
        search_kw_str = st.text_input(
            "搜索关键词（逗号分隔）",
            value=_default_keywords,
            placeholder="例：AI 增长运营, 海外增长, 26 届校招",
            help="至少 1 个关键词；多个关键词用逗号分隔。AI 会自动组合搜索。",
            key="search_kw_input",
        )
    with sc2:
        search_max = st.number_input("最多返回", min_value=5, max_value=30, value=15, step=5, key="search_max")

    with st.expander("高级：按 P0 公司 / 排除公司精调搜索", expanded=False):
        _p0_default = "\n".join(_career.get("target_companies_p0", []))
        _ex_default = "\n".join(_career.get("excluded_companies", []))
        adv_p0 = st.text_area("P0 公司白名单（每行一个）", value=_p0_default, height=80, key="search_p0")
        adv_ex = st.text_area("排除公司（每行一个）", value=_ex_default, height=80, key="search_excluded")

    if st.button("🔍 开始搜索", type="primary", key="do_keyword_search",
                 disabled=not _settings_search.has_anthropic_key):
        kws = [k.strip() for k in search_kw_str.split(",") if k.strip()]
        if not kws:
            alert_danger("请至少输入一个关键词。")
        else:
            try:
                from services.job_search import search_and_extract
                with st.spinner(f"AI 搜索中（约 30-60 秒 · 关键词: {', '.join(kws)}）..."):
                    results = search_and_extract(
                        keywords=kws,
                        target_roles=_career.get("target_roles", []),
                        target_companies_p0=[c.strip() for c in adv_p0.splitlines() if c.strip()],
                        excluded_companies=[c.strip() for c in adv_ex.splitlines() if c.strip()],
                        max_results=int(search_max),
                    )
                st.session_state["search_results"] = results
                alert_success(f"✓ 找到 {len(results)} 个匹配岗位。下方预览后可批量入库。")
            except Exception as e:
                alert_danger(f"搜索失败：{type(e).__name__}: {e}")

    if not _settings_search.has_anthropic_key:
        alert_warning("需要先在「系统设置」填 API Key。")

    # 搜索结果预览
    _results = st.session_state.get("search_results", [])
    if _results:
        st.markdown(f"### 搜索结果预览（{len(_results)} 条）")
        import pandas as _pd
        _df_preview = _pd.DataFrame(_results)[
            ["company", "position", "city", "priority", "match_score", "link_type", "notes", "link"]
        ]
        _df_preview.columns = ["公司", "岗位", "城市", "优先级", "匹配分", "链接类型", "备注", "URL"]
        st.dataframe(_df_preview, use_container_width=True, hide_index=True)

        ins_col, clr_col = st.columns([2, 1])
        with ins_col:
            if st.button(f"📥 把这 {len(_results)} 条入库到岗位池", type="primary", key="bulk_insert_jobs"):
                try:
                    from services.job_search import insert_jobs_to_pool
                    stats = insert_jobs_to_pool(_settings_search.db_full_path, _results)
                    alert_success(
                        f"✓ 入库完成：新增 {stats['inserted']} · 跳过重复 {stats['skipped']}"
                        + (f" · 错误 {len(stats['errors'])}" if stats['errors'] else "")
                    )
                    if stats['errors']:
                        with st.expander("查看错误详情"):
                            for e in stats['errors']:
                                st.text(e)
                    st.session_state["search_results"] = []
                except Exception as e:
                    alert_danger(f"入库失败：{type(e).__name__}: {e}")
        with clr_col:
            if st.button("清除搜索结果", key="clear_search_results"):
                st.session_state["search_results"] = []
                st.rerun()

# ── 链接抓取 ────────────────────────────────────────────────
with tab_url:
    st.markdown(
        "输入招聘链接，系统自动抓取职位信息。支持 **Moka HR（官网）**、"
        "**飞书招聘**、**Boss 直聘**、**拉勾**、**智联**、**猎聘** 等平台。"
    )

    url_input = st.text_input(
        "职位链接",
        key="scrape_url",
        placeholder="https://app.mokahr.com/campus_apply/... 或 https://xxx.jobs.feishu.cn/...",
    )

    st.caption("Moka、飞书、Boss 等 SPA 站点需要安装 Playwright 才能抓取。未安装时请使用「智能粘贴」。")

    col_opts1, col_opts2 = st.columns(2)
    with col_opts1:
        use_playwright = st.checkbox("Playwright 浏览器渲染", value=True,
                                     help="Moka/飞书/Boss 等 SPA 站点必须启用。安装：pip install playwright && playwright install chromium")
    with col_opts2:
        use_ai = st.checkbox("AI 辅助提取", value=True,
                             help="当常规解析失败时，用 Claude 从页面文本中智能提取职位信息")

    if st.button("开始抓取", type="primary", key="scrape_btn"):
        if not url_input:
            alert_danger("请输入职位链接。")
        else:
            with st.spinner("正在抓取职位信息..."):
                from services.jd_scraper import scrape_jd
                scraped = scrape_jd(url_input, use_playwright=use_playwright, use_ai=use_ai)

            if scraped.success:
                alert_success(f"抓取成功！渠道：{scraped.job_type}")
                st.session_state["scraped_result"] = scraped
            else:
                alert_danger(f"抓取失败：{scraped.error or '未能提取到有效内容'}")
                if scraped.raw_text:
                    st.session_state["scraped_result"] = scraped
                    alert_info("部分内容已抓取，你可以在下方手动编辑补充。")

    # 抓取结果编辑区
    if "scraped_result" in st.session_state:
        scraped = st.session_state["scraped_result"]
        divider()
        apple_section_heading("抓取结果（可编辑）")

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            s_company = st.text_input("公司名称", value=scraped.company, key="s_company")
            s_title = st.text_input("职位名称", value=scraped.title, key="s_title")
        with col_info2:
            s_location = st.text_input("工作地点", value=scraped.location, key="s_location")
            s_job_type = st.text_input("渠道类型", value=scraped.job_type, key="s_job_type")

        s_raw_text = st.text_area(
            "职位描述全文",
            value=scraped.raw_text,
            height=400,
            key="s_raw_text",
        )

        # 显示额外信息
        extras = []
        if scraped.salary:
            extras.append(f"薪资：{scraped.salary}")
        if scraped.experience:
            extras.append(f"经验：{scraped.experience}")
        if scraped.education:
            extras.append(f"学历：{scraped.education}")
        if extras:
            st.caption("  |  ".join(extras))

        col_save, col_clear = st.columns([3, 1])
        with col_save:
            if st.button("保存到 JD 库", type="primary", key="scrape_save"):
                if not s_company or not s_title or not s_raw_text:
                    alert_danger("公司名称、职位名称和职位描述为必填项。")
                else:
                    jd_id = execute(
                        """INSERT INTO job_descriptions
                           (company, title, location, raw_text, source_url, notes)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (s_company, s_title, s_location or None, s_raw_text,
                         scraped.source_url or None,
                         f"渠道: {s_job_type}" if s_job_type else None),
                    )
                    alert_success(f"已保存！JD #{jd_id} — {s_company} / {s_title}")
                    del st.session_state["scraped_result"]
        with col_clear:
            if st.button("清除结果", key="scrape_clear"):
                del st.session_state["scraped_result"]
                st.rerun()

    # 批量抓取区
    divider()
    with st.expander("批量抓取（多个链接）"):
        st.markdown("每行一个链接，系统会逐个抓取。")
        batch_urls = st.text_area("链接列表", height=150, key="batch_urls",
                                   placeholder="https://app.mokahr.com/...\nhttps://xxx.jobs.feishu.cn/...\nhttps://www.zhipin.com/...")

        if st.button("批量抓取", key="batch_scrape_btn"):
            urls = [u.strip() for u in batch_urls.strip().splitlines() if u.strip()]
            if not urls:
                alert_danger("请输入至少一个链接。")
            else:
                progress = st.progress(0)
                results = []
                for i, u in enumerate(urls):
                    st.caption(f"正在抓取 ({i+1}/{len(urls)}): {u[:60]}...")
                    from services.jd_scraper import scrape_jd
                    r = scrape_jd(u, use_playwright=use_playwright, use_ai=use_ai)
                    results.append(r)
                    progress.progress((i + 1) / len(urls))

                # 显示结果摘要
                success_count = 0
                for r in results:
                    if r.success and r.company and r.title and r.raw_text:
                        jd_id = execute(
                            """INSERT INTO job_descriptions
                               (company, title, location, raw_text, source_url, notes)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (r.company, r.title, r.location or None, r.raw_text,
                             r.source_url or None,
                             f"渠道: {r.job_type}" if r.job_type else None),
                        )
                        success_count += 1
                        alert_success(f"JD #{jd_id} — {r.company} / {r.title} ({r.job_type})")
                    else:
                        alert_danger(f"{r.source_url[:50]}... — {r.error or '提取不完整，需手动补充'}")

                alert_info(f"批量抓取完成：{success_count}/{len(urls)} 成功")

# ── 智能粘贴（AI 解析）──────────────────────────────────────
with tab_smart_paste:
    st.markdown(
        "**不用安装任何工具！** 在浏览器中打开招聘页面 → **Cmd+A 全选** → **Cmd+C 复制** → 粘贴到下方。\n\n"
        "AI 会自动从粘贴的内容中识别出岗位名称、公司、职位描述等信息。"
    )

    smart_url = st.text_input("原始链接（可选，用于记录来源和识别渠道）", key="smart_url",
                               placeholder="https://app.mokahr.com/...")

    smart_text = st.text_area(
        "粘贴页面全部内容",
        height=350,
        key="smart_text",
        placeholder="在招聘页面按 Cmd+A 全选，Cmd+C 复制，然后在这里 Cmd+V 粘贴...",
    )

    if st.button("AI 智能解析", type="primary", key="smart_parse_btn"):
        if not smart_text or len(smart_text.strip()) < 20:
            alert_danger("请粘贴页面内容（至少 20 个字符）。")
        else:
            with st.spinner("AI 正在识别职位信息..."):
                from services.jd_scraper import parse_pasted_jd
                parsed = parse_pasted_jd(smart_text, smart_url)

            if parsed.success:
                alert_success(f"解析成功！")
                st.session_state["smart_parsed"] = parsed
            else:
                alert_danger(f"解析失败：{parsed.error or '未能识别出有效的职位描述'}")

    if "smart_parsed" in st.session_state:
        sp = st.session_state["smart_parsed"]
        divider()
        apple_section_heading("解析结果（可编辑）")

        sp_col1, sp_col2 = st.columns(2)
        with sp_col1:
            sp_company = st.text_input("公司名称", value=sp.company, key="sp_company")
            sp_title = st.text_input("职位名称", value=sp.title, key="sp_title")
        with sp_col2:
            sp_location = st.text_input("工作地点", value=sp.location, key="sp_location")
            sp_type = st.text_input("渠道类型", value=sp.job_type, key="sp_type")

        sp_raw = st.text_area("职位描述", value=sp.raw_text, height=350, key="sp_raw")

        extras = []
        if sp.salary:
            extras.append(f"薪资：{sp.salary}")
        if sp.experience:
            extras.append(f"经验：{sp.experience}")
        if sp.education:
            extras.append(f"学历：{sp.education}")
        if extras:
            st.caption("  |  ".join(extras))

        sp_save_col, sp_clear_col = st.columns([3, 1])
        with sp_save_col:
            if st.button("保存到 JD 库", type="primary", key="sp_save"):
                if not sp_company or not sp_title or not sp_raw:
                    alert_danger("公司名称、职位名称和职位描述为必填项。")
                else:
                    jd_id = execute(
                        """INSERT INTO job_descriptions
                           (company, title, location, raw_text, source_url, notes)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (sp_company, sp_title, sp_location or None, sp_raw,
                         sp.source_url or None,
                         f"渠道: {sp_type}" if sp_type else None),
                    )
                    alert_success(f"已保存！JD #{jd_id} — {sp_company} / {sp_title}")
                    del st.session_state["smart_parsed"]
        with sp_clear_col:
            if st.button("清除", key="sp_clear"):
                del st.session_state["smart_parsed"]
                st.rerun()


# ── 手动粘贴 ────────────────────────────────────────────────
with tab_paste:
    company = st.text_input("公司名称", key="paste_company")
    job_title = st.text_input("职位名称", key="paste_title")
    location = st.text_input("工作地点（可选）", key="paste_location")
    source_url = st.text_input("职位链接（可选）", key="paste_url")
    raw_text = st.text_area("职位描述全文", height=300, key="paste_text",
                            placeholder="在此粘贴完整的职位描述...")

    if st.button("保存 JD", type="primary", key="paste_save"):
        if not company or not job_title or not raw_text:
            alert_danger("公司名称、职位名称和职位描述为必填项。")
        else:
            jd_id = execute(
                """INSERT INTO job_descriptions (company, title, location, raw_text, source_url)
                   VALUES (?, ?, ?, ?, ?)""",
                (company, job_title, location or None, raw_text, source_url or None),
            )
            alert_success(f"已保存！JD #{jd_id} — {company} / {job_title}")
# ── 上传文件 ────────────────────────────────────────────────
with tab_upload:
    st.markdown("支持 **.txt**、**.pdf**、**.docx** 格式。上传后自动提取文本内容，你可以编辑后再保存。")

    uploaded = st.file_uploader(
        "选择文件",
        type=["txt", "pdf", "docx"],
        key="upload_file",
    )

    if uploaded:
        st.caption(f"{uploaded.name}  |  {uploaded.size:,} 字节")

        with st.spinner("正在解析文件内容..."):
            extracted = extract_text(uploaded)

        if extracted:
            alert_success(f"成功提取 {len(extracted):,} 个字符")

            divider()
            up_company = st.text_input("公司名称", key="up_company")
            up_title = st.text_input("职位名称", key="up_title")
            up_location = st.text_input("工作地点（可选）", key="up_location")

            edited_text = st.text_area(
                "提取的内容（可编辑）",
                value=extracted,
                height=400,
                key="up_extracted",
            )

            if st.button("保存 JD", type="primary", key="upload_save"):
                if not up_company or not up_title or not edited_text:
                    alert_danger("公司名称、职位名称和描述内容为必填项。")
                else:
                    jd_id = execute(
                        """INSERT INTO job_descriptions (company, title, location, raw_text)
                           VALUES (?, ?, ?, ?)""",
                        (up_company, up_title, up_location or None, edited_text),
                    )
                    alert_success(f"已保存！JD #{jd_id} — {up_company} / {up_title}")
        else:
            alert_warning("未能从文件中提取到文本内容，请检查文件是否有效。")
