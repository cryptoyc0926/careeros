"""邮件撰写 — 起草、模板预填、保存和发送。"""

import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models.database import query, execute
from config import settings
from components.ui import page_header, section_title, divider, apple_section_heading, alert_success, alert_danger

page_header("邮件撰写", subtitle="让邮件有你自己的语气")

# ── 模板定义 ────────────────────────────────────────────────
TEMPLATES = {
    "自定义": {"subject": "", "body": ""},
    "求职申请": {
        "subject": "求职申请 — {role} | {name}",
        "body": """{manager}您好，

我在{source}上看到贵司正在招聘{role}一职，非常感兴趣。

我有{years}年相关经验，核心优势包括：
- {highlight_1}
- {highlight_2}

附件为我的简历，期待有机会进一步沟通。

{name}
{phone}""",
    },
    "跟进（第3天）": {
        "subject": "Re: 求职申请 — {role} | {name}",
        "body": """{manager}您好，

上周我提交了{role}岗位的申请，想跟进一下进展。
如果需要任何补充材料，请随时告知。

{name}""",
    },
    "跟进（第7天）": {
        "subject": "Re: 求职申请 — {role} | {name}",
        "body": """{manager}您好，

我之前申请了贵司{role}的职位，距离上次沟通已过一周。
仍然对这个机会非常感兴趣，不知是否方便安排一次简短的电话交流？

{name}""",
    },
}

# ── 关联 JD 选择 ────────────────────────────────────────────
jds = query("SELECT id, company, title FROM job_descriptions ORDER BY created_at DESC")
jd_options = {"不关联": None}
for r in jds:
    jd_options[f"#{r['id']} — {r['company']} / {r['title']}"] = r["id"]

linked_jd = st.selectbox("关联职位（可选）", list(jd_options.keys()))
linked_jd_id = jd_options[linked_jd]

# ── 模板选择 ────────────────────────────────────────────────
template_name = st.selectbox("邮件模板", list(TEMPLATES.keys()))
template = TEMPLATES[template_name]

# ── 撰写表单 ────────────────────────────────────────────────
recipient = st.text_input("收件人邮箱")
subject = st.text_input("主题", value=template["subject"])
body = st.text_area("正文", value=template["body"], height=250,
                     help="模板中的 {变量} 请替换为实际内容")

col_draft, col_send = st.columns(2)

with col_draft:
    if st.button("保存草稿", use_container_width=True):
        if not recipient or not subject or not body:
            alert_danger("收件人、主题和正文都是必填项。")
        else:
            execute(
                """INSERT INTO email_queue (application_id, recipient, subject, body_html, template_id, status)
                   VALUES (?, ?, ?, ?, ?, 'draft')""",
                (linked_jd_id, recipient, subject, body, template_name),
            )
            alert_success("草稿已保存")

with col_send:
    if st.button("立即发送", type="primary", use_container_width=True):
        if not recipient or not subject or not body:
            alert_danger("收件人、主题和正文都是必填项。")
        elif not settings.has_smtp:
            alert_danger("SMTP 未配置，请在 .env 中设置 SMTP_USER 和 SMTP_PASSWORD。")
        else:
            try:
                msg = MIMEMultipart()
                msg["From"] = settings.smtp_user
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain", "utf-8"))

                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)

                # 记录到数据库
                execute(
                    """INSERT INTO email_queue (application_id, recipient, subject, body_html, template_id, status, sent_at)
                       VALUES (?, ?, ?, ?, ?, 'sent', datetime('now'))""",
                    (linked_jd_id, recipient, subject, body, template_name),
                )
                alert_success("邮件已发送！")
            except Exception as e:
                alert_danger(f"发送失败: {e}")

# ── 邮件记录 ────────────────────────────────────────────────
divider()
apple_section_heading("邮件记录")

queue = query(
    "SELECT id, recipient, subject, status, template_id, sent_at, created_at FROM email_queue ORDER BY created_at DESC LIMIT 20"
)
if queue:
    for row in queue:
        st.markdown(f"**{row['subject']}** → {row['recipient']}")
        st.caption(f"状态: {row['status']} | 模板: {row['template_id'] or '无'} | {row['created_at'][:16]}")
else:
    st.caption("暂无邮件记录。")
