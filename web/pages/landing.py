"""CareerOS 对外官网 Landing —— 1:1 还原 new UI 5 张图。

结构：
  顶部 nav
  ├ Section Hero    「像编辑文档一样 定制简历」
  ├ Section AI Chat 「和 AI 边聊边改简历」
  ├ Section Kanban  「从岗位到投递，全流程追踪」
  ├ Section BYO-Key 「你的 Key，你的数据，你掌控」
  └ Footer CTA

注意：本页面 **色系独立于主仓库 Apple 工作台**（marketing vs product）。
  - Landing：纯白 + 靛蓝 #3B5BFE（1:1 还原 5 张参考图）
  - 主应用：Apple 暖灰 #f5f5f7 + Apple Blue #0071e3（由 app.py 全局 CSS 控制）

关键红线：
  - 所有 CSS/HTML 注入必须用 st.html（不是 st.markdown，避免 Markdown 缩进坑）
  - 字体栈必须双引号
  - 不写 HTML 注释（会被 Markdown parser 截断）
"""

from __future__ import annotations

import html as _html

import streamlit as st


# =========================================================================
# 局部设计 Token（Landing 独享，不污染主仓库 Apple tokens）
# =========================================================================
C_BG = "#FFFFFF"
C_BG_SOFT = "#F7F8FA"
C_BG_MUTED = "#EEF1F5"
C_BORDER = "#E5E7EB"

C_INK = "#0B1220"
C_INK_SUB = "#4B5563"
C_INK_MUTE = "#9CA3AF"

C_PRIMARY = "#3B5BFE"
C_PRIMARY_SOFT = "#EEF1FF"
C_PRIMARY_INK = "#1E3AE8"

C_SUCCESS = "#10B981"
C_SUCCESS_SOFT = "#ECFDF5"
C_WARN = "#F59E0B"
C_DANGER = "#EF4444"

R_MD = 10
R_LG = 14
R_PILL = 999

S_MD = "0 4px 16px rgba(11,18,32,.08)"
S_LG = "0 12px 32px rgba(11,18,32,.10)"

FONT = ('"Inter","PingFang SC","Hiragino Sans GB",'
        '"HarmonyOS Sans SC","Microsoft YaHei",sans-serif')


def _h(s: str) -> None:
    """稳妥注入 HTML：优先 st.html，fallback st.markdown。"""
    try:
        st.html(s)  # type: ignore[attr-defined]
    except Exception:
        st.markdown(s, unsafe_allow_html=True)


def _chip(text: str, tone: str = "neutral", icon: str | None = None) -> str:
    """胶囊标签。tone: neutral / primary / success / warn / danger"""
    palette = {
        "neutral": (C_BG_MUTED, C_INK_SUB),
        "primary": (C_PRIMARY_SOFT, C_PRIMARY_INK),
        "success": (C_SUCCESS_SOFT, C_SUCCESS),
        "warn":    ("#FFFBEB", C_WARN),
        "danger":  ("#FEF2F2", C_DANGER),
    }
    bg, fg = palette.get(tone, palette["neutral"])
    icon_html = f'<span style="margin-right:4px;">{_html.escape(icon)}</span>' if icon else ""
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'padding:2px 10px;background:{bg};color:{fg};'
        f'border-radius:{R_PILL}px;font-size:12px;font-weight:500;'
        f'line-height:1.6;white-space:nowrap;'
        f'font-family:{FONT};">{icon_html}{_html.escape(text)}</span>'
    )


# =========================================================================
# 页面配置 & 全局 Landing CSS（override 主仓库 Apple tokens）
# =========================================================================
try:
    st.set_page_config(
        page_title="CareerOS — 你的 AI 求职副驾",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except Exception:
    pass


# ⚠️ 这段 CSS 只在 Landing 生效（其他页面不 import 这个文件，不会受影响）
# 因为 Streamlit 的 st.html 注入的 CSS 全局生效，我们通过「在 Landing 显示时压制 Apple 灰底」
# + 「退出 Landing 后 app.py 的全局 CSS 会重新 rerun 覆盖回去」实现视觉隔离
_LANDING_CSS = (
    "<style>"
    # 1) Reset Apple 灰底，Landing 全白
    "html,body,.stApp{background:#FFFFFF!important;}"
    f"html,body,[class*='css'],.stApp{{font-family:{FONT}!important;}}"
    # 2) 隐藏 Streamlit 默认 toolbar / header / sidebar（Landing 全通栏）
    "section[data-testid='stSidebar']{display:none!important;}"
    "[data-testid='collapsedControl']{display:none!important;}"
    "header[data-testid='stHeader']{display:none!important;}"
    # 3) 主容器通栏 + 无 padding
    ".main .block-container{max-width:100%!important;padding:0!important;}"
    # 4) 按钮统一：primary 靛蓝、radius 10、无 box-shadow 外框
    ".stButton>button{"
    f"border-radius:{R_MD}px!important;font-weight:500!important;"
    f"font-size:14px!important;padding:8px 16px!important;"
    f"border:1px solid {C_BORDER}!important;"
    f"background:{C_BG}!important;color:{C_INK}!important;"
    "transition:all .15s cubic-bezier(.2,.7,.3,1)!important;"
    "box-shadow:none!important;}"
    ".stButton>button:hover{"
    f"background:{C_BG_MUTED}!important;transform:translateY(-1px);}}"
    ".stButton>button:active{transform:scale(.98);}"
    '.stButton>button[kind="primary"]{'
    f"background:{C_PRIMARY}!important;color:#fff!important;"
    f"border-color:{C_PRIMARY}!important;"
    "box-shadow:0 4px 12px rgba(59,91,254,.35)!important;}"
    '.stButton>button[kind="primary"]:hover{'
    f"background:{C_PRIMARY_INK}!important;}}"
    "</style>"
)
_h(_LANDING_CSS)


# =========================================================================
# 入 app 路由 helper
# =========================================================================
def _enter_app() -> None:
    """点 CTA 后进入工作台 —— 置 entered_app=True，app.py 读到后自动 rerun 走 navigation。"""
    st.session_state["entered_app"] = True
    st.rerun()


# =========================================================================
# 顶部 Nav
# =========================================================================
def _render_topbar() -> None:
    c_logo, c_menu, c_login, c_cta = st.columns(
        [3, 5, 1.2, 1.6], vertical_alignment="center"
    )
    with c_logo:
        _h(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'font-weight:800;font-size:19px;color:{C_INK};padding:12px 0 12px 48px;">'
            f'<span style="display:inline-flex;width:30px;height:30px;border-radius:9px;'
            f'background:{C_PRIMARY};color:#fff;'
            f'align-items:center;justify-content:center;font-size:16px;'
            f'box-shadow:0 2px 8px rgba(59,91,254,.35);">C</span>CareerOS</div>'
        )
    with c_menu:
        _h(
            f'<div style="display:flex;gap:32px;font-size:14px;color:{C_INK_SUB};padding:16px 0 16px 40px;">'
            f'<a href="#feature-1" style="color:inherit;text-decoration:none;">产品功能 ▾</a>'
            f'<a href="#feature-2" style="color:inherit;text-decoration:none;">使用场景</a>'
            f'<a href="#feature-3" style="color:inherit;text-decoration:none;">定价</a>'
            f'<a href="#feature-3" style="color:inherit;text-decoration:none;">资源中心</a>'
            f'</div>'
        )
    with c_login:
        if st.button("登录", key="landing_nav_login", use_container_width=True):
            _enter_app()
    with c_cta:
        if st.button("免费体验", key="landing_nav_cta", type="primary",
                     use_container_width=True):
            _enter_app()


# =========================================================================
# Section 1 — Hero
# =========================================================================
def _hero_check(icon: str, title: str, desc: str) -> str:
    return (
        f'<div style="display:flex;align-items:flex-start;gap:12px;'
        f'border:1px solid {C_BORDER};border-radius:12px;padding:14px 16px;'
        f'background:{C_BG};box-shadow:0 1px 2px rgba(11,18,32,.04);">'
        f'<span style="display:inline-flex;width:28px;height:28px;border-radius:8px;'
        f'background:{C_PRIMARY_SOFT};color:{C_PRIMARY};align-items:center;'
        f'justify-content:center;font-size:15px;line-height:1;flex-shrink:0;">{_html.escape(icon)}</span>'
        f'<span style="display:flex;flex-direction:column;gap:3px;">'
        f'<span style="font-size:15px;color:{C_INK};font-weight:700;">{_html.escape(title)}</span>'
        f'<span style="font-size:13px;color:{C_INK_SUB};line-height:1.45;">{_html.escape(desc)}</span>'
        f'</span>'
        f'</div>'
    )


def _hero_editor_mock() -> str:
    action_btn = (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'padding:3px 8px;border:1px solid {C_BORDER};border-radius:7px;'
        f'background:#fff;color:{C_INK_SUB};font-size:11px;font-weight:600;white-space:nowrap;">'
    )

    def inline_actions(primary: bool = False) -> str:
        first = "AI 优化" if primary else "优化"
        rewrite = f'{action_btn}重写</span>' if primary else ""
        return (
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin-left:8px;">'
            f'{action_btn}{first}</span>'
            f'{rewrite}'
            f'{action_btn}⋯</span>'
            f'</span>'
        )

    def section_title(text: str) -> str:
        return (
            f'<div style="font-size:13px;font-weight:800;color:{C_INK};'
            f'padding-top:10px;margin-top:10px;border-top:1px solid {C_BORDER};">{text}</div>'
        )

    def exp_row(company: str, role: str, date: str) -> str:
        return (
            f'<div style="display:grid;grid-template-columns:1.35fr 1fr auto;gap:8px;'
            f'align-items:baseline;margin-top:8px;">'
            f'<span style="font-weight:700;color:{C_INK};font-size:12.5px;">{company}</span>'
            f'<span style="color:{C_INK_SUB};font-size:12px;">{role}</span>'
            f'<span style="color:{C_INK_MUTE};font-size:11.5px;white-space:nowrap;">{date}</span>'
            f'</div>'
        )

    def bullet(text: str, highlighted: bool = False) -> str:
        style = (
            f'background:{C_PRIMARY_SOFT};border-left:3px solid {C_PRIMARY};'
            f'padding:6px 10px;border-radius:6px;margin:5px 0;'
            if highlighted else 'margin:4px 0;'
        )
        return (
            f'<div style="{style}color:{C_INK_SUB};font-size:11.5px;line-height:1.55;">'
            f'· {_html.escape(text)}</div>'
        )

    def dots(active: int) -> str:
        return ''.join(
            f'<span style="width:6px;height:6px;border-radius:50%;'
            f'background:{C_PRIMARY if i < active else C_BG_MUTED};display:inline-block;"></span>'
            for i in range(5)
        )

    jd_rows = [
        ("用户增长", 5),
        ("内容运营", 5),
        ("社群运营", 4),
        ("X (Twitter)", 4),
        ("Telegram", 5),
        ("内容矩阵", 5),
        ("数据分析", 3),
        ("AI 工具", 5),
    ]
    jd_match = ''.join(
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;'
        f'font-size:11.5px;color:{C_INK_SUB};margin-top:7px;">'
        f'<span>{_html.escape(label)}</span>'
        f'<span style="display:inline-flex;gap:4px;align-items:center;">{dots(count)}</span>'
        f'</div>'
        for label, count in jd_rows
    )

    toolbar = (
        f'<div style="display:flex;align-items:center;gap:5px;padding:8px 10px;'
        f'border-bottom:1px solid {C_BORDER};background:#FBFBFC;border-radius:14px 14px 0 0;">'
        f'{action_btn}正文</span>'
        f'{action_btn}10.5 ▾</span>'
        f'<span style="display:inline-flex;gap:2px;align-items:center;">'
        f'<span style="font-size:12px;font-weight:800;color:{C_INK_SUB};padding:3px 5px;">B</span>'
        f'<span style="font-size:12px;font-style:italic;color:{C_INK_SUB};padding:3px 5px;">I</span>'
        f'<span style="font-size:12px;text-decoration:underline;color:{C_INK_SUB};padding:3px 5px;">U</span>'
        f'</span>'
        f'{action_btn}≡</span>'
        f'{action_btn}↗</span>'
        f'<span style="flex:1;"></span>'
        f'{action_btn}保存</span>'
        f'{action_btn}导出 ▾</span>'
        f'</div>'
    )

    resume_panel = (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_LG};overflow:hidden;min-width:0;">'
        f'{toolbar}'
        f'<div style="padding:20px 22px;font-size:12px;line-height:1.55;">'
        f'<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:12px;">'
        f'<div style="min-width:0;">'
        f'<div style="font-size:22px;font-weight:800;color:{C_INK};letter-spacing:.16em;">杨　超</div>'
        f'<div style="color:{C_INK_MUTE};font-size:11.5px;margin-top:4px;">'
        f'186-8795-0926  |  bc1chao0926@gmail.com</div>'
        f'<div style="color:{C_INK_SUB};font-size:11.5px;margin-top:5px;">'
        f'求职意向：AI 增长运营  |  期望城市：杭州  |  到岗时间：下周到岗</div>'
        f'</div>'
        f'<div style="width:46px;height:46px;border-radius:50%;background:{C_PRIMARY};'
        f'color:#fff;display:flex;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:800;box-shadow:0 4px 12px rgba(59,91,254,.28);">YC</div>'
        f'</div>'
        f'{section_title("个人总结")}'
        f'<div style="display:flex;align-items:flex-start;gap:8px;margin-top:7px;">'
        f'<div style="color:{C_INK_SUB};font-size:11.5px;line-height:1.6;">'
        f'统计科班出身，擅长把数据变成增长动作。曾从 0 搭建 AI Trading 社区，实现 9,000+ 粉丝与 1,300+ Telegram 订阅，完成 20+ 次商业合作；3 段运营实习覆盖增长、内容与数据分析。'
        f'</div>{inline_actions(True)}</div>'
        f'{section_title("项目经历")}'
        f'{exp_row("AI Trading 社区搭建", "用户增长运营", "2024.03 - 至今")}'
        f'{bullet("从 0 搭建 X 与 Telegram 内容矩阵，在零投放预算下增长至 9,000+ 粉丝与 1,300+ 订阅。")}'
        f'{bullet("设计热点监测、信号筛选、结构化分析，分发输出流程，稳定支撑每日 15+ 条内容产出。")}'
        f'{bullet("围绕用户关注点做内容测试与社群运营，沉淀可复用的 AI 内容生产 SOP。")}'
        f'<div style="display:flex;justify-content:flex-end;">{inline_actions(False)}</div>'
        f'{exp_row("CareerOS 求职系统", "产品与自动化实践", "2025.10 - 至今")}'
        f'{bullet("搭建岗位池、JD 解析、简历定制，按面试准备工作流，覆盖求职全链路。")}'
        f'{bullet("用 SQLite 管理岗位与投递数据，结合大模型完成 JD 匹配、简历改写与评估。")}'
        f'<div style="display:flex;justify-content:flex-end;">{inline_actions(False)}</div>'
        f'{section_title("实习经历")}'
        f'{exp_row("Fancy Tech", "海外产品运营实习生", "2024.06 - 2024.09")}'
        f'{bullet("负责 AI 内容生产与分发，搭建 TikTok + Instagram 内容矩阵，应用 AI 工具批量生成选题与文案，优化发布策略，带动账号粉丝增长 200+，单条爆款内容播放量提升 5 倍。", True)}'
        f'{bullet("拆解 PhotoRoom、Pebblely 等竞品链路，提炼高转化场景并输出产品优化建议。")}'
        f'{bullet("在 Reddit、TikTok 垂直社群做英文私信触达与内容冷启动，验证产品 PMF 假设。")}'
        f'<div style="display:flex;justify-content:flex-end;">{inline_actions(False)}</div>'
        f'{exp_row("杭银消费金融股份有限公司", "数据运营实习生", "2023.06 - 2023.10")}'
        f'{bullet("参与用户分层、活动复盘与指标看板维护，支持运营策略迭代。")}'
        f'{bullet("整理业务数据与活动结果，输出周报和专项分析材料。")}'
        f'<div style="display:flex;justify-content:flex-end;">{inline_actions(False)}</div>'
        f'</div></div>'
    )

    jd_panel = (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_MD};padding:18px 18px;min-width:0;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'font-size:14px;font-weight:800;color:{C_INK};margin-bottom:10px;">'
        f'<span>目标 JD</span><span style="font-size:16px;">📋</span></div>'
        f'<div style="height:1px;background:{C_BORDER};margin-bottom:14px;"></div>'
        f'<div style="font-size:15px;font-weight:800;color:{C_INK};">用户增长运营</div>'
        f'<div style="font-size:12px;color:{C_INK_MUTE};margin-top:4px;">X · AI 行业</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">'
        f'<span style="display:inline-flex;align-items:center;padding:2px 9px;'
        f'border:1px solid {C_BORDER};border-radius:999px;background:#fff;'
        f'color:{C_INK_SUB};font-size:11px;font-weight:500;line-height:1.6;">杭州</span>'
        f'<span style="display:inline-flex;align-items:center;padding:2px 9px;'
        f'border:1px solid {C_BORDER};border-radius:999px;background:#fff;'
        f'color:{C_INK_SUB};font-size:11px;font-weight:500;line-height:1.6;">1-3 年</span>'
        f'<span style="display:inline-flex;align-items:center;padding:2px 9px;'
        f'border:1px solid {C_BORDER};border-radius:999px;background:#fff;'
        f'color:{C_INK_SUB};font-size:11px;font-weight:500;line-height:1.6;">本科</span>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:800;color:{C_INK};margin-top:18px;">岗位要求</div>'
        f'<div style="font-size:11.5px;color:{C_INK_SUB};line-height:1.65;margin-top:7px;">'
        f'<div>• 负责社交平台（X / Telegram）用户增长</div>'
        f'<div>• 搭建内容矩阵，制定内容策略并落地执行</div>'
        f'<div>• 数据驱动，监测指标，优化增长策略</div>'
        f'<div>• 熟悉 AI 工具，有内容自动化经验优先</div>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:800;color:{C_INK};margin-top:18px;">关键词匹配</div>'
        f'{jd_match}'
        f'<div style="display:flex;justify-content:flex-end;margin-top:18px;">'
        f'{action_btn}重新分析 JD</span>'
        f'</div></div>'
    )

    return (
        f'<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;align-items:stretch;">'
        f'{resume_panel}{jd_panel}</div>'
    )


def _section_hero() -> None:
    _h(
        f'<div id="hero" style="padding:56px 56px 40px 56px;'
        f'background:linear-gradient(180deg,#FFFFFF 0%, {C_BG_SOFT} 100%);">'
        f'<div style="max-width:1280px;margin:0 auto;display:grid;'
        f'grid-template-columns:5fr 6fr;gap:56px;align-items:center;">'
        f'<div>'
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};'
        f'padding:5px 12px;border-radius:999px;'
        f'font-size:12px;font-weight:600;margin-bottom:20px;">✦ 简历定制</div>'
        f'<h1 style="font-size:56px;font-weight:800;line-height:1.15;'
        f'color:{C_INK};letter-spacing:-0.02em;margin:0 0 20px 0;">'
        f'像编辑文档一样<br/><span style="color:{C_PRIMARY};">定制简历</span></h1>'
        f'<p style="font-size:17px;color:{C_INK_SUB};line-height:1.6;'
        f'margin:0 0 28px 0;max-width:460px;">'
        f'基于目标岗位 JD，智能建议优化内容，让简历更贴合'
        f'岗位要求，显著提升面试机会。</p>'
        f'<div style="display:flex;flex-direction:column;gap:12px;">'
        f'{_hero_check("📄", "所见即所得的在线编辑", "直接修改、增删、重写每一条经历与描述")}'
        f'{_hero_check("⚡", "JD 驱动的智能优化建议", "对齐岗位关键词与能力要求，自动匹配度")}'
        f'{_hero_check("🛡", "一键导出精美简历", "支持 PDF / Word 格式、排版精美、随时投递")}'
        f'</div></div>'
        f'<div>{_hero_editor_mock()}</div>'
        f'</div></div>'
    )


# =========================================================================
# Section 2 — AI Chat
# =========================================================================
def _chat_card_mock() -> str:
    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_MD};padding:22px;min-width:0;">'
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};'
        f'padding:5px 12px;border-radius:999px;font-size:12px;'
        f'font-weight:700;margin-bottom:18px;">✦ AI 助手</div>'
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:14px;">'
        f'<div style="width:30px;height:30px;border-radius:50%;background:{C_BG_MUTED};'
        f'flex-shrink:0;"></div>'
        f'<div style="display:flex;align-items:flex-start;gap:8px;min-width:0;">'
        f'<div style="background:{C_BG_SOFT};border:1px solid {C_BORDER};'
        f'border-radius:12px 12px 12px 3px;padding:12px 14px;'
        f'font-size:13px;color:{C_INK};line-height:1.55;max-width:260px;">'
        f'帮我优化这条经历，突出<br/>AI 内容生产和增长成果</div>'
        f'<div style="font-size:12px;color:{C_INK_MUTE};padding-top:4px;">10:24</div>'
        f'</div></div>'
        f'<div style="display:flex;align-items:flex-start;gap:10px;flex-direction:row-reverse;'
        f'margin-bottom:16px;">'
        f'<div style="width:30px;height:30px;border-radius:50%;background:{C_PRIMARY};'
        f'color:#fff;display:flex;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:800;flex-shrink:0;">AI</div>'
        f'<div style="display:flex;align-items:flex-start;gap:8px;min-width:0;">'
        f'<div style="font-size:12px;color:{C_INK_MUTE};padding-top:4px;">10:25</div>'
        f'<div style="background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};'
        f'border-radius:12px 12px 3px 12px;padding:12px 14px;'
        f'font-size:13px;line-height:1.6;max-width:330px;">'
        f'好的，已基于岗位「AI 增长运营」的要求，优化为突出 AI 应用、增长结果和可量化成果的表达：'
        f'</div></div></div>'
        f'<div style="border:1px solid {C_BORDER};border-radius:12px;'
        f'background:#fff;overflow:hidden;margin-bottom:16px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:10px 12px;border-bottom:1px solid {C_BORDER};">'
        f'<span style="font-size:13px;font-weight:800;color:{C_INK};">修改预览（待应用）</span>'
        f'<span style="display:inline-flex;gap:6px;">'
        f'<span style="background:#FEF2F2;color:{C_DANGER};border-radius:999px;'
        f'padding:2px 8px;font-size:11px;font-weight:700;">删除</span>'
        f'<span style="background:#ECFDF5;color:{C_SUCCESS};border-radius:999px;'
        f'padding:2px 8px;font-size:11px;font-weight:700;">新增</span>'
        f'</span></div>'
        f'<div style="background:#FEF2F2;border-left:3px solid {C_DANGER};'
        f'padding:10px 12px;color:{C_DANGER};font-size:12.5px;line-height:1.6;">'
        f'− 负责内容运营，搭建内容矩阵，发布笔记和视频，提升粉丝增长</div>'
        f'<div style="background:#ECFDF5;border-left:3px solid {C_SUCCESS};'
        f'padding:10px 12px;color:{C_SUCCESS};font-size:12.5px;line-height:1.6;">'
        f'+ 负责 AI 内容生产与分发，搭建 TikTok + Instagram 内容矩阵，应用 AI 工具批量生成成篇文案，单条爆款内容播放量提升 5 倍。</div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:16px;">'
        f'<span style="background:{C_PRIMARY};color:#fff;border-radius:9px;'
        f'padding:8px 18px;font-size:13px;font-weight:700;box-shadow:0 8px 18px rgba(59,91,254,.22);">应用修改</span>'
        f'<span style="background:#fff;color:{C_INK_SUB};border:1px solid {C_BORDER};'
        f'border-radius:9px;padding:8px 18px;font-size:13px;font-weight:700;">撤销修改</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;'
        f'border:1px solid {C_BORDER};border-radius:12px;background:#fff;'
        f'padding:12px 14px;color:{C_INK_MUTE};font-size:13px;">'
        f'<span>告诉 AI 你想怎么改，或问它建议</span>'
        f'<span style="color:{C_PRIMARY};font-size:16px;">📤</span>'
        f'</div></div>'
    )


def _ai_chat_feature_chip(icon: str, title: str, desc: str) -> str:
    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'padding:14px 12px;min-height:118px;box-shadow:0 1px 2px rgba(11,18,32,.04);">'
        f'<div style="font-size:19px;line-height:1;margin-bottom:10px;">{_html.escape(icon)}</div>'
        f'<div style="font-size:13px;font-weight:800;color:{C_INK};margin-bottom:6px;">{_html.escape(title)}</div>'
        f'<div style="font-size:11.5px;color:{C_INK_SUB};line-height:1.45;">{desc}</div>'
        f'</div>'
    )


def _ai_chat_resume_preview_mock() -> str:
    def section_title(text: str) -> str:
        return (
            f'<div style="font-size:13px;font-weight:800;color:{C_INK};'
            f'padding-top:10px;margin-top:10px;border-top:1px solid {C_BORDER};">{text}</div>'
        )

    def exp_row(company: str, role: str, date: str) -> str:
        return (
            f'<div style="display:grid;grid-template-columns:1.25fr .92fr auto;gap:8px;'
            f'align-items:baseline;margin-top:8px;">'
            f'<span style="font-weight:700;color:{C_INK};font-size:12px;">{company}</span>'
            f'<span style="color:{C_INK_SUB};font-size:11.5px;">{role}</span>'
            f'<span style="color:{C_INK_MUTE};font-size:11px;white-space:nowrap;">{date}</span>'
            f'</div>'
        )

    def bullet(text: str, highlighted: bool = False) -> str:
        style = (
            f'background:{C_PRIMARY_SOFT};border-left:3px solid {C_PRIMARY};'
            f'padding:6px 10px;border-radius:6px;margin:5px 0;'
            if highlighted else 'margin:4px 0;'
        )
        return (
            f'<div style="{style}color:{C_INK_SUB};font-size:11px;line-height:1.55;">'
            f'· {_html.escape(text)}</div>'
        )

    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_MD};overflow:hidden;min-width:0;">'
        f'<div style="padding:20px 22px;font-size:12px;line-height:1.55;">'
        f'<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:12px;">'
        f'<div style="min-width:0;">'
        f'<div style="font-size:22px;font-weight:800;color:{C_INK};letter-spacing:.16em;">杨　超</div>'
        f'<div style="color:{C_INK_MUTE};font-size:11.5px;margin-top:4px;">'
        f'186-8795-0926  |  bc1chao0926@gmail.com</div>'
        f'<div style="color:{C_INK_SUB};font-size:11.5px;margin-top:5px;">'
        f'求职意向：AI 增长运营  |  期望城市：杭州  |  到岗时间：下周到岗</div>'
        f'</div>'
        f'<div style="width:46px;height:46px;border-radius:50%;background:{C_PRIMARY};'
        f'color:#fff;display:flex;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:800;box-shadow:0 4px 12px rgba(59,91,254,.28);">YC</div>'
        f'</div>'
        f'{section_title("个人总结")}'
        f'<div style="color:{C_INK_SUB};font-size:11.5px;line-height:1.6;margin-top:7px;">'
        f'统计科班出身，擅长把数据变成增长动作。曾从 0 搭建 AI Trading 社区，实现 9,000+ 粉丝与 1,300+ Telegram 订阅，完成 20+ 次商业合作；3 段运营实习覆盖增长、内容与数据分析。'
        f'</div>'
        f'{section_title("项目经历")}'
        f'{exp_row("AI Trading 社区搭建", "用户增长运营", "2024.03 - 至今")}'
        f'{bullet("从 0 搭建 X 与 Telegram 内容矩阵，在零投放预算下增长至 9,000+ 粉丝与 1,300+ 订阅。")}'
        f'{bullet("设计热点监测、信号筛选、结构化分析，分发输出流程，稳定支撑每日 15+ 条内容产出。")}'
        f'{bullet("围绕用户关注点做内容测试与社群运营，沉淀可复用的 AI 内容生产 SOP。")}'
        f'{exp_row("CareerOS 求职系统", "产品与自动化实践", "2025.10 - 至今")}'
        f'{bullet("搭建岗位池、JD 解析、简历定制，按面试准备工作流，覆盖求职全链路。")}'
        f'{bullet("用 SQLite 管理岗位与投递数据，结合大模型完成 JD 匹配、简历改写与评估。")}'
        f'{section_title("实习经历")}'
        f'{exp_row("Fancy Tech", "海外产品运营实习生", "2024.06 - 2024.09")}'
        f'{bullet("负责 AI 内容生产与分发，搭建 TikTok + Instagram 内容矩阵，应用 AI 工具批量生成选题与文案，优化发布策略，带动账号粉丝增长 200+，单条爆款内容播放量提升 5 倍。", True)}'
        f'{bullet("拆解 PhotoRoom、Pebblely 等竞品链路，提炼高转化场景并输出产品优化建议。")}'
        f'{bullet("在 Reddit、TikTok 垂直社群做英文私信触达与内容冷启动，验证产品 PMF 假设。")}'
        f'{exp_row("杭银消费金融股份有限公司", "数据运营实习生", "2023.06 - 2023.10")}'
        f'{bullet("参与用户分层、活动复盘与指标看板维护，支持运营策略迭代。")}'
        f'{bullet("整理业务数据与活动结果，输出周报和专项分析材料。")}'
        f'</div></div>'
    )


def _section_ai_chat() -> None:
    _h(
        f'<div id="feature-1" style="padding:96px 56px;background:#fff;">'
        f'<div style="max-width:1280px;margin:0 auto;display:grid;'
        f'grid-template-columns:5fr 7fr;gap:56px;align-items:center;">'
        f'<div>'
        f'<h2 style="font-size:44px;font-weight:800;color:{C_INK};line-height:1.2;'
        f'margin:0 0 18px 0;letter-spacing:-0.02em;">'
        f'和 <span style="color:{C_PRIMARY};">AI</span> 边聊边改简历</h2>'
        f'<p style="font-size:16px;color:{C_INK_SUB};line-height:1.65;max-width:440px;margin:0;">'
        f'自然对话，精准优化，打造更有竞争力的简历</p>'
        f'<div style="margin-top:28px;">{_chat_card_mock()}</div>'
        f'</div>'
        f'<div style="min-width:0;">'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">'
        f'{_ai_chat_feature_chip("🧠", "智能分析", "AI 深度<br/>理解岗位<br/>需求")}'
        f'{_ai_chat_feature_chip("✓", "精准优化", "内容更贴合<br/>表达更专业")}'
        f'{_ai_chat_feature_chip("◐", "实时预览", "修改即预览<br/>效果看得见")}'
        f'{_ai_chat_feature_chip("✓", "一键应用", "安全可控<br/>随时撤销")}'
        f'</div>'
        f'{_ai_chat_resume_preview_mock()}'
        f'</div></div></div>'
    )


# =========================================================================
# Section 3 — Kanban
# =========================================================================
def _kanban_sidebar_mock() -> str:
    menu_items = [
        ("🏠", "首页", False, None),
        ("📋", "职位管理", True, None),
        ("📄", "JD 管理", False, None),
        ("👤", "投递追踪", False, None),
        ("🎤", "面试管理", False, None),
        ("📑", "Offer 管理", False, None),
        ("📝", "简历与模板", False, None),
        ("📊", "数据分析", False, None),
    ]
    rows = ""
    for icon, label, active, badge in menu_items:
        rows += (
            f'<div style="display:flex;align-items:center;gap:9px;padding:8px 10px;'
            f'border-radius:10px;background:{C_PRIMARY_SOFT if active else "transparent"};'
            f'color:{C_PRIMARY_INK if active else C_INK_SUB};font-size:12.5px;'
            f'font-weight:{700 if active else 500};margin-bottom:2px;">'
            f'<span style="width:18px;text-align:center;">{icon}</span>'
            f'<span>{_html.escape(label)}</span>'
            f'{badge or ""}'
            f'</div>'
        )
    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:16px;'
        f'box-shadow:{S_MD};padding:16px 14px;min-height:620px;display:flex;'
        f'flex-direction:column;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:9px;margin-bottom:18px;padding:0 4px;">'
        f'<span style="display:inline-flex;width:28px;height:28px;border-radius:8px;'
        f'background:{C_PRIMARY};color:#fff;align-items:center;justify-content:center;'
        f'font-size:13px;font-weight:800;">C</span>'
        f'<span style="font-size:15px;font-weight:800;color:{C_INK};">CareerOS</span>'
        f'</div>'
        f'{rows}'
        f'<div style="height:1px;background:{C_BORDER};margin:12px 4px;"></div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;'
        f'padding:8px 10px;border-radius:10px;color:{C_INK_SUB};font-size:12.5px;">'
        f'<span style="display:flex;align-items:center;gap:9px;"><span style="width:18px;text-align:center;">💡</span>AI 助手</span>'
        f'<span style="background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};'
        f'border-radius:999px;padding:1px 7px;font-size:10.5px;font-weight:700;">Beta</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:9px;padding:8px 10px;'
        f'border-radius:10px;color:{C_INK_SUB};font-size:12.5px;">'
        f'<span style="width:18px;text-align:center;">⚙</span><span>设置</span></div>'
        f'<div style="height:1px;background:{C_BORDER};margin:12px 4px;"></div>'
        f'<div style="margin-top:auto;display:flex;align-items:center;gap:9px;'
        f'padding:10px;border-radius:12px;background:{C_BG_SOFT};">'
        f'<span style="display:inline-flex;width:30px;height:30px;border-radius:50%;'
        f'background:{C_PRIMARY};color:#fff;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:800;">Y</span>'
        f'<span style="min-width:0;display:flex;flex-direction:column;">'
        f'<span style="font-size:12.5px;font-weight:700;color:{C_INK};">杨超</span>'
        f'<span style="font-size:11px;color:{C_INK_MUTE};">个人版 ▾</span>'
        f'</span></div></div>'
    )


def _kanban_mock() -> str:
    def card(
        color: str,
        logo: str,
        company: str,
        role: str,
        location: str,
        tags: list[str],
        meta: str,
        match: str,
    ) -> str:
        tag_html = ''.join(
            f'<span style="background:{C_BG_MUTED};color:{C_INK_SUB};border-radius:999px;'
            f'padding:2px 7px;font-size:10.5px;font-weight:600;">{_html.escape(tag)}</span>'
            for tag in tags
        )
        return (
            f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:12px;'
            f'padding:11px 12px;margin-bottom:10px;box-shadow:0 1px 2px rgba(11,18,32,.06);">'
            f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:8px;">'
            f'<div style="display:flex;align-items:center;gap:8px;min-width:0;">'
            f'<span style="display:inline-flex;width:28px;height:28px;border-radius:8px;'
            f'background:{color};color:#fff;align-items:center;justify-content:center;'
            f'font-size:12px;font-weight:800;flex-shrink:0;">{_html.escape(logo)}</span>'
            f'<span style="font-size:12.5px;font-weight:800;color:{C_INK};white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{_html.escape(company)}</span>'
            f'</div>'
            f'<span style="font-size:11px;color:{C_PRIMARY_INK};font-weight:800;white-space:nowrap;">{_html.escape(match)}</span>'
            f'</div>'
            f'<div style="font-size:12.5px;color:{C_INK};font-weight:700;line-height:1.35;margin-bottom:3px;">'
            f'{_html.escape(role)}</div>'
            f'<div style="font-size:11px;color:{C_INK_MUTE};margin-bottom:8px;">{_html.escape(location)}</div>'
            f'<div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px;">{tag_html}</div>'
            f'<div style="font-size:11px;color:{C_INK_MUTE};line-height:1.4;">{_html.escape(meta)}</div>'
            f'</div>'
        )

    cols_data = [
        (
            "待投递", 8, C_INK_MUTE, "更多 待投递 (5)", False,
            [
                ("#FF6900", "米", "小米科技", "AI 产品经理", "北京市·海淀区", ["产品", "AI"], "", "92%"),
                ("#E94B35", "字", "字节跳动", "内容策略产品经理", "北京市·海淀区", ["内容", "策略"], "", "88%"),
                ("#FFC600", "美", "美团", "增长产品经理", "上海市·长宁区", ["增长", "用户运营"], "", "85%"),
            ],
        ),
        (
            "已投递", 12, C_PRIMARY, "更多 已投递 (9)", False,
            [
                ("#00A4FF", "腾", "腾讯云", "AI 产品经理", "深圳市·南山区", ["云计算", "AI"], "投递于 2 天前", "90%"),
                ("#FF6A00", "阿", "阿里巴巴", "产品经理", "杭州市·余杭区", ["电商", "平台"], "投递于 5 天前", "87%"),
                ("#D91E18", "网", "网易", "数据产品经理", "杭州市·滨江区", ["数据", "BI"], "投递于 1 周前", "82%"),
            ],
        ),
        (
            "面试中", 5, C_PRIMARY_INK, "更多 面试中 (2)", False,
            [
                ("#2319DC", "百", "百度", "AI 产品经理（NLP 方向）", "北京市·海淀区", ["NLP", "AI"], "面·进行中", "93%"),
                ("#FE3366", "快", "快手", "策略产品经理", "北京市·海淀区", ["策略", "社区"], "面·预约中", "88%"),
                ("#2577E3", "携", "携程", "产品经理", "上海市·浦东新区", ["旅游", "平台"], "面·进行中", "86%"),
            ],
        ),
        (
            "Offer", 2, C_SUCCESS, "+ 添加到 Offer", True,
            [
                ("#E2231A", "京", "京东", "高级产品经理", "北京市·大兴区", ["电商"], "✅ Offer 已接受", "91%"),
                ("#FF6D0C", "滴", "滴滴", "产品经理", "北京市·海淀区", ["出行"], "✅ Offer 已接受", "89%"),
            ],
        ),
    ]
    col_blocks = []
    for title, count, color, more_text, dashed, cards in cols_data:
        cards_html = ''.join(card(*item) for item in cards)
        footer = (
            f'<div style="border:1px dashed {C_BORDER};border-radius:10px;padding:9px 10px;'
            f'text-align:center;color:{C_INK_SUB};font-size:11.5px;font-weight:700;background:#fff;">'
            f'{_html.escape(more_text)}</div>'
            if dashed else
            f'<div style="text-align:center;color:{C_PRIMARY_INK};font-size:11.5px;'
            f'font-weight:700;padding:7px 4px;">{_html.escape(more_text)}</div>'
        )
        col_blocks.append(
            f'<div style="min-width:0;background:{C_BG_SOFT};border-radius:14px;padding:12px 10px;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">'
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{color};"></span>'
            f'<span style="font-size:12.5px;font-weight:800;color:{C_INK};">{_html.escape(title)}</span>'
            f'</div>'
            f'<span style="font-size:11px;color:{C_INK_MUTE};background:#fff;'
            f'padding:1px 7px;border-radius:999px;">{count}</span>'
            f'</div>'
            f'{cards_html}'
            f'{footer}'
            f'</div>'
        )
    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_MD};padding:18px;min-width:0;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-bottom:18px;padding-bottom:12px;border-bottom:1px solid {C_BORDER};">'
        f'<div style="font-weight:800;color:{C_INK};font-size:15px;">我的投递看板 ▾</div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="display:inline-flex;align-items:center;gap:6px;background:{C_BG_SOFT};'
        f'border:1px solid {C_BORDER};border-radius:10px;padding:7px 12px;'
        f'color:{C_INK_MUTE};font-size:12px;min-width:190px;">🔍 搜索岗位 / 公司 / JD 关键词</span>'
        f'<span style="background:{C_PRIMARY};color:#fff;padding:7px 12px;'
        f'border-radius:9px;font-size:12px;font-weight:700;white-space:nowrap;">+ 添加职位</span>'
        f'<span style="display:inline-flex;width:30px;height:30px;border:1px solid {C_BORDER};'
        f'border-radius:9px;align-items:center;justify-content:center;color:{C_INK_SUB};">≡</span>'
        f'</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">'
        f'{"".join(col_blocks)}'
        f'</div></div>'
    )


def _ai_pm_drawer_mock() -> str:
    def info_row(label: str, value: str) -> str:
        return (
            f'<div style="display:grid;grid-template-columns:72px 1fr;gap:8px;'
            f'font-size:11.5px;line-height:1.55;margin-bottom:7px;">'
            f'<span style="color:{C_INK_MUTE};font-weight:700;">{_html.escape(label)}</span>'
            f'<span style="color:{C_INK_SUB};">{_html.escape(value)}</span>'
            f'</div>'
        )

    def bullet(text: str) -> str:
        return (
            f'<div style="display:flex;gap:7px;align-items:flex-start;font-size:11.5px;'
            f'line-height:1.55;color:{C_INK_SUB};margin-bottom:6px;">'
            f'<span style="color:{C_PRIMARY};font-weight:900;">•</span>'
            f'<span>{_html.escape(text)}</span></div>'
        )

    def match_row(text: str, status: str, partial: bool = False) -> str:
        chip_bg = "#FFFBEB" if partial else C_SUCCESS_SOFT
        chip_fg = C_WARN if partial else C_SUCCESS
        return (
            f'<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;'
            f'font-size:11.5px;color:{C_INK_SUB};margin-top:7px;">'
            f'<span>✓ {_html.escape(text)}</span>'
            f'<span style="background:{chip_bg};color:{chip_fg};border-radius:999px;'
            f'padding:2px 8px;font-size:10.5px;font-weight:800;white-space:nowrap;">{_html.escape(status)}</span>'
            f'</div>'
        )

    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:14px;'
        f'box-shadow:{S_MD};padding:18px 18px;min-width:0;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;min-width:0;">'
        f'<span style="display:inline-flex;width:34px;height:34px;border-radius:10px;'
        f'background:#2319DC;color:#fff;align-items:center;justify-content:center;'
        f'font-size:14px;font-weight:900;flex-shrink:0;">B</span>'
        f'<span style="min-width:0;display:flex;flex-direction:column;gap:2px;">'
        f'<span style="font-size:17px;font-weight:900;color:{C_INK};">AI 产品经理</span>'
        f'<span style="font-size:11.5px;color:{C_INK_MUTE};">北京市·海淀区</span>'
        f'</span></div>'
        f'<span style="color:{C_INK_MUTE};font-size:18px;line-height:1;">×</span>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;'
        f'border-bottom:1px solid {C_BORDER};margin-bottom:14px;">'
        f'<span style="text-align:center;padding:8px 0;color:{C_PRIMARY_INK};'
        f'border-bottom:2px solid {C_PRIMARY};font-size:11.5px;font-weight:800;">JD 详情</span>'
        f'<span style="text-align:center;padding:8px 0;color:{C_INK_MUTE};font-size:11.5px;font-weight:700;">匹配分析</span>'
        f'<span style="text-align:center;padding:8px 0;color:{C_INK_MUTE};font-size:11.5px;font-weight:700;">投递记录</span>'
        f'<span style="text-align:center;padding:8px 0;color:{C_INK_MUTE};font-size:11.5px;font-weight:700;">面试流程</span>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:900;color:{C_INK};margin-bottom:10px;">JD 核心信息</div>'
        f'{info_row("职位亮点", "负责百度 AI 搜索产品设计与迭代，探索大模型应用落地")}'
        f'{info_row("团队方向", "搜索体验 · 大模型应用 · 智能体产品")}'
        f'{info_row("汇报对象", "产品总监")}'
        f'{info_row("工作地点", "北京市 · 海淀区")}'
        f'{info_row("发布时间", "2025-05-20")}'
        f'<div style="font-size:13px;font-weight:900;color:{C_INK};margin:14px 0 8px;">岗位职责</div>'
        f'{bullet("负责 AI 搜索产品的需求分析、产品设计与项目推进")}'
        f'{bullet("结合大模型能力，探索创新的搜索体验与交互方式")}'
        f'{bullet("与研发、算法团队协作，推动产品落地与能力提升")}'
        f'{bullet("通过数据分析持续优化产品体验与核心指标")}'
        f'<div style="font-size:13px;font-weight:900;color:{C_INK};margin:14px 0 8px;">任职要求</div>'
        f'{bullet("3 年以上产品经验，有 AI / 搜索 / NLP 相关经验优先")}'
        f'{bullet("熟悉大模型应用场景，有 Prompt / Agent 项目经验优先")}'
        f'{bullet("优秀的用户洞察与产品设计能力，数据驱动")}'
        f'{bullet("本科以上学历，计算机、产品相关专业优先")}'
        f'<div style="border:1px solid {C_BORDER};border-radius:13px;background:{C_BG_SOFT};'
        f'padding:13px 13px;margin-top:14px;">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'<span style="display:inline-flex;width:64px;height:64px;border-radius:50%;'
        f'background:conic-gradient({C_PRIMARY} 0 93%, {C_BG_MUTED} 93% 100%);'
        f'align-items:center;justify-content:center;position:relative;flex-shrink:0;">'
        f'<span style="display:inline-flex;width:50px;height:50px;border-radius:50%;background:#fff;'
        f'align-items:center;justify-content:center;color:{C_PRIMARY_INK};font-size:16px;font-weight:900;">93%</span>'
        f'</span>'
        f'<span style="display:flex;flex-direction:column;gap:3px;">'
        f'<span style="font-size:13px;font-weight:900;color:{C_INK};">高度匹配</span>'
        f'<span style="font-size:11.5px;color:{C_INK_SUB};line-height:1.45;">你的简历与该岗位要求高度契合</span>'
        f'</span></div>'
        f'{match_row("3 年以上产品经验", "匹配")}'
        f'{match_row("AI / 大模型相关经验", "匹配")}'
        f'{match_row("产品设计与项目推进", "匹配")}'
        f'{match_row("数据分析能力", "匹配")}'
        f'{match_row("搜索产品经验", "部分匹配", True)}'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;">'
        f'<span style="text-align:center;border:1px solid {C_BORDER};border-radius:10px;'
        f'padding:9px 10px;font-size:12.5px;font-weight:800;color:{C_INK_SUB};background:#fff;">编辑 JD</span>'
        f'<span style="text-align:center;border-radius:10px;padding:9px 10px;'
        f'font-size:12.5px;font-weight:800;color:#fff;background:{C_PRIMARY};">去投递</span>'
        f'</div></div>'
    )


def _section_kanban() -> None:
    _h(
        f'<div id="feature-2" style="padding:96px 56px;background:{C_BG_SOFT};">'
        f'<div style="max-width:1280px;margin:0 auto;text-align:center;">'
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};'
        f'padding:5px 12px;border-radius:999px;font-size:12px;'
        f'font-weight:700;margin-bottom:18px;">🔵 AI 求职操作系统</div>'
        f'<h2 style="font-size:44px;font-weight:800;color:{C_INK};line-height:1.2;'
        f'margin:0 0 14px 0;letter-spacing:-0.02em;">'
        f'从岗位到投递，<span style="color:{C_PRIMARY};">全</span>流程追踪</h2>'
        f'<p style="font-size:16px;color:{C_INK_SUB};margin:0 auto 48px auto;'
        f'max-width:620px;line-height:1.6;">'
        f'JD 管理 · 智能匹配 · 投递追踪 · 面试管理 · Offer 记录，一站式求职闭环'
        f'</p></div>'
        f'<div style="max-width:1280px;margin:0 auto;display:grid;'
        f'grid-template-columns:2fr 6fr 3fr;gap:18px;align-items:start;">'
        f'{_kanban_sidebar_mock()}{_kanban_mock()}{_ai_pm_drawer_mock()}'
        f'</div></div>'
    )


# =========================================================================
# Section 4 — BYO-Key
# =========================================================================
def _model_row_mock(icon: str, name: str, masked_key: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;'
        f'border:1px solid {C_BORDER};border-radius:12px;margin-bottom:9px;background:#fff;">'
        f'<span style="display:inline-flex;width:34px;height:34px;border-radius:9px;'
        f'background:{C_INK};color:#fff;align-items:center;justify-content:center;'
        f'font-size:13px;font-weight:900;flex-shrink:0;">{_html.escape(icon)}</span>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:3px;">'
        f'<span style="font-weight:800;font-size:13.5px;color:{C_INK};">{_html.escape(name)}</span>'
        f'<span style="background:{C_SUCCESS_SOFT};color:{C_SUCCESS};border-radius:999px;'
        f'padding:2px 8px;font-size:10.5px;font-weight:800;">● 已配置</span>'
        f'</div>'
        f'<div style="font-size:11.5px;color:{C_INK_MUTE};font-family:monospace;">{_html.escape(masked_key)}</div>'
        f'</div>'
        f'<span style="border:1px solid {C_BORDER};border-radius:9px;padding:6px 11px;'
        f'font-size:12px;font-weight:800;color:{C_INK_SUB};background:#fff;white-space:nowrap;">管理</span>'
        f'</div>'
    )


def _byo_safety_note_mock() -> str:
    return (
        f'<div style="margin-top:16px;background:{C_PRIMARY_SOFT};border:1px solid rgba(59,91,254,.16);'
        f'border-radius:13px;padding:15px 16px;position:relative;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;">'
        f'<div style="font-size:13px;font-weight:900;color:{C_PRIMARY_INK};">🛡 数据安全与隐私</div>'
        f'<span style="background:#fff;color:{C_PRIMARY_INK};border-radius:999px;'
        f'padding:3px 9px;font-size:10.5px;font-weight:800;white-space:nowrap;">本地优先 · 端到端加密</span>'
        f'</div>'
        f'<div style="font-size:12px;color:{C_PRIMARY_INK};line-height:1.65;">'
        f'所有简历内容、API Key 与生成记录仅存储在你的本地设备，我们无法访问你的数据，也不会用于任何训练或分析。'
        f'</div>'
    )


def _download_card_mock(ext: str, color: str, title: str, sub: str) -> str:
    return (
        f'<div style="border:1px solid {C_BORDER};border-radius:13px;padding:16px 14px;'
        f'background:#fff;text-align:center;box-shadow:0 1px 2px rgba(11,18,32,.04);">'
        f'<div style="display:inline-flex;width:46px;height:52px;border-radius:9px;'
        f'background:{color};color:#fff;font-weight:900;font-size:12px;'
        f'align-items:center;justify-content:center;margin-bottom:10px;letter-spacing:.04em;">{_html.escape(ext)}</div>'
        f'<div style="font-size:13px;color:{C_INK};font-weight:900;margin-bottom:3px;">{_html.escape(title)}</div>'
        f'<div style="font-size:11.5px;color:{C_INK_MUTE};">{_html.escape(sub)}</div>'
        f'</div>'
    )


def _byo_version_history_mock() -> str:
    rows = [
        ("●", "v2.4 高级运营定制版", "当前版本", "今天 14:32", True),
        ("○", "v2.3 技术运营定制版", "", "昨天 20:15", False),
        ("○", "v2.2 产品运营定制版", "", "06-01 18:42", False),
        ("○", "v2.1 主简历（基础版）", "", "05-30 11:27", False),
    ]
    rows_html = ""
    for dot, title, chip, time_text, active in rows:
        rows_html += (
            f'<div style="display:grid;grid-template-columns:18px 1fr auto;gap:8px;'
            f'align-items:center;padding:9px 0;border-bottom:1px solid {C_BORDER if title != rows[-1][1] else "transparent"};">'
            f'<span style="color:{C_PRIMARY if active else C_INK_MUTE};font-size:13px;text-align:center;">{dot}</span>'
            f'<span style="display:flex;align-items:center;gap:7px;min-width:0;">'
            f'<span style="font-size:12.5px;font-weight:{800 if active else 600};color:{C_INK if active else C_INK_SUB};'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_html.escape(title)}</span>'
            f'{f"<span style=\"background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};border-radius:999px;padding:2px 8px;font-size:10.5px;font-weight:800;white-space:nowrap;\">{chip}</span>" if chip else ""}'
            f'</span>'
            f'<span style="font-size:11px;color:{C_INK_MUTE};white-space:nowrap;">{_html.escape(time_text)}</span>'
            f'</div>'
        )
    return (
        f'<div style="margin-top:18px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
        f'<div style="font-size:14px;font-weight:900;color:{C_INK};">版本历史</div>'
        f'<span style="font-size:12px;color:{C_PRIMARY_INK};font-weight:800;">查看全部</span>'
        f'</div>{rows_html}</div>'
    )


def _value_tile(icon: str, title: str, sub: str) -> str:
    return (
        f'<div style="background:{C_BG_SOFT};border:1px solid {C_BORDER};'
        f'border-radius:14px;padding:20px 22px;">'
        f'<div style="font-size:24px;margin-bottom:10px;line-height:1;">{icon}</div>'
        f'<div style="font-weight:700;color:{C_INK};font-size:14px;margin-bottom:6px;">{_html.escape(title)}</div>'
        f'<div style="color:{C_INK_SUB};font-size:12.5px;line-height:1.6;">{_html.escape(sub)}</div>'
        f'</div>'
    )


def _byo_panel_mock() -> str:
    tab_labels = ["在线简历编辑", "PDF 预览", "深度评估"]
    tabs_html = "".join(
        f'<span style="padding:10px 18px;font-size:13px;font-weight:800;'
        f'color:{C_PRIMARY_INK if i == 0 else C_INK_SUB};'
        f'border-bottom:2px solid {C_PRIMARY if i == 0 else "transparent"};'
        f'margin-bottom:-1px;">{_html.escape(t)}</span>'
        for i, t in enumerate(tab_labels)
    )
    return (
        f'<div style="background:#fff;border:1px solid {C_BORDER};border-radius:16px;'
        f'box-shadow:{S_LG};overflow:hidden;">'
        f'<div style="display:flex;gap:4px;padding:0 24px;border-bottom:1px solid {C_BORDER};'
        f'background:{C_BG_SOFT};">{tabs_html}</div>'
        f'<div style="padding:28px;display:grid;grid-template-columns:7fr 5fr;gap:32px;">'
        f'<div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:6px;">'
        f'<div style="font-size:15px;color:{C_INK};font-weight:900;">模型服务与 Key 管理</div>'
        f'<span style="background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};border-radius:999px;'
        f'padding:3px 9px;font-size:11px;font-weight:800;">BYO-Key</span>'
        f'</div>'
        f'<div style="font-size:12.5px;color:{C_INK_SUB};line-height:1.6;margin-bottom:14px;">'
        f'使用你自己的 API Key，数据仅在本地处理，不会上传至任何服务器。</div>'
        f'{_model_row_mock("A", "Claude (Anthropic)", "sk-ant-****-****-****")}'
        f'{_model_row_mock("Ⓞ", "OpenAI", "sk-proj-****-****-****")}'
        f'{_model_row_mock("◆", "Codex (OpenAI)", "sk-codex-****-****-****")}'
        f'{_model_row_mock("K", "Kimi", "sk-kimi-****-****-****")}'
        f'<div style="border:1px dashed {C_BORDER};border-radius:12px;padding:11px 12px;'
        f'text-align:center;color:{C_INK_SUB};font-size:12.5px;font-weight:800;background:#fff;">+ 添加自定义模型</div>'
        f'{_byo_safety_note_mock()}'
        f'</div>'
        f'<div>'
        f'<div style="font-size:15px;color:{C_INK};font-weight:900;margin-bottom:5px;">导出与下载</div>'
        f'<div style="font-size:12.5px;color:{C_INK_SUB};line-height:1.6;margin-bottom:14px;">'
        f'导出即带走，支持原稿与改写版本。</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
        f'{_download_card_mock("PDF", "#EF4444", "导出 PDF", "（原稿）")}'
        f'{_download_card_mock("DOCX", "#2563EB", "导出 DOCX", "（原稿改写）")}'
        f'{_download_card_mock("DOCX", "#2563EB", "导出 DOCX", "（模板版）")}'
        f'</div>'
        f'{_byo_version_history_mock()}'
        f'</div></div></div>'
    )


def _section_byo_key() -> None:
    _h(
        f'<div id="feature-3" style="padding:96px 56px;background:#fff;">'
        f'<div style="max-width:1280px;margin:0 auto 40px auto;display:grid;'
        f'grid-template-columns:1fr auto;gap:24px;align-items:start;">'
        f'<div style="text-align:left;">'
        f'<h2 style="font-size:44px;font-weight:800;color:{C_INK};line-height:1.2;'
        f'margin:0 0 14px 0;letter-spacing:-0.02em;">'
        f'你的 <span style="color:{C_PRIMARY};">Key</span>，你的数据，你掌控</h2>'
        f'<p style="font-size:16px;color:{C_INK_SUB};margin:0;'
        f'max-width:640px;line-height:1.6;">'
        f'自带 API Key（BYO-Key）接入任意大模型，数据仅存储在你的设备，导出即带走，安全可控。'
        f'</p></div>'
        f'<div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap;padding-top:4px;">'
        f'<span style="background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};border-radius:999px;'
        f'padding:5px 11px;font-size:12px;font-weight:800;">🛡 BYO-Key 隐私优先</span>'
        f'<span style="background:{C_PRIMARY_SOFT};color:{C_PRIMARY_INK};border-radius:999px;'
        f'padding:5px 11px;font-size:12px;font-weight:800;">🔒 数据本地加密存储</span>'
        f'</div></div>'
        f'<div style="max-width:1200px;margin:0 auto;">{_byo_panel_mock()}'
        f'<div style="margin-top:36px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">'
        f'{_value_tile("🔑", "BYO-Key 自带密钥", "支持 Claude / OpenAI / Codex / Kimi 等主流模型，自带 Key，更自由，更安全。")}'
        f'{_value_tile("🔒", "隐私优先", "数据本地处理与存储，端到端加密，不上传、不共享、不训练。")}'
        f'{_value_tile("⬇", "随时导出", "PDF / DOCX 一键导出，原稿 / 改写 / 模板多格式，随时带走你的成果。")}'
        f'</div></div></div>'
    )


# =========================================================================
# Footer CTA
# =========================================================================
def _section_footer_cta() -> None:
    _h(
        f'<div style="padding:96px 56px;background:linear-gradient(135deg,{C_PRIMARY} 0%, {C_PRIMARY_INK} 100%);">'
        f'<div style="max-width:720px;margin:0 auto;text-align:center;color:#fff;">'
        f'<h2 style="font-size:40px;font-weight:800;line-height:1.2;'
        f'margin:0 0 14px 0;letter-spacing:-0.01em;">'
        f'把找工作，变成一场可追踪的实验</h2>'
        f'<p style="font-size:16px;opacity:.85;margin:0 0 36px 0;line-height:1.6;">'
        f'免费开始，全程本地 —— 只管投简历，其它交给 CareerOS。'
        f'</p></div></div>'
        f'<div style="background:{C_INK};color:{C_INK_MUTE};padding:28px 56px;font-size:12.5px;">'
        f'<div style="max-width:1280px;margin:0 auto;display:flex;'
        f'justify-content:space-between;align-items:center;">'
        f'<div>© 2026 CareerOS · 本地优先的求职协同工具</div>'
        f'<div style="display:flex;gap:24px;">'
        f'<a href="https://github.com/cryptoyc0926/careeros" target="_blank" '
        f'style="color:inherit;text-decoration:none;">GitHub</a>'
        f'<a href="#" style="color:inherit;text-decoration:none;">文档</a>'
        f'<a href="#" style="color:inherit;text-decoration:none;">反馈</a>'
        f'</div></div></div>'
    )
    _l, cta_mid, _r = st.columns([3, 2, 3])
    with cta_mid:
        if st.button("免费开始使用 →", key="landing_cta_footer",
                     type="primary", use_container_width=True):
            _enter_app()


# =========================================================================
# 渲染
# =========================================================================
_render_topbar()
_section_hero()
_section_ai_chat()
_section_kanban()
_section_byo_key()
_section_footer_cta()
