"""Cheat Sheet — Company research and talking points."""

import streamlit as st
from config import settings
from components.ui import page_header, section_title, alert_warning, alert_danger

page_header("公司速查表", subtitle="一键生成目标公司情报摘要，面试前必备")


company_name = st.text_input("Company Name")
role_title = st.text_input("Role you're interviewing for")

if st.button("Generate Cheat Sheet", type="primary"):
    if not company_name:
        alert_danger("Enter a company name.")
    elif not settings.has_anthropic_key:
        alert_danger("Claude API key not configured. Go to **Settings**.")
    else:
        alert_warning("⏳ Cheat sheet generation will be implemented in Phase 6 (Module 5 build).")
        with st.expander("Preview: What the cheat sheet will include"):
            st.markdown(f"""
            **{company_name}** — Interview Briefing

            - Company overview (founding, size, funding/revenue)
            - Recent news and product launches
            - Key competitors and positioning
            - Tech stack and engineering culture
            - Company values with your talking points
            - "Why {company_name}?" narrative
            """)
