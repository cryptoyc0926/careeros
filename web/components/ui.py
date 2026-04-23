"""
Career OS — UI 组件库 v4 (Indigo White tokens)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Design 基线：new UI 靛蓝白体系 + Nature 气质

全部 token 从 Appendix A 落地；删除 Instrument Serif；删除左竖条/顶横条系统；
保留所有旧组件名作为 delegate（向后兼容），新代码请使用新组件名。
"""
from __future__ import annotations
import streamlit as st

# ═════════════════════════════════════════════════════════════
#  Appendix A — Design Tokens
# ═════════════════════════════════════════════════════════════

# ── Surface / Background ──（Indigo v1）
BG_PAGE    = "#FFFFFF"            # 主页面底
BG_SURFACE = "#F7F8FA"            # section 分层底
BG_SOFT    = "#FAFBFC"
BG_SUNKEN  = "#EEF1F5"

# ── Text ──（靛蓝黑，可读性最佳）
TEXT_STRONG = "#0B1220"           # H1/H2 主文字
TEXT_BODY   = "#374151"           # 正文
TEXT_MUTED  = "#6B7280"           # 次级
TEXT_DIM    = "rgba(11,18,32,0.48)"

# ── Border ──
BORDER_SOFT   = "#E5E7EB"
BORDER_SOFTER = "rgba(11,18,32,0.04)"
BORDER_FOCUS  = "#3B5BFE"         # ← 靛蓝 focus ring

# ── Accent ──（Indigo #3B5BFE）
ACCENT_BLUE    = "#3B5BFE"
ACCENT_BLUE_HV = "#2A46D8"
ACCENT_INDIGO  = "#1E3AE8"        # chart highlight / 深靛蓝

# ── Semantic ──
SEMANTIC_SUCCESS = "#16a34a"
SEMANTIC_WARNING = "#d97706"
SEMANTIC_DANGER  = "#dc2626"

# ── Shape ──
RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_PILL = "6px", "10px", "14px", "980px"

# ── Shadow ──
SHADOW_CARD = "0 1px 2px rgba(0,0,0,0.04)"
SHADOW_HOVR = "0 8px 24px rgba(0,0,0,0.08)"
# Standard motion easing
EASING_STANDARD = "cubic-bezier(0.4, 0, 0.2, 1)"
SHADOW_HERO = "0 8px 32px rgba(0,0,0,0.06)"

# ── Spacing ──
SP_1, SP_2, SP_3, SP_4 = "4px", "8px", "12px", "16px"
SP_5, SP_6, SP_7, SP_8 = "24px", "32px", "48px", "64px"

# ── Typography ──（Indigo v1: Inter 为首 + 保留 SF/PingFang fallback）
# ⚠️ 单引号包字体名：此常量被 f-string 插入到 inline style="..."，
#    如果内层用双引号会和外层 style="..." 冲突，导致 HTML 属性提前闭合
FONT_SANS = ("'Inter','SF Pro Text','SF Pro Display',-apple-system,BlinkMacSystemFont,"
             "'PingFang SC','Helvetica Neue','Noto Sans SC',sans-serif")

# ── Legacy alias（向后兼容，供未迁移的内页使用）──
FG, MUTED, ACCENT, BORDER, SEC_BG, WHITE = (
    TEXT_STRONG, TEXT_MUTED, ACCENT_BLUE, BORDER_SOFT, BG_PAGE, BG_SURFACE
)
BG_SUB, RADIUS, SHADOW, CARD_PAD = BG_PAGE, RADIUS_LG, SHADOW_CARD, SP_5


# ═════════════════════════════════════════════════════════════
#  Semantic color maps（badge / status 用）
# ═════════════════════════════════════════════════════════════

COLORS = {
    "success": (SEMANTIC_SUCCESS, "rgba(22,163,74,0.08)"),
    "warning": (SEMANTIC_WARNING, "rgba(217,119,6,0.08)"),
    "danger":  (SEMANTIC_DANGER,  "rgba(220,38,38,0.08)"),
    "info":    (ACCENT_BLUE,      "rgba(59,91,254,0.08)"),   # ← 靛蓝 chip 浅底
    "accent":  (ACCENT_BLUE,      "rgba(59,91,254,0.08)"),
    "muted":   (TEXT_MUTED,       "rgba(0,0,0,0.03)"),
    "purple":  ("#7c3aed", "rgba(124,58,237,0.08)"),
    "orange":  ("#ea580c", "rgba(234,88,12,0.08)"),
}

TIER_VARIANT = {"P0": "orange", "P1": "info", "P2": "muted"}

STATUS_VARIANT = {
    "未投递": "muted", "已投递": "info", "笔试中": "warning",
    "面试中": "success", "等待回复": "warning", "已拿offer": "success",
    "已拒绝": "danger", "已放弃": "muted",
    "fetched": "success", "needs_browser": "warning", "pending": "muted",
    "failed": "danger", "blocked": "danger", "manual": "muted",
}


# ═════════════════════════════════════════════════════════════
#  基础工具：badge / divider / empty_state
# ═════════════════════════════════════════════════════════════

def badge(text: str, variant: str = "info") -> str:
    color, bg = COLORS.get(variant, COLORS["info"])
    return (
        f'<span style="background:{bg};color:{color};padding:2px 10px;'
        f'border-radius:{RADIUS_PILL};font-size:11px;font-weight:500;'
        f'white-space:nowrap;display:inline-block;line-height:1.7;'
        f'vertical-align:middle;font-family:{FONT_SANS}">{text}</span>'
    )

def tier_badge(tier: str) -> str:
    return badge(tier, TIER_VARIANT.get(tier, "muted"))

def status_badge(status: str) -> str:
    return badge(status, STATUS_VARIANT.get(status, "muted"))

def jd_status_badge(jd_fetch_mode: str, jd_status: str) -> str:
    if jd_status == "fetched":       return badge("JD 已抓取", "success")
    if jd_status == "needs_browser": return badge("需 Chrome", "warning")
    if jd_fetch_mode == "blocked":   return badge("黑名单", "danger")
    if jd_fetch_mode == "manual":    return badge("手动", "muted")
    if jd_fetch_mode == "auto":      return badge("待抓取", "muted")
    if jd_status == "failed":        return badge("失败", "danger")
    return badge("—", "muted")

def divider() -> None:
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {BORDER_SOFTER};margin:{SP_6} 0">',
        unsafe_allow_html=True,
    )

def empty_state(icon: str, message: str, hint: str = "") -> None:
    """简易空状态（带 emoji 图标，内页表格空时用）。"""
    st.markdown(
        f'<div style="text-align:center;padding:{SP_7} 0;color:{TEXT_MUTED};font-family:{FONT_SANS}">'
        f'<div style="font-size:36px;margin-bottom:{SP_3};opacity:0.65">{icon}</div>'
        f'<div style="font-size:15px;font-weight:500;color:{TEXT_STRONG}">{message}</div>'
        + (f'<div style="font-size:13px;margin-top:{SP_2};color:{TEXT_MUTED}">{hint}</div>' if hint else "")
        + '</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════
#  Appendix E.1 — 新组件（首选使用）
# ═════════════════════════════════════════════════════════════

def page_shell_header(
    title: str,
    subtitle: str = "",
    right_label: str = "",
    right_page: str = "",
    right_hint: str = "",
) -> None:
    """统一内页 header。左：标题+说明；右：可选轻量操作或状态文字。"""
    has_right = bool(right_label or right_hint)
    cols = st.columns([7, 2]) if has_right else (st.container(),)

    with cols[0]:
        st.markdown(
            f'<div style="padding:{SP_1} 0 {SP_4}">'
            f'<h2 style="margin:0;font-size:24px;font-weight:600;'
            f'color:{TEXT_STRONG};letter-spacing:-0.24px;line-height:1.2;'
            f'font-family:{FONT_SANS}">{title}</h2>'
            + (f'<p style="margin:{SP_2} 0 0;font-size:14px;color:{TEXT_MUTED};'
               f'font-family:{FONT_SANS};line-height:1.55">{subtitle}</p>'
               if subtitle else '')
            + '</div>',
            unsafe_allow_html=True,
        )

    if has_right:
        with cols[1]:
            st.markdown(f'<div style="padding-top:{SP_3}"></div>', unsafe_allow_html=True)
            if right_label and right_page:
                if st.button(right_label, use_container_width=True, key=f"psh_{title}_{right_label}"):
                    st.switch_page(right_page)
            elif right_hint:
                st.markdown(
                    f'<p style="font-size:12px;color:{TEXT_MUTED};text-align:right;'
                    f'padding-top:{SP_3};font-family:{FONT_SANS}">{right_hint}</p>',
                    unsafe_allow_html=True,
                )

    st.markdown(
        f'<hr style="border:none;border-top:1px solid {BORDER_SOFTER};margin:0 0 {SP_6}">',
        unsafe_allow_html=True,
    )


def apple_section_heading(title: str, subtitle: str = "") -> None:
    """section 级标题。无 icon。上下留白 SP_7/SP_3。"""
    sub_html = (
        f'<p style="margin:{SP_2} 0 0;font-size:13px;color:{TEXT_MUTED};'
        f'font-family:{FONT_SANS};font-weight:400">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="margin:{SP_7} 0 {SP_4}">'
        f'<h3 style="margin:0;font-size:20px;font-weight:600;color:{TEXT_STRONG};'
        f'letter-spacing:-0.16px;line-height:1.3;font-family:{FONT_SANS}">{title}</h3>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def hero_intro_block(
    eyebrow: str,
    title: str,
    subtitle: str,
    primary: tuple[str, str] | None = None,
    secondary: tuple[str, str] | None = None,
) -> None:
    """居中 Hero。上下结构，与页面底色融合。"""
    st.markdown(
        f'<div style="padding:{SP_7} {SP_5} {SP_5};text-align:center;'
        f'font-family:{FONT_SANS}">'
        f'<div style="font-size:12px;color:{TEXT_MUTED};font-weight:500;'
        f'letter-spacing:0.02em;margin-bottom:{SP_4}">{eyebrow}</div>'
        f'<h1 style="margin:0 0 {SP_4};font-size:32px;font-weight:600;'
        f'color:{TEXT_STRONG};letter-spacing:-0.32px;line-height:1.15;'
        f'font-family:{FONT_SANS};max-width:640px;margin-left:auto;margin-right:auto">'
        f'{title}</h1>'
        f'<p style="margin:0 auto;font-size:17px;color:{TEXT_BODY};'
        f'line-height:1.5;max-width:560px;font-family:{FONT_SANS};'
        f'letter-spacing:-0.08px">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if primary or secondary:
        _spacer, c1, c2, _spacer2 = st.columns([2, 1.4, 1.4, 2])
        if primary:
            with c1:
                if st.button(primary[0], type="primary", use_container_width=True, key=f"hero_p_{primary[0]}"):
                    st.switch_page(primary[1])
        if secondary:
            with c2:
                if st.button(secondary[0], use_container_width=True, key=f"hero_s_{secondary[0]}"):
                    st.switch_page(secondary[1])
    st.markdown(f'<div style="height:{SP_5}"></div>', unsafe_allow_html=True)


def summary_card_hero(value: str | int, label: str, hint: str = "") -> None:
    """首页主数据卡（大号，叙事式）。value 36px，label 15px，hint 13px。"""
    hint_html = (
        f'<div style="font-size:13px;color:{TEXT_MUTED};margin-top:{SP_2};'
        f'font-family:{FONT_SANS};line-height:1.5">{hint}</div>' if hint else ""
    )
    st.markdown(
        f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_6} {SP_5};'
        f'box-shadow:{SHADOW_CARD};font-family:{FONT_SANS};'
        f'min-height:128px;display:flex;flex-direction:column;justify-content:center">'
        f'<div style="font-size:15px;color:{TEXT_MUTED};font-weight:500;'
        f'margin-bottom:{SP_2}">{label}</div>'
        f'<div style="font-size:36px;font-weight:600;color:{TEXT_STRONG};'
        f'letter-spacing:-0.32px;line-height:1;font-variant-numeric:tabular-nums">'
        f'{value}</div>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def soft_stat_card(value: str | int, label: str, hint: str = "") -> None:
    """次级数据卡。无边框装饰条，value 24px。"""
    hint_html = (
        f'<div style="font-size:11px;color:{TEXT_MUTED};margin-top:{SP_1};'
        f'font-family:{FONT_SANS}">{hint}</div>' if hint else ""
    )
    st.markdown(
        f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_4} {SP_4};'
        f'box-shadow:{SHADOW_CARD};font-family:{FONT_SANS};'
        f'min-height:92px;display:flex;flex-direction:column;justify-content:center">'
        f'<div style="font-size:24px;font-weight:600;color:{TEXT_STRONG};'
        f'letter-spacing:-0.24px;line-height:1;font-variant-numeric:tabular-nums">'
        f'{value}</div>'
        f'<div style="font-size:12px;color:{TEXT_MUTED};margin-top:{SP_2};'
        f'font-family:{FONT_SANS}">{label}</div>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def task_action_card(title: str, description: str, page: str) -> None:
    """任务引导卡（横向 3 卡布局），整卡可点，hover 升起。

    注意：<a> 内嵌 <div> 会被 Markdown parser 切成独立 block，
    必须用 <span style="display:block"> 保持 inline token 连续。
    """
    route = "/" + page.replace("pages/", "").replace(".py", "")
    st.markdown(
        f'<a href="{route}" target="_self" class="apple-action-card" '
        f'style="text-decoration:none;'
        f'background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_5};box-shadow:{SHADOW_CARD};'
        f'transition:all 0.22s {EASING_STANDARD};cursor:pointer;font-family:{FONT_SANS};'
        f'min-height:132px;display:flex;flex-direction:column;justify-content:space-between">'
        f'<span style="display:block">'
        f'<span style="display:block;font-size:15px;font-weight:600;color:{TEXT_STRONG};'
        f'margin-bottom:{SP_2};letter-spacing:-0.12px">{title}</span>'
        f'<span style="display:block;font-size:13px;color:{TEXT_MUTED};line-height:1.55">{description}</span>'
        f'</span>'
        f'<span style="display:block;font-size:13px;color:{ACCENT_BLUE};margin-top:{SP_3};font-weight:500">'
        f'开始 →</span>'
        f'</a>',
        unsafe_allow_html=True,
    )


def feature_card(title: str, description: str, page: str) -> None:
    """常用入口卡。title + 一句描述 + 右下角 '进入 →'。

    同 task_action_card：<a> 内部用 <span display:block>，避免块级标签被 parser 切开。
    """
    route = "/" + page.replace("pages/", "").replace(".py", "")
    st.markdown(
        f'<a href="{route}" target="_self" class="apple-feature-card" '
        f'style="text-decoration:none;'
        f'background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_5};box-shadow:{SHADOW_CARD};'
        f'transition:all 0.22s {EASING_STANDARD};cursor:pointer;font-family:{FONT_SANS};'
        f'min-height:112px;display:flex;flex-direction:column;justify-content:space-between">'
        f'<span style="display:block">'
        f'<span style="display:block;font-size:15px;font-weight:600;color:{TEXT_STRONG};'
        f'margin-bottom:{SP_1};letter-spacing:-0.12px">{title}</span>'
        f'<span style="display:block;font-size:13px;color:{TEXT_MUTED};line-height:1.55">{description}</span>'
        f'</span>'
        f'<span style="display:block;font-size:12px;color:{ACCENT_BLUE};margin-top:{SP_3};font-weight:500">'
        f'进入 →</span>'
        f'</a>',
        unsafe_allow_html=True,
    )


def app_footer(text: str = "") -> None:
    """页面底部弱信息。居中小字，无装饰。"""
    st.markdown(
        f'<p style="text-align:center;font-size:12px;color:{TEXT_MUTED};'
        f'padding:{SP_7} 0 {SP_2};font-family:{FONT_SANS};margin:0">{text}</p>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════
#  Appendix G — 新增靛蓝白组件（替代内联 HTML 拼接）
# ═════════════════════════════════════════════════════════════

def funnel_stage_card(label: str, count: int, rate_hint: str = "") -> None:
    """漏斗阶段卡（Indigo 单色 + tabular-nums）。"""
    hint_html = (
        f'<div style="font-size:11px;color:{TEXT_MUTED};margin-bottom:{SP_2};'
        f'font-family:{FONT_SANS}">{rate_hint}</div>'
    ) if rate_hint else f'<div style="height:20px"></div>'
    st.markdown(
        f'{hint_html}'
        f'<div style="background:{BG_SURFACE};padding:{SP_4} {SP_3};'
        f'border-radius:{RADIUS_LG};text-align:center;'
        f'border:1px solid {BORDER_SOFTER};box-shadow:{SHADOW_CARD};'
        f'font-family:{FONT_SANS}">'
        f'<div style="font-size:28px;font-weight:600;color:{TEXT_STRONG};'
        f'letter-spacing:-0.3px;font-variant-numeric:tabular-nums">{count}</div>'
        f'<div style="font-size:12px;color:{TEXT_MUTED};margin-top:{SP_2}">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def diagnostic_alert(severity: str, message: str, copyable: bool = False) -> None:
    """诊断信息条（靛蓝白风格，无 emoji，只用颜色+文字）。

    severity: success | info | warning | danger
    copyable: True 时额外追加一个可复制的 code block（st.code 右上角自带 copy 按钮）
    """
    color, bg = COLORS.get(severity, COLORS["info"])
    st.markdown(
        f'<div style="background:{bg};border:1px solid {BORDER_SOFTER};'
        f'padding:{SP_3} {SP_4};border-radius:{RADIUS_MD};'
        f'font-size:13px;color:{TEXT_STRONG};font-family:{FONT_SANS};'
        f'border-left:3px solid {color};margin:{SP_2} 0">{message}</div>',
        unsafe_allow_html=True,
    )
    # 同时把错误写入 session 错误缓冲，便于在「系统设置」里统一查看最近错误
    if severity == "danger":
        try:
            buf = st.session_state.setdefault("_error_log", [])
            import datetime as _dt
            buf.append({"t": _dt.datetime.now().isoformat(timespec="seconds"), "msg": str(message)[:500]})
            if len(buf) > 20:
                del buf[:-20]
        except Exception:
            pass
    # danger 自动启用 copyable；其他级别按传参
    if copyable or severity == "danger":
        with st.expander("📋 复制错误详情（给作者提 issue 时贴这个）", expanded=False):
            st.code(str(message), language="text")


# alert_* 便捷别名：用于替代原生 st.success / st.info / st.warning / st.error
def alert_success(message: str) -> None:
    diagnostic_alert("success", message)


def alert_info(message: str) -> None:
    diagnostic_alert("info", message)


def alert_warning(message: str) -> None:
    diagnostic_alert("warning", message)


def alert_danger(message: str, copyable: bool = True) -> None:
    diagnostic_alert("danger", message, copyable=copyable)


def score_hero_card(score: int, verdict: str = "", hint: str = "") -> None:
    """匹配分/评分主卡（靛蓝白风格，无饱和色警示）。"""
    st.markdown(
        f'<div style="background:{BG_SURFACE};padding:{SP_5} {SP_6};'
        f'border-radius:{RADIUS_LG};text-align:center;'
        f'border:1px solid {BORDER_SOFTER};box-shadow:{SHADOW_CARD};'
        f'font-family:{FONT_SANS}">'
        f'<div style="font-size:42px;font-weight:600;color:{TEXT_STRONG};'
        f'letter-spacing:-0.5px;font-variant-numeric:tabular-nums;line-height:1">'
        f'{score}<span style="font-size:20px;color:{TEXT_MUTED};margin-left:4px">分</span></div>'
        f'{f"<div style=\"font-size:14px;color:{TEXT_BODY};margin-top:{SP_3}\">{verdict}</div>" if verdict else ""}'
        f'{f"<div style=\"font-size:12px;color:{TEXT_MUTED};margin-top:{SP_2}\">{hint}</div>" if hint else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )


def path_row_card(label: str, path: str, exists: bool = True) -> None:
    """系统路径行（替代硬编码 #fafafc 内联 HTML）。"""
    state = badge("存在", "success") if exists else badge("不存在", "danger")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:{SP_3};padding:{SP_2} 0;'
        f'font-size:13px;color:{TEXT_STRONG};font-family:{FONT_SANS}">'
        f'{state}'
        f'<span style="color:{TEXT_MUTED};min-width:80px">{label}</span>'
        f'<code style="background:{BG_SOFT};padding:2px {SP_2};border-radius:{RADIUS_SM};'
        f'font-size:12px;color:{TEXT_BODY}">{path}</code>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kanban_column_card(company: str, title: str) -> None:
    """看板小卡（pipeline 专用）— 静态卡，无链接。若需整卡点击用 `task_action_card`。

    无内联色，全 token 化。
    """
    st.markdown(
        f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'padding:10px {SP_3};border-radius:{RADIUS_MD};margin:{SP_2} 0;'
        f'box-shadow:{SHADOW_CARD};font-family:{FONT_SANS}">'
        f'<div style="font-size:12px;font-weight:600;color:{TEXT_STRONG}">{company}</div>'
        f'<div style="font-size:11px;color:{TEXT_MUTED};margin-top:2px">{title}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kanban_empty() -> None:
    """看板列空态。"""
    st.markdown(
        f'<div style="color:{TEXT_MUTED};font-size:12px;text-align:center;'
        f'padding:{SP_4} 0;font-family:{FONT_SANS}">暂无</div>',
        unsafe_allow_html=True,
    )


def empty_state_rich(
    title: str,
    description: str = "",
    primary_action: tuple[str, str] | None = None,
    secondary_action: tuple[str, str] | None = None,
) -> None:
    """设计感空状态（替代裸 st.error + st.stop）。"""
    st.markdown(
        f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_8} {SP_5};text-align:center;'
        f'box-shadow:{SHADOW_CARD};font-family:{FONT_SANS};margin:{SP_5} 0">'
        f'<h3 style="margin:0 0 {SP_3};font-size:20px;font-weight:600;'
        f'color:{TEXT_STRONG};letter-spacing:-0.16px">{title}</h3>'
        + (f'<p style="margin:0 auto;font-size:14px;color:{TEXT_MUTED};'
           f'line-height:1.6;max-width:440px;white-space:pre-line">{description}</p>'
           if description else '')
        + '</div>',
        unsafe_allow_html=True,
    )
    if primary_action or secondary_action:
        _s1, c1, c2, _s2 = st.columns([2, 1.4, 1.4, 2])
        if primary_action:
            with c1:
                if st.button(primary_action[0], type="primary", use_container_width=True,
                             key=f"es_p_{primary_action[0]}_{title[:8]}"):
                    st.switch_page(primary_action[1])
        if secondary_action:
            with c2:
                if st.button(secondary_action[0], use_container_width=True,
                             key=f"es_s_{secondary_action[0]}_{title[:8]}"):
                    st.switch_page(secondary_action[1])


def task_list_card(
    card_title: str,
    items: list[dict],
    empty_text: str = "暂无待处理项",
    right_badge: str = "",
) -> None:
    """任务列表卡（保留，list 场景不同于 task_action_card）。"""
    badge_html = (
        f'<span style="font-size:11px;background:rgba(0,113,227,0.08);color:{ACCENT_BLUE};'
        f'padding:2px 8px;border-radius:{RADIUS_PILL};margin-left:{SP_2};font-weight:500">'
        f'{right_badge}</span>'
        if right_badge else ""
    )
    header = (
        f'<div style="font-size:14px;font-weight:600;color:{TEXT_STRONG};'
        f'margin-bottom:{SP_4};font-family:{FONT_SANS}">{card_title}{badge_html}</div>'
    )
    rows = ""
    if not items:
        rows = (f'<div style="font-size:13px;color:{TEXT_MUTED};text-align:center;'
                f'padding:{SP_5} 0;font-family:{FONT_SANS}">{empty_text}</div>')
    else:
        for i, item in enumerate(items):
            label = item.get("label", "")
            meta  = item.get("meta", "")
            score = item.get("score")
            sep = f'border-top:1px solid {BORDER_SOFTER};' if i > 0 else ""
            score_html = (
                f'<span style="font-size:15px;font-weight:600;color:{TEXT_STRONG};'
                f'font-family:{FONT_SANS};white-space:nowrap;font-variant-numeric:tabular-nums">'
                f'{score} 分</span>' if score is not None else ""
            )
            meta_html = (f'<div style="font-size:12px;color:{TEXT_MUTED};margin-top:2px">{meta}</div>'
                         if meta else "")
            rows += (
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:{SP_3} 0;{sep}font-family:{FONT_SANS}">'
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-size:13px;font-weight:500;color:{TEXT_STRONG};'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>'
                f'{meta_html}</div>'
                f'{score_html}</div>'
            )
    st.markdown(
        f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
        f'border-radius:{RADIUS_LG};padding:{SP_5};box-shadow:{SHADOW_CARD}">'
        f'{header}{rows}</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════
#  Appendix E.2 — Legacy 组件（delegate 到新组件，向后兼容）
# ═════════════════════════════════════════════════════════════

def page_header(
    title: str,
    subtitle: str = "",
    badge_html: str = "",      # 废弃，不再渲染
    right_text: str = "",
    right_page: str = "",
) -> None:
    """[Legacy] delegate 到 page_shell_header。badge_html 参数被忽略。"""
    # 兼容旧调用：strip 标题中的 emoji 前缀（如果有残留）
    clean_title = title.strip()
    page_shell_header(
        title=clean_title,
        subtitle=subtitle,
        right_label=right_text,
        right_page=right_page,
    )


def section_block(title: str, subtitle: str = "", icon: str = "") -> None:
    """[Legacy] icon 参数被忽略，delegate 到 apple_section_heading。"""
    apple_section_heading(title, subtitle=subtitle)


def section_title(text: str, icon: str = "") -> None:
    """[Legacy] alias，icon 被忽略。"""
    apple_section_heading(text)


def hero_section(
    eyebrow: str,
    title: str,
    subtitle: str,
    primary_label: str,
    primary_page: str,
    secondary_label: str,
    secondary_page: str,
) -> None:
    """[Legacy] delegate 到 hero_intro_block。"""
    hero_intro_block(
        eyebrow=eyebrow,
        title=title,
        subtitle=subtitle,
        primary=(primary_label, primary_page),
        secondary=(secondary_label, secondary_page),
    )


def summary_stat_card(label: str, value, tone: str = "default", hint: str = "") -> None:
    """[Legacy] tone 参数被忽略（左竖条系统已废弃），delegate 到 soft_stat_card。

    注意：签名与 soft_stat_card 参数顺序不同（老版 label 在前），这里保持兼容。
    """
    soft_stat_card(value=value, label=label, hint=hint)


def metric_card(label: str, value, delta: str = "", delta_good: bool = True) -> None:
    """[Legacy] delegate 到 soft_stat_card（delta 作 hint）。"""
    soft_stat_card(value=value, label=label, hint=delta)


def action_card(
    title: str,
    description: str,
    page: str,
    icon: str = "",           # 废弃
    emphasis: str = "secondary",  # 废弃
) -> None:
    """[Legacy] icon 和 emphasis 被忽略，delegate 到 feature_card。"""
    feature_card(title, description, page)
