"""设置 — 个人画像 + 系统配置 + 测试连接。"""

import streamlit as st
import os
import json
from pathlib import Path
from config import settings
from components.ui import (
    page_shell_header, section_title, divider, badge, apple_section_heading,
    path_row_card, alert_success, alert_warning, alert_danger, alert_info,
)
from services.action_status import format_action_status_caption, get_all_action_status, record_action_status
from services.provider_health import ping_current_provider

page_shell_header(
    title="系统设置",
    subtitle="配置个人画像、API 与系统路径",
    right_hint=("AI Provider · 已连接" if settings.has_anthropic_key else "AI Provider · 未配置"),
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


# ── LLM API 配置（多 Provider）──────────────────────────
apple_section_heading("大模型 API 配置", subtitle="支持 Claude / Kimi / 智谱 GLM / DeepSeek 等多家 Anthropic 兼容端点")

current_env = _read_env()

_PROVIDERS = {
    "codex": {
        "label":     "Codex 免费共享（默认 · 无需注册）",
        "base_url":  "https://navacodex.shop/v1",
        "model":     "gpt-5.4",
        "key_link":  "https://navacodex.shop/register",
        "hint":      "CareerOS 默认 Provider · 无需填 Key 直接用（作者共享余额 · 用完为止）· 想用自己的也可以填下面",
        "wire":      "openai",
    },
    "anthropic": {
        "label":     "Claude (Anthropic 官方)",
        "base_url":  "",
        "model":     "claude-sonnet-4-6",
        "key_link":  "https://console.anthropic.com/",
        "hint":      "免费 $5 额度；支持所有最新 Claude 模型。",
        "wire":      "anthropic",
    },
    "openai": {
        "label":     "OpenAI (官方)",
        "base_url":  "https://api.openai.com/v1",
        "model":     "gpt-4o-mini",
        "key_link":  "https://platform.openai.com/api-keys",
        "hint":      "OpenAI 官方 · GPT-4o / 4o-mini 便宜好用。",
        "wire":      "openai",
    },
    "kimi": {
        "label":     "Kimi (月之暗面)",
        "base_url":  "https://api.moonshot.cn/anthropic",
        "model":     "kimi-k2-0905-preview",
        "key_link":  "https://platform.moonshot.cn/console/api-keys",
        "hint":      "国内访问稳定；长上下文支持；需充值。",
        "wire":      "anthropic",
    },
    "glm": {
        "label":     "智谱 GLM-4.6",
        "base_url":  "https://open.bigmodel.cn/api/anthropic",
        "model":     "glm-4.6",
        "key_link":  "https://bigmodel.cn/usercenter/apikeys",
        "hint":      "国产大模型；Anthropic 兼容 API；新用户送额度。",
        "wire":      "anthropic",
    },
    "deepseek": {
        "label":     "DeepSeek",
        "base_url":  "https://api.deepseek.com/anthropic",
        "model":     "deepseek-chat",
        "key_link":  "https://platform.deepseek.com/api_keys",
        "hint":      "性价比最高；推理能力强。",
        "wire":      "anthropic",
    },
    "proxy": {
        "label":     "自定义代理 / 其他兼容端点",
        "base_url":  "",
        "model":     "claude-sonnet-4-6",
        "key_link":  "",
        "hint":      "任何兼容 Anthropic API 的代理，自己填 base_url 和 model。",
        "wire":      "anthropic",
    },
}

# 读取当前 provider（优先 session_state > .env > settings 默认值）
_current_provider = (
    st.session_state.get("LLM_PROVIDER")
    or current_env.get("LLM_PROVIDER")
    or settings.llm_provider
).lower()
if _current_provider not in _PROVIDERS:
    _current_provider = "codex"

# 云端 BYO-Key 提示
if settings.demo_mode:
    alert_info(
        "**BYO-Key 模式**：你在下面填的 API Key 只存在当前浏览器会话，**关闭页面就清空**（零数据泄露风险）。"
        "如需长期保存，建议本地部署：`git clone` 后在 `web/.env` 里填 Key。"
    )

with st.form("api_config"):
    provider_keys = list(_PROVIDERS.keys())
    provider = st.selectbox(
        "选择 LLM Provider",
        options=provider_keys,
        index=provider_keys.index(_current_provider),
        format_func=lambda k: _PROVIDERS[k]["label"],
        help="选对应的大模型服务商，会自动填入 base_url 和默认模型名。",
    )
    _p = _PROVIDERS[provider]
    st.caption(f"💡 {_p['hint']}" + (f" [申请 Key →]({_p['key_link']})" if _p["key_link"] else ""))

    # 安全：永不把真实 Key 预填到 input value（DOM 可读）
    # 显示当前状态 + 掩码；用户留空则保留，输入新值才覆盖
    _existing_key = st.session_state.get("ANTHROPIC_API_KEY") or current_env.get("ANTHROPIC_API_KEY", "")
    if _existing_key:
        st.caption(f"当前 Key：`{settings.masked_key(_existing_key)}` · 留空保持不变，输入新 Key 覆盖")
    api_key = st.text_input(
        "API Key",
        value="",
        type="password",
        placeholder="粘贴新 Key 或留空保持当前 Key",
        help="BYO-Key 模式下只存在当前浏览器会话。留空保持现有 Key；输入非空值才会覆盖。",
    )
    base_url = st.text_input(
        "API 端点（base_url）",
        value=st.session_state.get("ANTHROPIC_BASE_URL") or current_env.get("ANTHROPIC_BASE_URL", "") or _p["base_url"],
        help="留空用 Anthropic 官方。其他 provider 会自动填对应端点。",
        placeholder=_p["base_url"] or "https://api.anthropic.com",
    )
    model = st.text_input(
        "模型名称",
        value=st.session_state.get("CLAUDE_MODEL") or current_env.get("CLAUDE_MODEL", "") or _p["model"],
        help="每家 provider 的可用模型名不同，参考下面提示",
        placeholder=_p["model"],
    )

    if st.form_submit_button("保存 API 配置", type="primary"):
        # BYO-Key / DEMO_MODE：只写 session_state（云端 FS 只读）
        # 本地模式：同时写 session_state + .env（永久保存）
        # API Key 特殊处理：留空保持现有，输入非空值才覆盖
        _api_key_effective = api_key.strip() if api_key and api_key.strip() else _existing_key

        st.session_state["LLM_PROVIDER"]      = provider
        st.session_state["ANTHROPIC_API_KEY"] = _api_key_effective
        st.session_state["ANTHROPIC_BASE_URL"] = base_url
        st.session_state["CLAUDE_MODEL"]      = model

        _can_write_env = not settings.demo_mode
        if _can_write_env:
            try:
                current_env["LLM_PROVIDER"]       = provider
                current_env["ANTHROPIC_API_KEY"]  = _api_key_effective
                current_env["ANTHROPIC_BASE_URL"] = base_url
                current_env["CLAUDE_MODEL"]      = model
                _write_env(current_env)
                alert_success(f"配置已保存到当前会话 + .env（Provider: {_p['label']}）")
            except Exception as e:
                alert_success(f"配置已保存到当前会话（Provider: {_p['label']}）· .env 写入失败：{e}")
        else:
            alert_success(f"配置已保存到当前会话（Provider: {_p['label']}）· 关闭页面后清空")

# 公开池状态（Codex 且用户没填 Key 时显示）
_using_shared_pool = (
    settings.llm_provider == "codex"
    and not st.session_state.get("ANTHROPIC_API_KEY")
    and bool(settings.codex_shared_key)
)
if _using_shared_pool:
    try:
        from services.llm_client import get_pool_spent_usd
        _spent = get_pool_spent_usd()
        alert_info(
            f"**免费试用中** · 你正在使用 CareerOS 公开共享 Key（无需注册、无需填 Key、不做拦截）。"
            f"本次会话已消耗约 `${_spent:.4f}` · 功能完全放开，不满意随时到这里填自己的 Key。"
            f"[如需自己兑换 Key 请点这里 →](https://navacodex.shop/register)"
        )
    except Exception:
        pass

# 状态指示（用 badge 组件替代 emoji）
if settings.has_anthropic_key:
    _cur_p = _PROVIDERS.get(settings.llm_provider, _PROVIDERS["anthropic"])
    st.markdown(
        badge("已连接", "success") +
        f' <span style="font-size:13px;color:#1d1d1f">{_cur_p["label"]} · {settings.masked_key(settings.anthropic_api_key)}</span>',
        unsafe_allow_html=True,
    )
    if settings.has_custom_base_url:
        st.caption(f"端点：{settings.anthropic_base_url}")
    st.caption(f"当前模型：{settings.claude_model}")
else:
    st.markdown(badge("未配置", "danger"), unsafe_allow_html=True)
    st.caption("填入 API Key 后才能使用 AI 生成功能。")

# ── 测试连接按钮 ──────────────────────────────────────────
col_test, _ = st.columns([1, 3])
with col_test:
    if st.button("测试连接", disabled=not settings.has_anthropic_key, help="发送一次最小 API 调用，验证 Key / 端点 / 模型是否可用"):
        record_action_status(st.session_state, "provider_ping", "running", "正在测试连接")
        result = ping_current_provider()
        if result.ok:
            record_action_status(
                st.session_state,
                "provider_ping",
                "success",
                f"{result.label} · {result.model} · 回复：{result.reply[:40]}",
            )
            alert_success(f"连接成功 · 模型 `{result.model}` 可用 · 回复：{result.reply[:40]}")
        else:
            record_action_status(st.session_state, "provider_ping", result.status, result.message)
            alert_danger(result.message)
    _provider_ping_caption = format_action_status_caption(st.session_state, "provider_ping")
    if _provider_ping_caption:
        st.caption(_provider_ping_caption)

# ── SMTP 邮件配置 ─────────────────────────────────────────
divider()
apple_section_heading("邮件 SMTP 配置")

with st.form("smtp_config"):
    smtp_host = st.text_input("SMTP 服务器", value=current_env.get("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = st.text_input("SMTP 端口", value=current_env.get("SMTP_PORT", "587"))
    smtp_user = st.text_input("SMTP 用户名（邮箱地址）", value=current_env.get("SMTP_USER", ""))
    # 安全：SMTP 密码同样不预填真实值
    _existing_smtp_pass = current_env.get("SMTP_PASSWORD", "")
    if _existing_smtp_pass:
        st.caption(f"当前密码：`{settings.masked_key(_existing_smtp_pass)}` · 留空保持不变，输入新密码覆盖")
    smtp_pass = st.text_input(
        "SMTP 密码 / 应用专用密码",
        value="",
        type="password",
        placeholder="粘贴新密码或留空保持当前密码",
    )

    if st.form_submit_button("保存邮件配置"):
        current_env["SMTP_HOST"] = smtp_host
        current_env["SMTP_PORT"] = smtp_port
        current_env["SMTP_USER"] = smtp_user
        # 留空保留现有密码
        current_env["SMTP_PASSWORD"] = smtp_pass.strip() if smtp_pass and smtp_pass.strip() else _existing_smtp_pass
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

# ══════════════════════════════════════════════════════════
# 数据备份：导出所有数据到 JSON / 从 JSON 导入
# 云端部署上这是唯一的数据持久化方式（Cloud FS 只读/重启丢数据）
# ══════════════════════════════════════════════════════════
divider()
apple_section_heading(
    "数据备份与恢复",
    subtitle="把所有岗位/简历/投递记录导出成一个 JSON 文件保存到本地，下次打开再导入",
)

alert_info(
    "**为什么需要这个？** 在 Streamlit Cloud / HF Space 上运行时，应用重启会丢失所有数据。"
    "用完点「导出所有数据」下载 JSON 到你的本地文件夹（iCloud / OneDrive / Google Drive 同步盘都行），"
    "下次打开应用时「从文件导入」选它就能恢复 —— **这就是你的本地持久化方案**。"
)

from services.data_sync import export_all_data, import_all_data
from datetime import datetime

bc1, bc2 = st.columns(2)

with bc1:
    st.markdown("**导出数据**")
    if settings.db_full_path.exists():
        try:
            payload = export_all_data(settings.db_full_path, settings.user_profile)
            total_rows = sum(len(v) for v in payload.get("tables", {}).values())
            _stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "下载 careeros_backup_"+_stamp+".json",
                data=json.dumps(payload, ensure_ascii=False, indent=2),
                file_name=f"careeros_backup_{_stamp}.json",
                mime="application/json",
                use_container_width=True,
                help=f"当前快照包含 {total_rows} 行数据，外加个人画像 user_profile",
            )
            st.caption(f"当前待备份：{total_rows} 行数据 · {len(payload.get('tables', {}))} 张表")
        except Exception as e:
            alert_danger(f"导出失败：{e}")
    else:
        st.caption("数据库还未初始化，暂无数据可导出。")

with bc2:
    st.markdown("**从文件导入**")
    uploaded = st.file_uploader(
        "选择 careeros_backup_*.json 文件",
        type=["json"],
        help="从上次「导出数据」下载的文件",
        key="backup_uploader",
    )
    import_mode = st.radio(
        "导入方式",
        options=["merge", "replace"],
        format_func=lambda m: {"merge": "合并（保留现有数据 · 推荐）", "replace": "替换（清空后导入 · 危险）"}[m],
        horizontal=False,
        key="import_mode_radio",
    )
    if uploaded is not None:
        if st.button("确认导入", type="primary", key="do_import"):
            try:
                payload = json.loads(uploaded.read().decode("utf-8"))
                # 先导入 user_profile（如存在）
                if payload.get("user_profile"):
                    settings.save_user_profile(payload["user_profile"])
                # 导入表数据
                stats = import_all_data(settings.db_full_path, payload, mode=import_mode)
                total = sum(stats.values())
                alert_success(
                    f"导入成功：共 {total} 行。"
                    f" 明细：{', '.join(f'{k}={v}' for k, v in stats.items() if v > 0) or '无新增'}"
                )
                st.rerun()
            except Exception as e:
                alert_danger(f"导入失败：{type(e).__name__}: {e}")

# ── 文件路径 ──────────────────────────────────────────────
divider()
apple_section_heading(
    "系统文件路径",
    subtitle="这些是 CareerOS 读写数据的实际位置，通常不需要改",
)

alert_info(
    "**这一栏在看什么？** CareerOS 是纯本地运行的，所有数据都存在下面这些路径里。"
    "「存在」= 已经有该文件/目录；「不存在」= 还没创建（首次使用时正常，数据会在你操作后自动生成）。"
    "云端部署（Streamlit Cloud / HF Space）重启后非持久化目录会丢数据，建议通过 UI 填的信息写回 GitHub 永久化。"
)

if settings.demo_mode:
    paths_data = [
        ("数据库",    "云端临时数据库",
                      settings.db_full_path,
                      "SQLite 单文件，存储所有岗位、简历、投递、面试、素材等"),
        ("主简历",    "主简历数据表",
                      settings.master_resume_full_path,
                      "旧版 YAML 格式主简历（已被 DB 的 resume_master 表取代，可忽略）"),
        ("输出目录",  "云端临时输出目录",
                      settings.output_full_path,
                      "生成的定制简历 PDF / 求职信 / 导出文件存放处"),
        ("项目根目录", "云端应用目录",
                      settings.project_root,
                      "Streamlit 应用代码所在目录"),
    ]
else:
    paths_data = [
        ("数据库",    str(settings.db_full_path.resolve()),
                      settings.db_full_path,
                      "SQLite 单文件，存储所有岗位、简历、投递、面试、素材等"),
        ("主简历",    str(settings.master_resume_full_path.resolve()),
                      settings.master_resume_full_path,
                      "旧版 YAML 格式主简历（已被 DB 的 resume_master 表取代，可忽略）"),
        ("输出目录",  str(settings.output_full_path.resolve()),
                      settings.output_full_path,
                      "生成的定制简历 PDF / 求职信 / 导出文件存放处"),
        ("项目根目录", str(settings.project_root.resolve()),
                      settings.project_root,
                      "Streamlit 应用代码所在目录"),
    ]
for label, display_path, actual_path, desc in paths_data:
    path_row_card(label, display_path, exists=Path(actual_path).exists())
    st.caption(f"　　↳ {desc}")

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
# 最近错误日志（session 级，关闭页面就清空）
# ══════════════════════════════════════════════════════════
divider()
apple_section_heading(
    "最近错误日志",
    subtitle="本次浏览器会话里出现过的最近 20 条错误（关闭页面即清空，不上传任何地方）",
)

_err_buf = st.session_state.get("_error_log") or []
if not _err_buf:
    st.caption("（暂无错误记录）")
else:
    st.caption(f"共 {len(_err_buf)} 条错误。复制下面代码块可完整发给作者提 issue：")
    _log_text = "\n\n".join(f"[{e['t']}]\n{e['msg']}" for e in _err_buf[::-1])
    st.code(_log_text, language="text")
    if st.button("清空错误日志", key="clear_error_log"):
        st.session_state["_error_log"] = []
        st.rerun()

# ══════════════════════════════════════════════════════════
# 最近动作状态（session 级，关闭页面就清空）
# ══════════════════════════════════════════════════════════
divider()
apple_section_heading(
    "最近动作",
    subtitle="本次浏览器会话内按钮和任务的运行状态，便于确认动作是否真的执行。",
)

_all_actions = get_all_action_status(st.session_state)
if not _all_actions:
    st.caption("（暂无动作记录）")
else:
    for key, payload in sorted(
        _all_actions.items(),
        key=lambda item: item[1].get("last_time") or "",
        reverse=True,
    ):
        message = payload.get("message") or ""
        suffix = f" · {message}" if message else ""
        st.markdown(f"- `{key}` · **{payload.get('status', '')}** · {payload.get('last_time', '-')}{suffix}")

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
