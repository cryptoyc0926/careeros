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
#  全局 CSS — CareerOS Indigo White Shell (v4)
#  Token 来源：new UI 靛蓝白体系（白底 + 单 accent + 极浅边框）
#  字体：SF Pro / PingFang SC / Inter（无衬线统一，无 Instrument Serif）
#  按钮：Primary = Indigo #3B5BFE；Secondary = 白底 + 极浅边框
# ═════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ═══ 1. 全局基底 ══════════════════════════════════════════ */
html, body, [class*="css"], .stApp {
    font-family: "Inter", "SF Pro Text", "SF Pro Display", -apple-system, BlinkMacSystemFont,
                 "PingFang SC", "Helvetica Neue", Inter, "Noto Sans SC", sans-serif !important;
    background-color: #FFFFFF !important;   /* 页面底色 */
    color: #0B1220 !important;              /* 主文本 */
    font-size: 15px;
    letter-spacing: -0.08px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ═══ 2. 顶部 Header ══════════════════════════════════════ */
[data-testid="stHeader"] {
    background: rgba(255,255,255,0.8) !important;
    border-bottom: 1px solid rgba(11,18,32,0.06) !important;
}
[data-testid="stHeader"] * { color: #6B7280 !important; }
[data-testid="stToolbar"] {
    display: flex !important;
    visibility: visible !important;
    pointer-events: none !important;
    background: transparent !important;
}
[data-testid="stToolbar"] > div {
    visibility: hidden !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] *,
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] * {
    visibility: visible !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {
    display: flex !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 100000 !important;
    align-items: center !important;
    width: auto !important;
    min-width: 112px !important;
    min-height: 36px !important;
    padding: 8px 12px !important;
    justify-content: flex-start !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    color: #0B1220 !important;
    box-shadow: 0 4px 16px rgba(11,18,32,0.08) !important;
    pointer-events: auto !important;
}
[data-testid="stExpandSidebarButton"]::after,
[data-testid="collapsedControl"]::after {
    content: "展开导航";
    margin-left: 6px;
    font-size: 13px;
    font-weight: 600;
    line-height: 1;
    color: #0B1220;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="collapsedControl"] svg {
    width: 16px !important;
    height: 16px !important;
}
[data-testid="stDecoration"] { display: none !important; }

/* ═══ 3. 侧边栏（弱化后台感，融入页面底色）══════════════════ */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid rgba(11,18,32,0.06) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] a { color: #6B7280 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] strong {
    color: #0B1220 !important;
}
[data-testid="stSidebarCollapsedControl"] button {
    background: #ffffff !important;
    color: #6B7280 !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
}

/* 侧边栏导航激活态 — Indigo 淡底 + 字重变化 */
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] li[aria-selected="true"] > a {
    color: #3B5BFE !important;
    font-weight: 600 !important;
    background: rgba(59,91,254,0.06) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebarNav"] a { color: #6B7280 !important; border-radius: 6px !important; }
[data-testid="stSidebarNav"] a:hover { color: #0B1220 !important; background: rgba(11,18,32,0.03) !important; }

/* ═══ 4. 主内容区（浅灰页面 + 宽度 1080）══════════════════════ */
section[data-testid="stMain"] { background: #FFFFFF !important; }
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1080px !important;
    background: transparent !important;
}
.stMainBlockContainer { background: transparent !important; }

/* ═══ 5. 文字层级（无 Serif，纯无衬线）════════════════════════ */
h1, h2, h3, h4, h5, h6 {
    color: #0B1220 !important;
    font-family: "Inter", "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont,
                 "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.2px !important;
}
p, li, span, label { color: #0B1220; }
.stMarkdown p {
    color: #0B1220 !important;
    line-height: 1.55 !important;
    font-size: 15px !important;
}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #0B1220 !important; }
[data-testid="stCaptionContainer"], .stCaption {
    color: #6B7280 !important;
    font-size: 12px !important;
}
code {
    background: #F7F8FA !important;
    color: #0B1220 !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
    border-radius: 6px;
    font-family: "SF Mono", ui-monospace, Menlo, monospace;
    font-size: 13px !important;
}

/* ═══ 6. 按钮 — 三层级统一（v5：多 selector 联合 + 兜底）═════════
 * Primary   = Indigo #3B5BFE + 白字
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
    font-family: "Inter", "SF Pro Text", -apple-system, "PingFang SC", sans-serif !important;
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
    color: #0B1220 !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
}
/* DownloadButton 继承基础样式 + Indigo primary（当 kind=primary）*/
.stDownloadButton button,
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    letter-spacing: -0.08px !important;
    padding: 9px 18px !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-family: "Inter", "SF Pro Text", -apple-system, "PingFang SC", sans-serif !important;
    line-height: 1.2 !important;
}
.stDownloadButton button:hover,
[data-testid="stDownloadButton"] button:hover {
    background-color: #F7F8FA !important;
    border-color: rgba(11,18,32,0.16) !important;
    color: #0B1220 !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton button:active,
[data-testid="stDownloadButton"] button:active {
    transform: translateY(0) scale(0.98) !important;
}
.stDownloadButton button:focus-visible {
    box-shadow: 0 0 0 3px rgba(59,91,254,0.25) !important;
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
    background-color: #3B5BFE !important;
    background: #3B5BFE !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 1px 2px rgba(59,91,254,0.2) !important;
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
    background-color: #2A46D8 !important;
    background: #2A46D8 !important;
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
/* Focus ring — 3px 靛蓝外环，键盘访问性 */
.stButton button:focus-visible,
button[data-testid^="stBaseButton"]:focus-visible {
    box-shadow: 0 0 0 3px rgba(59,91,254,0.25) !important;
    outline: none !important;
}
.stButton button[kind="primary"]:disabled,
button[data-testid="stBaseButton-primary"]:disabled {
    background-color: rgba(11,18,32,0.08) !important;
    background: rgba(11,18,32,0.08) !important;
    color: rgba(11,18,32,0.48) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Secondary — 已由兜底规则覆盖白底深字，这里只补 hover */
.stButton button:hover,
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: #F7F8FA !important;
    background: #F7F8FA !important;
    border-color: rgba(11,18,32,0.16) !important;
    color: #0B1220 !important;
    transform: translateY(-1px) !important;
}
/* Primary hover 必须覆盖 secondary hover（靠后定义）*/
.stButton button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #2A46D8 !important;
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
    border: 1px solid rgba(11,18,32,0.08) !important;
    border-radius: 10px !important;
    color: #0B1220 !important;
    font-size: 15px !important;
    padding: 10px 12px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #3B5BFE !important;
    box-shadow: 0 0 0 3px rgba(59,91,254,0.12) !important;
}
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: #ffffff !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
    border-radius: 10px !important;
    color: #0B1220 !important;
}
/* Dropdown popover */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="select"] [data-baseweb="popover"] {
    background: #ffffff !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.08) !important;
}
[data-baseweb="option"] { color: #0B1220 !important; }
[data-baseweb="option"]:hover { background: #F7F8FA !important; }

/* Multiselect 选中 chip — 从黑底橙字改为极浅灰底深字 */
.stMultiSelect [data-baseweb="tag"],
[data-baseweb="select"] [data-baseweb="tag"],
span[data-baseweb="tag"] {
    background-color: #FFFFFF !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
    color: #0B1220 !important;
    border-radius: 6px !important;
}
.stMultiSelect [data-baseweb="tag"] *,
span[data-baseweb="tag"] * {
    color: #0B1220 !important;
    background: transparent !important;
}
.stMultiSelect [data-baseweb="tag"] svg,
span[data-baseweb="tag"] svg {
    fill: #6B7280 !important;
    color: #6B7280 !important;
}

/* Number input 加减按钮（+ / -）— 黑底改为白底 */
.stNumberInput button,
[data-testid="stNumberInput"] button {
    background: #ffffff !important;
    color: #0B1220 !important;
    border: 1px solid rgba(11,18,32,0.08) !important;
}
.stNumberInput button:hover,
[data-testid="stNumberInput"] button:hover {
    background: #F7F8FA !important;
}
.stNumberInput [data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
}

/* Radio 按钮组内的圆点 — Indigo */
[data-baseweb="radio"] [data-testid="stMarkdownContainer"],
.stRadio label {
    color: #0B1220 !important;
}
[data-baseweb="radio"] div[role="radio"][aria-checked="true"] {
    border-color: #3B5BFE !important;
    background: #3B5BFE !important;
}

/* Card hover（避免使用会被 sanitizer 剥离的内联事件）*/
a.apple-action-card:hover,
a.apple-feature-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
    transform: translateY(-2px) !important;
    border-color: rgba(11,18,32,0.12) !important;
}
/* Card focus-visible — 键盘访问性 3px 靛蓝环 */
a.apple-action-card:focus-visible,
a.apple-feature-card:focus-visible {
    box-shadow: 0 0 0 3px rgba(59,91,254,0.25) !important;
    outline: none !important;
    border-color: rgba(11,18,32,0.12) !important;
}

/* ═══ 8. 表格 / DataFrame ══════════════════════════════════ */
.stDataFrame {
    border: 1px solid rgba(11,18,32,0.06) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stDataFrame table { background: #ffffff !important; }
.stDataFrame th {
    background: #F7F8FA !important;
    color: #6B7280 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(11,18,32,0.06) !important;
}
.stDataFrame td {
    background: #ffffff !important;
    color: #0B1220 !important;
    border-bottom: 1px solid rgba(11,18,32,0.04) !important;
    font-size: 13px !important;
}
.stDataFrame tr:hover td { background: #F7F8FA !important; }

/* ═══ 9. Expander ══════════════════════════════════════════ */
details, .streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
    border-radius: 12px !important;
    color: #0B1220 !important;
}
.streamlit-expanderContent {
    background: #F7F8FA !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* ═══ 10. 原生 Metric 卡（保留兜底样式，首选用 soft_stat_card）═══ */
[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
[data-testid="metric-container"] label {
    color: #6B7280 !important;
    font-size: 12px !important;
}
[data-testid="stMetricValue"] {
    color: #0B1220 !important;
    font-size: 24px !important;
    font-weight: 600 !important;
    font-family: "SF Pro Display", -apple-system, "PingFang SC", sans-serif !important;
    letter-spacing: -0.24px !important;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ═══ 11. Tabs（细下划线）═══════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(11,18,32,0.06) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6B7280 !important;
    border-bottom: 2px solid transparent !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 18px !important;
    transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #0B1220 !important; }
.stTabs [aria-selected="true"] {
    color: #0B1220 !important;
    border-bottom-color: #0B1220 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 20px !important;
}

/* ═══ 12. Alert ══════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 3px !important;
    background: #F7F8FA !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
}
.stAlert [data-testid="stMarkdownContainer"] p { color: #0B1220 !important; }

/* ═══ 13. 进度条 ══════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: #3B5BFE !important;
    border-radius: 99px !important;
}
.stProgress > div > div {
    background: rgba(11,18,32,0.06) !important;
    border-radius: 99px !important;
}

/* ═══ 14. Radio / Checkbox ════════════════════════════════ */
.stRadio label, .stCheckbox label { color: #0B1220 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #6B7280 !important; }

/* ═══ 15. Slider ══════════════════════════════════════════ */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #3B5BFE !important;
    border-color: #3B5BFE !important;
}

/* ═══ 16. 分隔线 ══════════════════════════════════════════ */
hr { border-color: rgba(11,18,32,0.06) !important; margin: 24px 0 !important; }

/* ═══ 17. Spinner ════════════════════════════════════════ */
.stSpinner > div { border-top-color: #3B5BFE !important; }

/* ═══ 18. 图表 — 白底，无黑框，细灰网格 ═════════════ */
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
    border: 1px solid rgba(11,18,32,0.06) !important;
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
    stroke: rgba(11,18,32,0.06) !important;
}

/* ═══ 18b. DataFrame — 删除黑框，细灰分隔 ══════════════════ */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stTable"],
.stDataFrame,
.stDataFrame > div,
.stDataFrame iframe {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid rgba(11,18,32,0.06) !important;
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
    color: #6B7280 !important;
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
    color: #0B1220 !important;
    border: none !important;
}
/* View more/less 文字本身（可能在 span 内部）*/
[data-testid="stSidebarNav"] button *,
[data-testid="stSidebar"] button[kind="navToggle"] * {
    color: #6B7280 !important;
    font-weight: 400 !important;
}

/* ═══ 19. 底部工具栏 ════════════════════════════════════ */
[data-testid="stStatusWidget"] { color: #6B7280 !important; }
footer { display: none !important; }

/* ═══ 19b. 顶部 Deploy 按钮（自用工具无需 Streamlit 公网部署入口）═════ */
[data-testid="stDeployButton"] { display: none !important; }

/* ═══ 20. 数字 tabular 字形（stat 卡专用）═══════════════════ */
.cos-num {
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.2px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar 导航文案本地化：Streamlit 内置的 View more / View less ───
# st.markdown 会剥离 <script>，必须用 components.v1.html 在 iframe 内执行
# JS，再经 window.parent.document 挂 MutationObserver。flag 挡重复 rerun。
from streamlit.components.v1 import html as _careeros_html_inject  # noqa: E402

_careeros_html_inject(
    """
<script>
(function(){
  var doc = (window.parent && window.parent.document) || document;
  if (doc.__careerosSidebarLocalized) return;
  doc.__careerosSidebarLocalized = true;
  function localize(){
    var b = doc.querySelector('[data-testid="stSidebarNavViewButton"]');
    if (!b) return;
    var t = (b.textContent || '').trim();
    if (t === 'View more') b.textContent = '\u67e5\u770b\u66f4\u591a \u25be';
    else if (t === 'View less') b.textContent = '\u6536\u8d77 \u25b4';
  }
  localize();
  var mo = new MutationObserver(localize);
  mo.observe(doc.body, {childList:true, subtree:true, characterData:true});
})();
</script>
    """,
    height=0,
)

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


# ── 对外 Landing 路由 ──────────────────────────────────────
# 未 entered_app → 显示 Landing 官网；点 CTA 后 entered_app=True 走工作台
if "entered_app" not in st.session_state:
    st.session_state["entered_app"] = False

# 允许通过 query param 跳过 landing（开发/分享直达）
try:
    _qp = st.query_params
    if _qp.get("app") == "1":
        st.session_state["entered_app"] = True
except Exception:
    pass

if not st.session_state["entered_app"]:
    # 执行 pages/landing.py 作为对外官网
    # 进入时标记 "just_landed"，下次 rerun 进主应用后注入 scrollTop=0
    st.session_state["_pending_scroll_top"] = True
    from pathlib import Path as _P
    _landing = _P(__file__).parent / "pages" / "landing.py"
    if _landing.exists():
        exec(compile(_landing.read_text(encoding="utf-8"), str(_landing), "exec"),
             {"__file__": str(_landing)})
        st.stop()

# ── 从 Landing 进主应用时：scrollTop=0 避免继承 Landing 的滚动位置 ─
# st.markdown 会剥离 <script>，走 components.v1.html 的 iframe 才能真执行。
# Streamlit 1.38+ 把 scrollable main 从 stMain 改成 section.main，多选器兜底。
if st.session_state.get("_pending_scroll_top"):
    st.session_state["_pending_scroll_top"] = False
    _careeros_html_inject(
        """
<script>
setTimeout(function(){
  var doc = (window.parent && window.parent.document) || document;
  var win = (window.parent && window.parent.window) || window;
  var m = doc.querySelector('[data-testid="stMain"]')
       || doc.querySelector('section.main')
       || doc.querySelector('[data-testid="stAppViewContainer"]');
  if (m) m.scrollTop = 0;
  win.scrollTo(0, 0);
}, 80);
</script>
        """,
        height=0,
    )

# ── DEMO_MODE 全局提示条 ────────────────────────────────
if settings.demo_mode:
    st.markdown(
        '<div style="background:#fff8e1;border:1px solid rgba(217,119,6,0.25);'
        'border-left:3px solid #d97706;padding:10px 16px;border-radius:10px;'
        'font-size:13px;color:#0B1220;margin:0 0 12px 0;'
        'font-family:\'SF Pro Text\',-apple-system,sans-serif">'
        '<b>在线 Demo（共享额度 + BYO-Key）</b> · '
        '默认可用 Codex 共享额度试用，也可以在「系统设置」填入你自己的 API Key；'
        '作者不会保存你的任何数据。长期使用建议 '
        '<a href="https://github.com/cryptoyc0926/careeros" target="_blank" style="color:#3B5BFE;text-decoration:none">自部署本地版</a>。'
        '</div>',
        unsafe_allow_html=True,
    )

# ── 导航 ──────────────────────────────────────────────────
pages = {
    "": [
        st.Page("pages/home.py", title="总览", default=True),
    ],
    "简历定制": [
        st.Page("pages/resume_tailor.py",    title="在线定制"),
        st.Page("pages/history_versions.py", title="历史版本"),
        st.Page("pages/master_resume.py",    title="简历管理"),
        st.Page("pages/resume_templates.py", title="简历模板"),
    ],
    "求职工具": [
        st.Page("pages/job_pool.py",          title="岗位池"),
    ],
    "资源中心": [
        st.Page("pages/star_pool.py",    title="素材库"),
        st.Page("pages/case_library.py", title="案例库"),
    ],
    "系统": [
        st.Page("pages/settings_page.py", title="设置"),
        st.Page("pages/help_feedback.py", title="帮助反馈"),
    ],
}

nav = st.navigation(pages)

# ── 侧边栏底部 ────────────────────────────────────────────
from components.ui import divider as _apple_divider
with st.sidebar:
    _apple_divider()
    if st.button("← 返回首页", key="_sidebar_back_to_landing", use_container_width=True):
        st.session_state["entered_app"] = False
        st.rerun()
    st.caption("Career OS v0.1.0")
    if settings.has_anthropic_key:
        st.caption("AI Provider · 已连接")
    else:
        st.caption("AI Provider · 未配置")

# ── 运行选中页面 ──────────────────────────────────────────
nav.run()
