"""
Career OS — 主入口
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
启动方式:  streamlit run app.py

使用 Streamlit st.navigation / st.Page API (v1.36+)
实现多页面路由和分组侧边栏。
"""

import streamlit as st
from pathlib import Path
from config import settings

# ── 页面配置（必须是第一个 Streamlit 调用）─────────────────
st.set_page_config(
    page_title="Career OS",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════
#  全局 CSS — Nature × Apple Design Language (v4)
#  Token 来源：plan Appendix A（Apple 暖灰 + 单 accent + 极浅边框）
#  字体：SF Pro / PingFang SC / Inter（无衬线统一，无 Instrument Serif）
#  按钮：Primary = Apple Blue #0071e3；Secondary = 白底 + 极浅边框
# ═════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ═══ 1. 全局基底 ══════════════════════════════════════════ */
html, body, [class*="css"], .stApp {
    font-family: "SF Pro Text", "SF Pro Display", -apple-system, BlinkMacSystemFont,
                 "PingFang SC", "Helvetica Neue", Inter, "Noto Sans SC", sans-serif !important;
    background-color: #f5f5f7 !important;   /* Apple 标准页面底色 */
    color: #1d1d1f !important;              /* Apple near-black */
    font-size: 15px;
    letter-spacing: -0.08px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ═══ 2. 顶部 Header ══════════════════════════════════════ */
[data-testid="stHeader"] {
    background: rgba(245,245,247,0.8) !important;
    border-bottom: 1px solid rgba(29,29,31,0.06) !important;
}
[data-testid="stHeader"] * { color: #6e6e73 !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ═══ 3. 侧边栏（弱化后台感，融入页面底色）══════════════════ */
[data-testid="stSidebar"] {
    background-color: #f5f5f7 !important;
    border-right: 1px solid rgba(29,29,31,0.06) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] a { color: #6e6e73 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] strong {
    color: #1d1d1f !important;
}
[data-testid="stSidebarCollapsedControl"] button {
    background: #ffffff !important;
    color: #6e6e73 !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
}

/* 侧边栏导航激活态 — Apple Blue 淡底 + 字重变化 */
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] li[aria-selected="true"] > a {
    color: #0071e3 !important;
    font-weight: 600 !important;
    background: rgba(0,113,227,0.06) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebarNav"] a { color: #6e6e73 !important; border-radius: 6px !important; }
[data-testid="stSidebarNav"] a:hover { color: #1d1d1f !important; background: rgba(29,29,31,0.03) !important; }

/* ═══ 4. 主内容区（浅灰页面 + 宽度 1080）══════════════════════ */
section[data-testid="stMain"] { background: #f5f5f7 !important; }
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1080px !important;
    background: transparent !important;
}
.stMainBlockContainer { background: transparent !important; }

/* ═══ 5. 文字层级（无 Serif，纯无衬线）════════════════════════ */
h1, h2, h3, h4, h5, h6 {
    color: #1d1d1f !important;
    font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont,
                 "PingFang SC", "Helvetica Neue", Inter, "Noto Sans SC", sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.2px !important;
}
p, li, span, label { color: #1d1d1f; }
.stMarkdown p {
    color: #1d1d1f !important;
    line-height: 1.55 !important;
    font-size: 15px !important;
}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1d1d1f !important; }
[data-testid="stCaptionContainer"], .stCaption {
    color: #6e6e73 !important;
    font-size: 12px !important;
}
code {
    background: #fafafc !important;
    color: #1d1d1f !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 6px;
    font-family: "SF Mono", ui-monospace, Menlo, monospace;
    font-size: 13px !important;
}

/* ═══ 6. 按钮 — 三层级统一（v5：多 selector 联合 + 兜底）═════════
 * Primary   = Apple Blue #0071e3 + 白字
 * Secondary = 白底 + 极浅边框 + 深字
 * Danger    = 红底白字（key 含 "danger" 时生效）
 * Streamlit 1.36+ DOM：button 不再是 .stButton 的直接子元素，
 *                    属性从 kind="secondary" 迁到 data-testid="stBaseButton-secondary"
 *                    所以必须多 selector 联合，+ 最后兜底强制白底深字
 * 禁止黑框按钮 / 禁止胶囊按钮 / 禁止窄列挤压换行
 * ══════════════════════════════════════════════════════════ */

/* 基础（所有按钮共享）*/
.stButton button,
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    letter-spacing: -0.08px !important;
    padding: 9px 18px !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-family: "SF Pro Text", -apple-system, "PingFang SC", Inter, sans-serif !important;
    white-space: nowrap !important;
    min-width: 0 !important;
    line-height: 1.2 !important;
}

/* 终极兜底 — 任何 stButton / stDownloadButton 内的 button 默认白底深字 */
.stButton button,
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button,
.stDownloadButton button,
[data-testid="stDownloadButton"] button {
    background-color: #ffffff !important;
    color: #1d1d1f !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
}
/* DownloadButton 继承基础样式 + Apple Blue primary（当 kind=primary）*/
.stDownloadButton button,
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    letter-spacing: -0.08px !important;
    padding: 9px 18px !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-family: "SF Pro Text", -apple-system, "PingFang SC", Inter, sans-serif !important;
    line-height: 1.2 !important;
}
.stDownloadButton button:hover,
[data-testid="stDownloadButton"] button:hover {
    background-color: #fafafc !important;
    border-color: rgba(29,29,31,0.16) !important;
    color: #1d1d1f !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton button:active,
[data-testid="stDownloadButton"] button:active {
    transform: translateY(0) scale(0.98) !important;
}
.stDownloadButton button:focus-visible {
    box-shadow: 0 0 0 3px rgba(0,113,227,0.25) !important;
    outline: none !important;
}

/* Primary — 多 selector 联合 */
.stButton button[kind="primary"],
.stButton button[data-testid="stBaseButton-primary"],
.stButton button[data-testid*="Primary"],
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
    background-color: #0071e3 !important;
    background: #0071e3 !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 1px 2px rgba(0,113,227,0.2) !important;
}
/* 强制 Primary 按钮内所有后代（包括 markdown 包裹的 <p><span><div>）都白字 */
.stButton button[kind="primary"] *,
button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-primaryFormSubmit"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
}
.stButton button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background-color: #005bb5 !important;
    background: #005bb5 !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
}
.stButton button[kind="primary"]:active,
button[data-testid="stBaseButton-primary"]:active {
    background-color: #004a96 !important;
    background: #004a96 !important;
    transform: translateY(0) scale(0.98) !important;
}
/* Secondary active — 同款细微压缩反馈 */
.stButton button:active,
button[data-testid="stBaseButton-secondary"]:active,
button[data-testid="stBaseButton-secondaryFormSubmit"]:active {
    transform: translateY(0) scale(0.98) !important;
}
/* Focus ring — Apple 标准 3px 蓝色外环，键盘访问性 */
.stButton button:focus-visible,
button[data-testid^="stBaseButton"]:focus-visible {
    box-shadow: 0 0 0 3px rgba(0,113,227,0.25) !important;
    outline: none !important;
}
.stButton button[kind="primary"]:disabled,
button[data-testid="stBaseButton-primary"]:disabled {
    background-color: rgba(29,29,31,0.08) !important;
    background: rgba(29,29,31,0.08) !important;
    color: rgba(29,29,31,0.48) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Secondary — 已由兜底规则覆盖白底深字，这里只补 hover */
.stButton button:hover,
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: #fafafc !important;
    background: #fafafc !important;
    border-color: rgba(29,29,31,0.16) !important;
    color: #1d1d1f !important;
    transform: translateY(-1px) !important;
}
/* Primary hover 必须覆盖 secondary hover（靠后定义）*/
.stButton button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #005bb5 !important;
    color: #ffffff !important;
}

/* Danger — key 含 "danger" 的破坏性按钮（Streamlit 会把 key 写入 DOM 的 key 属性或 data-testid）*/
.stButton:has(button[kind]) button[key*="danger"],
.stButton button[id*="danger"],
div[data-testid="stButton"][class*="danger"] button,
button[data-testid*="danger"] {
    background-color: #dc2626 !important;
    background: #dc2626 !important;
    color: #ffffff !important;
    border: none !important;
}
/* 稳妥兜底：通过 element id (Streamlit 会把 key 注入 id) 选中 */
button[kind][id*="danger"],
.element-container:has(button[id*="danger"]) button {
    background-color: #dc2626 !important;
    background: #dc2626 !important;
    color: #ffffff !important;
    border: none !important;
}
button[kind][id*="danger"]:hover {
    background-color: #b91c1c !important;
    background: #b91c1c !important;
    color: #ffffff !important;
}

/* 窄列挤压防护 — columns 内按钮不拉伸、不换行 */
[data-testid="stHorizontalBlock"] .stButton button {
    white-space: nowrap !important;
    min-width: 0 !important;
    padding-left: 12px !important;
    padding-right: 12px !important;
}

/* ═══ 7. 输入框 / 选择框 / 多选 ════════════════════════════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
    border-radius: 10px !important;
    color: #1d1d1f !important;
    font-size: 15px !important;
    padding: 10px 12px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0071e3 !important;
    box-shadow: 0 0 0 3px rgba(0,113,227,0.12) !important;
}
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
    border-radius: 10px !important;
    color: #1d1d1f !important;
}
/* Dropdown popover */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="select"] [data-baseweb="popover"] {
    background: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.08) !important;
}
[data-baseweb="option"] { color: #1d1d1f !important; }
[data-baseweb="option"]:hover { background: #fafafc !important; }

/* Multiselect 选中 chip — 从黑底橙字改为极浅灰底深字（Apple style） */
.stMultiSelect [data-baseweb="tag"],
[data-baseweb="select"] [data-baseweb="tag"],
span[data-baseweb="tag"] {
    background-color: #f5f5f7 !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
    color: #1d1d1f !important;
    border-radius: 6px !important;
}
.stMultiSelect [data-baseweb="tag"] *,
span[data-baseweb="tag"] * {
    color: #1d1d1f !important;
    background: transparent !important;
}
.stMultiSelect [data-baseweb="tag"] svg,
span[data-baseweb="tag"] svg {
    fill: #6e6e73 !important;
    color: #6e6e73 !important;
}

/* Number input 加减按钮（+ / -）— 黑底改为白底 */
.stNumberInput button,
[data-testid="stNumberInput"] button {
    background: #ffffff !important;
    color: #1d1d1f !important;
    border: 1px solid rgba(29,29,31,0.08) !important;
}
.stNumberInput button:hover,
[data-testid="stNumberInput"] button:hover {
    background: #fafafc !important;
}
.stNumberInput [data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
}

/* Radio 按钮组内的圆点 — 橙色改为 Apple Blue */
[data-baseweb="radio"] [data-testid="stMarkdownContainer"],
.stRadio label {
    color: #1d1d1f !important;
}
[data-baseweb="radio"] div[role="radio"][aria-checked="true"] {
    border-color: #0071e3 !important;
    background: #0071e3 !important;
}

/* Apple card hover（避免使用会被 sanitizer 剥离的内联事件）*/
a.apple-action-card:hover,
a.apple-feature-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
    transform: translateY(-2px) !important;
    border-color: rgba(29,29,31,0.12) !important;
}
/* Apple card focus-visible — 键盘访问性 3px 蓝环 */
a.apple-action-card:focus-visible,
a.apple-feature-card:focus-visible {
    box-shadow: 0 0 0 3px rgba(0,113,227,0.25) !important;
    outline: none !important;
    border-color: rgba(29,29,31,0.12) !important;
}

/* ═══ 8. 表格 / DataFrame ══════════════════════════════════ */
.stDataFrame {
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stDataFrame table { background: #ffffff !important; }
.stDataFrame th {
    background: #fafafc !important;
    color: #6e6e73 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(29,29,31,0.06) !important;
}
.stDataFrame td {
    background: #ffffff !important;
    color: #1d1d1f !important;
    border-bottom: 1px solid rgba(29,29,31,0.04) !important;
    font-size: 13px !important;
}
.stDataFrame tr:hover td { background: #fafafc !important; }

/* ═══ 9. Expander ══════════════════════════════════════════ */
details, .streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 12px !important;
    color: #1d1d1f !important;
}
.streamlit-expanderContent {
    background: #fafafc !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* ═══ 10. 原生 Metric 卡（保留兜底样式，首选用 soft_stat_card）═══ */
[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
[data-testid="metric-container"] label {
    color: #6e6e73 !important;
    font-size: 12px !important;
}
[data-testid="stMetricValue"] {
    color: #1d1d1f !important;
    font-size: 24px !important;
    font-weight: 600 !important;
    font-family: "SF Pro Display", -apple-system, "PingFang SC", sans-serif !important;
    letter-spacing: -0.24px !important;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ═══ 11. Tabs（Apple 式细下划线）═══════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(29,29,31,0.06) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6e6e73 !important;
    border-bottom: 2px solid transparent !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 18px !important;
    transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #1d1d1f !important; }
.stTabs [aria-selected="true"] {
    color: #1d1d1f !important;
    border-bottom-color: #1d1d1f !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 20px !important;
}

/* ═══ 12. Alert ══════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 3px !important;
    background: #fafafc !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
}
.stAlert [data-testid="stMarkdownContainer"] p { color: #1d1d1f !important; }

/* ═══ 13. 进度条 ══════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: #0071e3 !important;
    border-radius: 99px !important;
}
.stProgress > div > div {
    background: rgba(29,29,31,0.06) !important;
    border-radius: 99px !important;
}

/* ═══ 14. Radio / Checkbox ════════════════════════════════ */
.stRadio label, .stCheckbox label { color: #1d1d1f !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #6e6e73 !important; }

/* ═══ 15. Slider ══════════════════════════════════════════ */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #0071e3 !important;
    border-color: #0071e3 !important;
}

/* ═══ 16. 分隔线 ══════════════════════════════════════════ */
hr { border-color: rgba(29,29,31,0.06) !important; margin: 24px 0 !important; }

/* ═══ 17. Spinner ════════════════════════════════════════ */
.stSpinner > div { border-top-color: #0071e3 !important; }

/* ═══ 18. 图表 — Apple 风格（白底，无黑框，细灰网格）═════════════ */
.js-plotly-plot .plotly,
.vega-embed,
.vega-embed canvas,
.vega-embed svg,
[data-testid="stVegaLiteChart"],
[data-testid="stVegaLiteChart"] canvas,
[data-testid="stVegaLiteChart"] svg,
[data-testid="stBarChart"],
[data-testid="stLineChart"],
[data-testid="stAreaChart"],
.stVegaLiteChart,
.stPlotlyChart {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    padding: 12px !important;
}
/* 图表内部 canvas/svg 本身透明（被外层白底包住即可），避免双层白造成内阴影 */
.vega-embed canvas,
.vega-embed svg,
[data-testid="stVegaLiteChart"] canvas,
[data-testid="stVegaLiteChart"] svg {
    background: transparent !important;
    background-color: transparent !important;
}
/* Vega 网格线颜色（Streamlit 默认黑）*/
.vega-embed .mark-rule line,
.vega-embed .gridline {
    stroke: rgba(29,29,31,0.06) !important;
}

/* ═══ 18b. DataFrame — 删除黑框，Apple 细灰分隔 ══════════════════ */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stTable"],
.stDataFrame,
.stDataFrame > div,
.stDataFrame iframe {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid rgba(29,29,31,0.06) !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
/* glide-data-grid（Streamlit dataframe 底层）*/
[data-testid="stDataFrame"] canvas,
[data-testid="stDataFrameResizable"] canvas {
    background: #ffffff !important;
}
[data-testid="stDataFrame"] [data-testid="stDataFrameScrollArea"] {
    background: #ffffff !important;
}

/* ═══ 18c. Sidebar "View more / View less" 导航折叠链接 ═══════════ */
/* Streamlit 默认给折叠按钮深色 bg — 改成无框灰字链接样式 */
[data-testid="stSidebarNav"] button,
[data-testid="stSidebarNav"] a,
[data-testid="stSidebar"] button[kind="navToggle"],
[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] + button {
    background: transparent !important;
    background-color: transparent !important;
    color: #6e6e73 !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    padding: 4px 12px !important;
    text-align: left !important;
    justify-content: flex-start !important;
}
[data-testid="stSidebarNav"] button:hover,
[data-testid="stSidebar"] button[kind="navToggle"]:hover {
    background: transparent !important;
    color: #1d1d1f !important;
    border: none !important;
}
/* View more/less 文字本身（可能在 span 内部）*/
[data-testid="stSidebarNav"] button *,
[data-testid="stSidebar"] button[kind="navToggle"] * {
    color: #6e6e73 !important;
    font-weight: 400 !important;
}

/* ═══ 19. 底部工具栏 ════════════════════════════════════ */
[data-testid="stStatusWidget"] { color: #6e6e73 !important; }
footer { display: none !important; }

/* ═══ 20. 数字 tabular 字形（stat 卡专用）═══════════════════ */
.cos-num {
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.2px;
}
</style>
""", unsafe_allow_html=True)

# ── 每次启动都跑 init_db 补齐缺失的表（幂等 · IF NOT EXISTS）───
# 说明：init_db 用 CREATE TABLE IF NOT EXISTS，对已有表无副作用。
# 这样 schema 升级后老用户的 db 也能自动补新表（例如 jobs_pool 等核心业务表）。
db_path = settings.db_full_path
db_path.parent.mkdir(parents=True, exist_ok=True)
try:
    from scripts.init_db import init_database
    init_database(db_path)
except Exception as _init_err:
    # 即使 init 失败（比如表已存在 + 不兼容变更）也让页面继续渲染，报错给用户看
    st.warning(f"数据库初始化遇到警告：{type(_init_err).__name__}: {_init_err}")

# ── DEMO_MODE 全局提示条 ────────────────────────────────
if settings.demo_mode:
    st.markdown(
        '<div style="background:#fff8e1;border:1px solid rgba(217,119,6,0.25);'
        'border-left:3px solid #d97706;padding:10px 16px;border-radius:10px;'
        'font-size:13px;color:#1d1d1f;margin:0 0 12px 0;'
        'font-family:\'SF Pro Text\',-apple-system,sans-serif">'
        '<b>在线 Demo（共享额度 + BYO-Key）</b> · '
        '默认可用 Codex 共享额度试用，也可以在「系统设置」填入你自己的 API Key；'
        '作者不会保存你的任何数据。长期使用建议 '
        '<a href="https://github.com/cryptoyc0926/careeros" target="_blank" style="color:#0071e3;text-decoration:none">自部署本地版</a>。'
        '</div>',
        unsafe_allow_html=True,
    )

# ── 导航 ──────────────────────────────────────────────────
pages = {
    "仪表盘": [
        st.Page("pages/home.py",      title="首页",    default=True),
        st.Page("pages/analytics.py", title="数据分析"),
    ],
    "目标岗位": [
        st.Page("pages/jd_input.py",   title="添加岗位 JD"),
        st.Page("pages/jd_browser.py", title="浏览 JD 库"),
        st.Page("pages/job_pool.py",   title="岗位池"),
    ],
    "简历管理": [
        st.Page("pages/master_resume.py",  title="主简历"),
        st.Page("pages/resume_tailor.py",  title="在线定制编辑"),
        st.Page("pages/star_pool.py",      title="经历素材库"),
    ],
    "投递进度": [
        st.Page("pages/pipeline.py",        title="看板追踪"),
        st.Page("pages/followup.py",        title="跟进提醒"),
        st.Page("pages/email_composer.py",  title="邮件撰写"),
    ],
    "面试准备": [
        st.Page("pages/interview.py",      title="模拟面试"),
        st.Page("pages/interview_prep.py", title="题库 & 故事"),
    ],
    "系统": [
        st.Page("pages/settings_page.py", title="设置"),
    ],
}

nav = st.navigation(pages)

# ── 侧边栏底部 ────────────────────────────────────────────
from components.ui import divider as _apple_divider
with st.sidebar:
    _apple_divider()
    st.caption("Career OS v0.1.0")
    if settings.has_anthropic_key:
        st.caption("AI Provider · 已连接")
    else:
        st.caption("AI Provider · 未配置")

# ── 运行选中页面 ──────────────────────────────────────────
nav.run()
