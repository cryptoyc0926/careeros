"""数据分析 — 求职全局总览与行动漏斗。"""

import streamlit as st
import pandas as pd
from models.database import query
from components.ui import (
    page_header, section_title, divider, badge,
    summary_card_hero, soft_stat_card, apple_section_heading,
    funnel_stage_card, diagnostic_alert,
    BG_SURFACE, BORDER_SOFTER, RADIUS_LG, SHADOW_CARD, FONT_SANS,
    TEXT_STRONG, TEXT_MUTED, ACCENT_BLUE, SP_2, SP_3,
)

page_header(
    "数据分析",
    subtitle="看清转化进度，也看清瓶颈",
    right_text="返回首页",
    right_page="pages/home.py",
)


def render_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, empty_text: str) -> None:
    """Render a compact HTML bar list without invoking Vega charts."""
    chart_df = df[[x_col, y_col]].copy()
    chart_df[y_col] = pd.to_numeric(chart_df[y_col], errors="coerce").fillna(0)
    chart_df = chart_df[chart_df[y_col] > 0]
    if chart_df.empty:
        st.caption(empty_text)
        return
    max_value = float(chart_df[y_col].max()) or 1.0
    rows = []
    for _, row in chart_df.iterrows():
        label = str(row[x_col] or "未分类")
        value = float(row[y_col])
        width = max(4, min(100, round(value / max_value * 100)))
        value_text = str(int(value)) if value.is_integer() else f"{value:g}"
        rows.append(
            f'<div style="display:grid;grid-template-columns:72px 1fr 36px;'
            f'align-items:center;gap:10px;margin:9px 0;font-family:{FONT_SANS}">'
            f'<span style="font-size:12px;color:{TEXT_MUTED};white-space:nowrap">{label}</span>'
            f'<span style="height:10px;background:rgba(0,113,227,0.10);border-radius:99px;overflow:hidden">'
            f'<span style="display:block;width:{width}%;height:100%;background:{ACCENT_BLUE};border-radius:99px"></span>'
            f'</span>'
            f'<span style="font-size:12px;color:{TEXT_STRONG};text-align:right;font-variant-numeric:tabular-nums">{value_text}</span>'
            f'</div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 核心指标 — 从 jobs_pool (真实数据) + job_descriptions 双源汇总
# ══════════════════════════════════════════════════════════════

try:
    # jobs_pool 统计
    jp_total = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE COALESCE(status,'NEW') != '已排除'")[0]["c"]
    jp_p0 = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE 等级='P0' AND COALESCE(status,'NEW') != '已排除'")[0]["c"]
    jp_applied = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE status='已投递'")[0]["c"]
    jp_new = query("SELECT COUNT(*) AS c FROM jobs_pool WHERE COALESCE(status,'NEW')='NEW'")[0]["c"]
    jp_avg = query("SELECT ROUND(AVG(匹配分),1) AS c FROM jobs_pool WHERE COALESCE(status,'NEW') != '已排除'")[0]["c"] or 0
except Exception:
    jp_total = jp_p0 = jp_applied = jp_new = 0
    jp_avg = 0

try:
    # job_descriptions 统计（面试/offer 阶段）
    jd_interview = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE status='interview'")[0]["c"]
    jd_offer = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE status='offer'")[0]["c"]
    jd_rejected = query("SELECT COUNT(*) AS c FROM job_descriptions WHERE status='rejected'")[0]["c"]
except Exception:
    jd_interview = jd_offer = jd_rejected = 0

# ── 第一行：核心数字（1 主卡 + 5 次卡，与首页一致）──────────────

main_col, side_col = st.columns([1, 1.4], gap="large")
with main_col:
    summary_card_hero(
        value=jp_total,
        label="岗位池",
        hint=f"平均匹配分 {jp_avg}" if jp_avg else "",
    )
with side_col:
    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1: soft_stat_card(jp_p0, "P0 岗位")
    with c2: soft_stat_card(jp_new, "待行动")
    with c3: soft_stat_card(jp_applied, "已投递")
    with c4: soft_stat_card(jd_interview, "面试中")
    with c5: soft_stat_card(jd_offer, "Offer")

# ══════════════════════════════════════════════════════════════
# 求职漏斗 — 从发现到拿Offer的转化可视化
# ══════════════════════════════════════════════════════════════
# 漏斗逻辑：
#   发现岗位(全部) → P0筛选 → 已投递 → 面试 → Offer
#   每个阶段显示数量和转化率，帮助你识别瓶颈：
#   - P0/总数 低 → 岗位质量不够，需要优化搜索策略
#   - 已投递/P0 低 → 行动力不足，今天就去投
#   - 面试/已投递 低 → 简历需要优化
#   - Offer/面试 低 → 面试准备不足

apple_section_heading("求职转化漏斗", "每个阶段的转化率帮你定位瓶颈 — 哪个环节在拖后腿")

funnel_stages = [
    ("发现岗位",   jp_total),
    ("P0 筛选",    jp_p0),
    ("已投递",     jp_applied),
    ("面试中",     jd_interview),
    ("拿到 Offer", jd_offer),
]

# 横向漏斗
cols = st.columns(len(funnel_stages))
for i, (label, count) in enumerate(funnel_stages):
    with cols[i]:
        if i > 0:
            prev_count = funnel_stages[i - 1][1]
            rate = f"↓ {count / prev_count * 100:.0f}%" if prev_count > 0 else "↓ —"
        else:
            rate = "起点"
        funnel_stage_card(label, count, rate_hint=rate)

# 漏斗诊断
if jp_total > 0 and jp_applied == 0:
    diagnostic_alert("danger", f"瓶颈：零投递 — 岗位池有 {jp_total} 个岗位但还没开始投递。先投 P0 里匹配分最高的 3 个。")
elif jp_p0 > 0 and jp_applied > 0 and jp_applied / jp_p0 < 0.3:
    diagnostic_alert("info", f"P0 投递率 {jp_applied}/{jp_p0} = {jp_applied/jp_p0*100:.0f}%，还有 {jp_p0 - jp_applied} 个 P0 待投递")
elif jp_applied > 0 and jd_interview == 0:
    diagnostic_alert("info", f"已投递 {jp_applied} 个，还没有面试邀约 — 检查简历匹配度，或跟进 HR")
elif jd_interview > 0 and jd_offer == 0:
    diagnostic_alert("success", f"{jd_interview} 个面试进行中，做好面试准备")
elif jd_offer > 0:
    diagnostic_alert("success", f"已拿到 {jd_offer} 个 Offer")

# ══════════════════════════════════════════════════════════════
# 岗位等级分布 + 今日快报
# ══════════════════════════════════════════════════════════════

divider()

left, right = st.columns([1, 1])

with left:
    apple_section_heading("岗位等级分布")
    try:
        dist = query("SELECT 等级, COUNT(*) AS 数量 FROM jobs_pool WHERE COALESCE(status,'NEW') != '已排除' GROUP BY 等级 ORDER BY 等级")
        if dist:
            df_dist = pd.DataFrame(dist)
            render_bar_chart(df_dist, "等级", "数量", "暂无数据")
        else:
            st.caption("暂无数据")
    except Exception:
        st.caption("暂无数据")

with right:
    apple_section_heading("P0 待行动清单")
    try:
        p0_new = query(
            "SELECT 公司, 岗位名称, 匹配分, 今日行动 FROM jobs_pool "
            "WHERE 等级='P0' AND COALESCE(status,'NEW')='NEW' "
            "ORDER BY 匹配分 DESC LIMIT 8"
        )
        if p0_new:
            for r in p0_new:
                score = int(r["匹配分"]) if r["匹配分"] else 0
                action = r["今日行动"] or "待定"
                short_action = action[:30] + "…" if len(action) > 30 else action
                st.markdown(
                    f'<div style="background:{BG_SURFACE};border:1px solid {BORDER_SOFTER};'
                    f'padding:12px 14px;border-radius:{RADIUS_LG};margin:6px 0;'
                    f'box-shadow:{SHADOW_CARD};font-family:{FONT_SANS}">'
                    f'<div style="font-size:13px;font-weight:600;color:{TEXT_STRONG}">'
                    f'{r["公司"]} · {r["岗位名称"]} '
                    f'<span style="color:{ACCENT_BLUE};font-size:12px;font-weight:500;'
                    f'margin-left:6px;font-variant-numeric:tabular-nums">{score} 分</span></div>'
                    f'<div style="font-size:12px;color:{TEXT_MUTED};margin-top:4px">{short_action}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("所有 P0 岗位都已处理")
    except Exception:
        st.caption("暂无数据")

# ══════════════════════════════════════════════════════════════
# 匹配分分布
# ══════════════════════════════════════════════════════════════

apple_section_heading("匹配分分布")

try:
    scores = query("SELECT 匹配分 FROM jobs_pool WHERE COALESCE(status,'NEW') != '已排除' AND 匹配分 IS NOT NULL")
    if scores:
        df_scores = pd.DataFrame(scores)
        # 分桶统计
        bins = {"90+": 0, "80-89": 0, "70-79": 0, "60-69": 0, "<60": 0}
        for s in df_scores["匹配分"]:
            if s >= 90: bins["90+"] += 1
            elif s >= 80: bins["80-89"] += 1
            elif s >= 70: bins["70-79"] += 1
            elif s >= 60: bins["60-69"] += 1
            else: bins["<60"] += 1
        df_bins = pd.DataFrame({"分数段": list(bins.keys()), "岗位数": list(bins.values())})
        render_bar_chart(df_bins, "分数段", "岗位数", "暂无评分数据")
    else:
        st.caption("暂无评分数据")
except Exception:
    st.caption("暂无评分数据")

# ══════════════════════════════════════════════════════════════
# 投递模式分析（Phase 3.2）
# ══════════════════════════════════════════════════════════════

apple_section_heading("投递模式分析")

try:
    # 各渠道统计
    channel_stats = query(
        """SELECT apply_channel, COUNT(*) AS total,
                  SUM(CASE WHEN status='已投递' THEN 1 ELSE 0 END) AS applied
           FROM jobs_pool
           WHERE apply_channel IS NOT NULL
           GROUP BY apply_channel"""
    )
    if channel_stats:
        ch_left, ch_right = st.columns(2)
        with ch_left:
            apple_section_heading("各渠道投递数")
            ch_labels = {"boss": "Boss直聘", "email": "邮件", "referral": "内推",
                         "portal": "校招门户", "maimai": "脉脉", "wechat": "企业微信"}
            df_ch = pd.DataFrame(channel_stats)
            df_ch["渠道"] = df_ch["apply_channel"].map(lambda x: ch_labels.get(x, x))
            render_bar_chart(df_ch, "渠道", "total", "暂无渠道数据")

        with ch_right:
            apple_section_heading("跟进状态")
            followup_stats = query(
                """SELECT
                      SUM(CASE WHEN followup_count = 0 THEN 1 ELSE 0 END) AS 未跟进,
                      SUM(CASE WHEN followup_count = 1 THEN 1 ELSE 0 END) AS 跟进1次,
                      SUM(CASE WHEN followup_count >= 2 THEN 1 ELSE 0 END) AS 跟进2次以上
                   FROM jobs_pool WHERE status='已投递'"""
            )
            if followup_stats:
                fs = followup_stats[0]
                fc1, fc2, fc3 = st.columns(3)
                with fc1: soft_stat_card(fs.get("未跟进", 0), "未跟进")
                with fc2: soft_stat_card(fs.get("跟进1次", 0), "跟进1次")
                with fc3: soft_stat_card(fs.get("跟进2次以上", 0), "跟进2次+")

    # 各等级响应率
    priority_stats = query(
        """SELECT 等级,
                  COUNT(*) AS total,
                  SUM(CASE WHEN status='已投递' THEN 1 ELSE 0 END) AS applied
           FROM jobs_pool
           WHERE COALESCE(status,'NEW') != '已排除'
           GROUP BY 等级 ORDER BY 等级"""
    )
    if priority_stats:
        apple_section_heading("各等级投递率")
        for ps in priority_stats:
            total = ps["total"]
            applied = ps["applied"]
            rate = f"{applied/total*100:.0f}%" if total > 0 else "0%"
            st.caption(f"{ps['等级']}: {applied}/{total} = {rate}")
    else:
        st.caption("暂无投递数据")
except Exception:
    st.caption("暂无投递分析数据")

# ── 底部信息 ─────────────────────────────────────────────────
divider()
jd_total = query('SELECT COUNT(*) AS c FROM job_descriptions')[0]['c']
st.caption(f"数据来源：jobs_pool {jp_total} 条 · job_descriptions {jd_total} 条 · 今日 {__import__('datetime').date.today()}")
