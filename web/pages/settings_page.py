"""设置 — 个人画像 + 系统配置 + 测试连接。"""

import streamlit as st
import os
from pathlib import Path
from config import settings
from components.ui import (
    page_shell_header, section_title, divider, badge, apple_section_heading,
    path_row_card, alert_success, alert_warning, alert_danger, alert_info,
)

page_shell_header(
    title="系统设置",
    subtitle="配置个人画像、API 与系统路径",
    right_hint=("Claude API · 已连接" if settings.has_anthropic_key else "Claude API · 未配置"),
)

# ══════════════════════════════════════════════════════════
# 个人画像（首次使用的第一步，写入 data/user_profile.yaml）
# ══════════════════════════════════════════════════════════
apple_section_heading("个人画像", subtitle="这些信息会注入简历定制、邮件模板、面试准备的 prompt")

_profile = settings.user_profile or {}
_user = _profile.get("user", {}) or {}
_career = _profile.get("career", {}) or {}

with st.form("user_profile_form"):
    c1, c2 = st.columns(2)
    with c1:
        p_name = st.text_input("中文姓名", value=_user.get("name", ""))
        p_school = st.text_input("学校", value=_user.get("school", ""))
        p_major = st.text_input("专业", value=_user.get("major", ""))
        p_year = st.text_input("毕业年（例 2026）", value=str(_user.get("graduation_year", "")))
    with c2:
        p_name_en = st.text_input("英文名（可选）", value=_user.get("name_en", ""))
        p_email = st.text_input("邮箱", value=_user.get("email", ""))
        p_phone = st.text_input("手机", value=_user.get("phone", ""))
        p_city = st.text_input("目标城市", value=_user.get("city", ""))

    p_target_roles = st.text_input(
        "目标岗位方向（逗号分隔，按优先级）",
        value=", ".join(_career.get("target_roles", [])),
        help="例：AI 增长运营, 产品运营, 数据分析",
    )
    p_highlights = st.text_area(
        "一句话核心亮点",
        value=_career.get("highlights", ""),
        help="会注入到邮件/内推模板的 {highlights} 占位",
        height=80,
    )

    if st.form_submit_button("保存画像", type="primary"):
        try:
            new_profile = {
                "user": {
                    "name": p_name.strip(),
                    "name_en": p_name_en.strip(),
                    "school": p_school.strip(),
                    "major": p_major.strip(),
                    "graduation_year": int(p_year) if p_year.strip().isdigit() else p_year.strip(),
                    "email": p_email.strip(),
                    "phone": p_phone.strip(),
                    "city": p_city.strip(),
                },
                "career": {
                    **_career,
                    "target_roles": [r.strip() for r in p_target_roles.split(",") if r.strip()],
                    "highlights": p_highlights.strip(),
                },
            }
            settings.save_user_profile(new_profile)
            # 清缓存让 settings.user_profile 读到新值
            from config import get_settings
            get_settings.cache_clear()
            alert_success("个人画像已保存到 data/user_profile.yaml")
        except Exception as e:
            alert_danger(f"保存失败：{e}")

if not settings.has_user_profile:
    alert_info("首次使用：填写上面的字段后点「保存画像」即可，系统会自动创建 user_profile.yaml。")

divider()

# ── .env 文件路径 ──────────────────────────────────────────
env_path = settings.project_root / ".env"


def _read_env() -> dict:
    """读取 .env 文件为字典。"""
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env_vars[key.strip()] = val.strip()
    return env_vars


def _write_env(env_vars: dict):
    """将字典写回 .env 文件。"""
    lines = []
    for k, v in env_vars.items():
        lines.append(f"{k}={v}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Claude API 配置 ───────────────────────────────────────
apple_section_heading("Claude API 配置")

current_env = _read_env()

with st.form("api_config"):
    api_key = st.text_input(
        "API Key",
        value=current_env.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Anthropic API Key 或自定义代理的 Key",
    )
    base_url = st.text_input(
        "API 端点（留空使用官方地址）",
        value=current_env.get("ANTHROPIC_BASE_URL", ""),
        help="自定义 API 代理地址，如 http://cccai.cfd",
    )
    model = st.text_input(
        "模型名称",
        value=current_env.get("CLAUDE_MODEL", "claude-opus-4-6"),
        help="如 claude-opus-4-6, claude-sonnet-4-5-20250514 等",
    )

    if st.form_submit_button("保存 API 配置", type="primary"):
        current_env["ANTHROPIC_API_KEY"] = api_key
        current_env["ANTHROPIC_BASE_URL"] = base_url
        current_env["CLAUDE_MODEL"] = model
        _write_env(current_env)
        alert_success("API 配置已保存，重启应用后生效。")
        st.caption("提示：Ctrl+C 停止 Streamlit，再重新运行 streamlit run app.py")

# 状态指示（用 badge 组件替代 emoji）
if settings.has_anthropic_key:
    st.markdown(
        badge("已连接", "success") +
        f' <span style="font-size:13px;color:#1d1d1f">{settings.masked_key(settings.anthropic_api_key)}</span>',
        unsafe_allow_html=True,
    )
    if settings.has_custom_base_url:
        st.caption(f"自定义端点：{settings.anthropic_base_url}")
    st.caption(f"当前模型：{settings.claude_model}")
else:
    st.markdown(badge("未配置", "danger"), unsafe_allow_html=True)
    st.caption("填入 API Key 后才能使用 AI 生成功能。")

# ── 测试连接按钮 ──────────────────────────────────────────
col_test, _ = st.columns([1, 3])
with col_test:
    if st.button("测试连接", disabled=not settings.has_anthropic_key, help="发送一次最小 API 调用，验证 Key / 端点 / 模型是否可用"):
        try:
            from anthropic import Anthropic
            client_kwargs = {"api_key": settings.anthropic_api_key}
            if settings.has_custom_base_url:
                client_kwargs["base_url"] = settings.anthropic_base_url
            client = Anthropic(**client_kwargs)
            resp = client.messages.create(
                model=settings.claude_model,
                max_tokens=16,
                messages=[{"role": "user", "content": "ping"}],
            )
            reply = resp.content[0].text if resp.content else ""
            alert_success(f"✓ 连接成功 · 模型 `{settings.claude_model}` 可用 · 回复：{reply[:40]}")
        except Exception as e:
            alert_danger(f"✗ 连接失败：{type(e).__name__} · {str(e)[:200]}")

# ── SMTP 邮件配置 ─────────────────────────────────────────
divider()
apple_section_heading("邮件 SMTP 配置")

with st.form("smtp_config"):
    smtp_host = st.text_input("SMTP 服务器", value=current_env.get("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = st.text_input("SMTP 端口", value=current_env.get("SMTP_PORT", "587"))
    smtp_user = st.text_input("SMTP 用户名（邮箱地址）", value=current_env.get("SMTP_USER", ""))
    smtp_pass = st.text_input("SMTP 密码 / 应用专用密码", value=current_env.get("SMTP_PASSWORD", ""), type="password")

    if st.form_submit_button("保存邮件配置"):
        current_env["SMTP_HOST"] = smtp_host
        current_env["SMTP_PORT"] = smtp_port
        current_env["SMTP_USER"] = smtp_user
        current_env["SMTP_PASSWORD"] = smtp_pass
        _write_env(current_env)
        alert_success("SMTP 配置已保存，重启应用后生效。")

if settings.has_smtp:
    st.markdown(
        badge("已配置", "success") +
        f' <span style="font-size:13px;color:#1d1d1f">{settings.smtp_user} → {settings.smtp_host}:{settings.smtp_port}</span>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(badge("未配置", "muted"), unsafe_allow_html=True)
    st.caption("配置后可直接从系统发送求职邮件。")

# ── 文件路径 ──────────────────────────────────────────────
divider()
apple_section_heading("文件路径")

paths_data = {
    "数据库": str(settings.db_full_path),
    "主简历": str(settings.master_resume_full_path),
    "输出目录": str(settings.output_full_path),
    "项目根目录": str(settings.project_root),
}
for label, path in paths_data.items():
    path_row_card(label, path, exists=Path(path).exists())

# ── 数据库信息 ─────────────────────────────────────────────
divider()
apple_section_heading("数据库")

if settings.db_full_path.exists():
    from models.database import query
    tables = query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    counts = {}
    for t in tables:
        name = t["name"]
        try:
            c = query(f"SELECT COUNT(*) AS c FROM [{name}]")[0]["c"]
            counts[name] = c
        except Exception:
            counts[name] = "?"

    for name, count in counts.items():
        st.text(f"  {name}：{count} 条记录")

    db_size = settings.db_full_path.stat().st_size
    st.caption(f"数据库大小：{db_size:,} 字节")

    # 重置数据库按钮
    divider()
    if st.button("重置数据库", help="删除并重新创建所有表（数据将丢失）"):
        st.session_state["confirm_reset_db"] = True

    if st.session_state.get("confirm_reset_db"):
        alert_warning("确定要重置数据库吗？所有数据将被清除。")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("确认重置", key="danger_reset_db"):
                from scripts.init_db import init_database
                init_database(settings.db_full_path, reset=True)
                st.session_state["confirm_reset_db"] = False
                alert_success("数据库已重置。")
                st.rerun()
        with c2:
            if st.button("取消"):
                st.session_state["confirm_reset_db"] = False
                st.rerun()
else:
    alert_warning("数据库尚未初始化，将在应用启动时自动创建。")

# ══════════════════════════════════════════════════════════
# 目标公司管理（P0 / P1 / 排除清单 + 内推码）
# ══════════════════════════════════════════════════════════
divider()
apple_section_heading("目标公司", subtitle="维护 P0/P1 主攻清单 + 排除清单 + 内推码")

_career_all = (settings.user_profile or {}).get("career", {}) or {}
with st.form("target_companies_form"):
    c1, c2 = st.columns(2)
    with c1:
        v_p0 = st.text_area(
            "P0 主攻公司（每行一个）",
            value="\n".join(_career_all.get("target_companies_p0", [])),
            height=120,
        )
        v_excluded = st.text_area(
            "排除公司（每行一个 · 扫描时自动跳过）",
            value="\n".join(_career_all.get("excluded_companies", [])),
            height=100,
        )
    with c2:
        v_p1 = st.text_area(
            "P1 积极投递（每行一个）",
            value="\n".join(_career_all.get("target_companies_p1", [])),
            height=120,
        )
        v_referral_raw = st.text_area(
            "内推码（每行一条：公司=码）",
            value="\n".join(f"{k}={v}" for k, v in (_career_all.get("referral_codes", {}) or {}).items()),
            height=100,
        )

    if st.form_submit_button("保存目标公司", type="primary"):
        try:
            referral_map = {}
            for line in v_referral_raw.splitlines():
                if "=" in line:
                    k, _, val = line.partition("=")
                    if k.strip():
                        referral_map[k.strip()] = val.strip()
            merged_career = {
                **_career_all,
                "target_companies_p0": [c.strip() for c in v_p0.splitlines() if c.strip()],
                "target_companies_p1": [c.strip() for c in v_p1.splitlines() if c.strip()],
                "excluded_companies": [c.strip() for c in v_excluded.splitlines() if c.strip()],
                "referral_codes": referral_map,
            }
            settings.save_user_profile({
                **(settings.user_profile or {}),
                "career": merged_career,
            })
            from config import get_settings
            get_settings.cache_clear()
            alert_success("目标公司清单已保存。")
        except Exception as e:
            alert_danger(f"保存失败：{e}")
