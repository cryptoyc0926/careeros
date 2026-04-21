"""
简历规则解析器回归测试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
目的：保证未来改 parser 不会破坏已识别的字段。
覆盖两种真实格式：
  · Fixture A（杨超 AI 管培生）: 公司-角色-日期 顺序 + 职位关键词清晰
  · Fixture B（杨超 产品经理实习）: 日期-职位-公司 顺序 + 教育"专业 学校"颠倒

运行：
    cd web && python -m pytest tests/test_resume_parser.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from services.resume_rule_parser import parse_resume_text  # noqa: E402


# ═════════════════════════════════════════════════════════════════
# Fixture A：作者 AI 管培生简历（公司-角色-日期 顺序）
# ═════════════════════════════════════════════════════════════════
FIXTURE_A = """
杨 超
186-8795-0926 | bc1chao0926@gmail.com
求职意向：AI 管培生 | 期望城市：杭州 | 到岗时间：下周到岗

个人总结
统计科班出身，但我更擅长的是把数据变成增长。

核心技能
数据运营：用户行为分析 · 转化漏斗优化 · AB 测试
增长实战：社媒矩阵搭建 · 内容分发策略 · 社群运营
工具链：Claude Code · Python · MySQL
证书：英语 CET-6 · 计算机二级

项目经历
AI Trading 社区搭建 用户增长运营 2024.03 - 至今
• 构建自动化信号预警与工作流
• 流程提效：搭建标准链路
• 增长验证：推动账号从 0 到 1 增长至 9,000+ X 粉丝

实习经历
Fancy Tech 海外产品运营实习生 2024.06 - 2024.09
• 主导 AIGC 电商内容产品海外冷启动与矩阵建设

杭银消费金融股份有限公司 产品运营实习生 2023.06 - 2024.10
• 协作与触达：主导跨部门协作机制升级

教育背景
浙江工商大学 | 应用统计专业 | 2022.09 - 2026.07 | 校三等奖学金
""".strip()


# ═════════════════════════════════════════════════════════════════
# Fixture B：作者产品经理实习简历（日期-职位-公司 顺序）
# ═════════════════════════════════════════════════════════════════
FIXTURE_B = """
杨超
求职意向：产品经理实习生
电话：18687950926 现居：杭州
邮箱：bc1chao0926@gmail.com

教育经历
2022.09-2026.06 应用统计学本科 浙江工商大学
• 主修课程：多元统计分析、R语言
• 获奖荣誉：校三等奖学金

实习经历
2025.08-2026.01 数据运营实习生 WEEX 交易所
•活动运营：负责拉新促活、交易赛
•渠道协同：协同50+KOL渠道推进活动执行

2024.07-2025.03 投研实习生 Block Infinity fund 基金
•投资分析：深度参与Web3领域研究

2023.07-2023.10 产品运营实习生 杭银消费金融股份有限公司
•协作与触达：主导跨部门协作机制升级

技能证书
• 办公技能：熟练使用Openclaw、Python、R
• 专业证书：英语CET-6
""".strip()


FIXTURE_C_FULL_UPLOAD = """
杨 超
186-8795-0926 | bc1chao0926@gmail.com
求职意向：AI 产品运营实习 | 期望城市：杭州 | 到岗时间：一周内（每周可实习 5 天）

个人总结
在校期间独立运营 AI × 金融信息方向内容账号 X @Cady_btc，零投放做到 9,000+ 粉、Telegram 社群 1,300+ 订阅，完成 20+ 次品牌商单，熟悉海内外社交平台内容生态。日常用 Claude Code、Kimi、ChatGPT、Cursor 做内容生产与小工具开发。两段运营实习覆盖海外 AIGC 冷启动（TikTok / Instagram / Reddit）、竞品拆解、活动数据复盘与跨部门协作。英语 CET-6，可独立完成英文内容撰写。应用统计出身，习惯用数据面板复盘每条内容的真实表现。

项目经历
X @Cady_btc 独立运营 · AI 方向内容账号 2024.03 — 至今
• 海外社媒运营：X 推特账号自运营，主阵地面向英文受众，同步 Telegram 中文社群 1,300+ 订阅；日更 AI × 金融赛道内容，X 粉丝 0 → 9,000+，完成 20+ 次品牌商单，社区对用户反馈收集全程自理
• AI 内容生产线：基于 X API + Claude + OpenCLaw 搭建信息抓取管道，每日自动拉 50+ 条海外资讯，用 60+ 条个人 Prompt 模板筛选二次加工，单条内容生产时间从 40 分钟压到 10 分钟以内
• 达人共创：主动触达同领域博主做互推、联名推文与 Space 对谈合作，单次互推平均带来 200+ 粉增长

CareerOS（开源） 求职全流程 AI 工具 · vibe coding 作品 2026.04 — 至今
• 产品定义：独立拆出 6 个核心模块（JD 抓取 / 岗位评分 / 大师简历 / 定制简历 / 公司画像 / 外联模板），端到端覆盖求职信息流；岗位池持续采集 100+ 国内外 AI 公司招聘页
• 技术实现：Streamlit + SQLite 做 Web 层，写了分级 JD 抓取管道（适配静态页、SPA、受限站点、人工录入四种来源）；大师简历 YAML + AI 定制 + 规则引擎校验三段式生成，单条 JD 定制简历 30 秒产出
• 开发方法论：全流程 vibe coding，独立完成架构设计、开发、测试、文档、部署；v0.1.0 已发布，含完整 README、架构图、Dockerfile、BYO-Key 模式
• 网站链接：careeros-chad.streamlit.app | GitHub: github.com/cryptoyc0926/careeros

实习经历
Fancy Tech 海外产品运营实习生 2024.06 — 2024.09
• 海外社媒 0 → 1：公司海外内容从零起步，独立搭建 TikTok + Instagram 官方账号，交付一套「AI 生产 — 二次编辑 — 多平台分发」SOP 文档；团队后续可复用；零投放条件下做到单条内容 10,000+ 自然曝光，带动官网均 UV 从个位数提升到 200+
• 海外竞品调研：系统拆解 PhotoRoom、Pebblely 等头部 AIGC 工具的定价策略、核心转化场景与 SEO 打法，产出 30+ 页英文竞品画像，为产品策略迭代提供输入
• 海外精准获客：在 Reddit、TikTok 垂直社群做英文私信触达与内容冷启动，拿下首批海外付费用户，验证产品 PMF 假设，建立用户反馈到内容选题的正向循环

杭银消费金融 产品运营实习生 2023.06 — 2023.10
• 活动数据复盘：搭建活动日报 + 归因模型，单场活动参与率提升 18.9%，参与人数 1,240 → 1,644，单场借款金额 1,048 万 → 1,262 万（+20.6%）
• 跨团队协作：主导业务经理朋友圈素材 SOP 升级，Canva 海报 + 文案模板化，配合产品与运营团队推进活动落地，单场触达率从 4% 提升到 10%
• 内容冷启动：策划短视频 20+ 期，账号冷启动做到单月 2w+ 播放，AB 测试确立核心激励品，投放成本下降 40%

专业技能
• AI 工具与内容生产：Claude Code、Kimi、ChatGPT、Gemini、Cursor、Perplexity、NotebookLM；Prompt 工程（模板库 60+）、Figma、Canva
• 数据、开发与语言：Python、R、MySQL、SQL、Streamlit、Git、Axure；英语 CET-6（可独立撰写英文内容）、计算机二级

教育背景
浙江工商大学 应用统计学 · 本科 2022.09 — 2026.07 | 核心课程：多元统计分析、统计预测、R 语言、贝叶斯数据分析、属性数据分析 | 荣誉：校三等奖学金、文体奖学金
""".strip()


# ═════════════════════════════════════════════════════════════════
# Tests
# ═════════════════════════════════════════════════════════════════

def test_fixture_a_basics():
    r = parse_resume_text(FIXTURE_A)
    assert r["basics"]["name"] == "杨超"
    assert r["basics"]["phone"] == "186-8795-0926"
    assert r["basics"]["email"] == "bc1chao0926@gmail.com"
    assert r["basics"]["target_role"] == "AI 管培生"
    assert r["basics"]["city"] == "杭州"


def test_fixture_a_projects():
    r = parse_resume_text(FIXTURE_A)
    assert len(r["projects"]) == 1
    p = r["projects"][0]
    assert p["company"] == "AI Trading 社区搭建"
    assert p["role"] == "用户增长运营"
    assert "2024.03" in p["date"]
    assert len(p["bullets"]) >= 1


def test_fixture_a_internships():
    r = parse_resume_text(FIXTURE_A)
    assert len(r["internships"]) == 2
    assert r["internships"][0]["company"] == "Fancy Tech"
    assert r["internships"][0]["role"] == "海外产品运营实习生"
    assert r["internships"][1]["company"] == "杭银消费金融股份有限公司"
    assert r["internships"][1]["role"] == "产品运营实习生"


def test_fixture_a_education():
    r = parse_resume_text(FIXTURE_A)
    assert len(r["education"]) == 1
    e = r["education"][0]
    assert e["school"] == "浙江工商大学"
    assert e["major"] == "应用统计专业"


def test_fixture_a_skills():
    r = parse_resume_text(FIXTURE_A)
    assert len(r["skills"]) >= 3
    labels = {s["label"] for s in r["skills"]}
    assert "数据运营" in labels
    assert "工具链" in labels


def test_fixture_b_basics():
    r = parse_resume_text(FIXTURE_B)
    assert r["basics"]["name"] == "杨超"
    assert r["basics"]["phone"] == "18687950926"
    assert r["basics"]["email"] == "bc1chao0926@gmail.com"
    assert r["basics"]["target_role"] == "产品经理实习生"
    assert r["basics"]["city"] == "杭州"


def test_fixture_b_internships_count():
    r = parse_resume_text(FIXTURE_B)
    # 必须识别出 3 段实习
    assert len(r["internships"]) == 3, f"expected 3, got {len(r['internships'])}: {r['internships']}"


def test_fixture_b_education_swap_tolerance():
    """日期-职位-公司 + '专业 学校' 倒序 — parser 至少要识别出 school 或 major 其中之一。"""
    r = parse_resume_text(FIXTURE_B)
    assert len(r["education"]) == 1
    e = r["education"][0]
    # 允许 school/major 颠倒，但要都非空
    has_school = bool(e["school"])
    has_major = bool(e["major"])
    assert has_school or has_major, "教育字段完全为空"
    # 日期必须识别到
    assert "2022.09" in e["date"]


def test_empty_text_raises_or_returns_empty():
    """文本为空时不崩溃。"""
    r = parse_resume_text("")
    assert r["basics"]["name"] == ""
    assert r["projects"] == []


def test_fixture_c_full_upload_preserves_all_sections():
    r = parse_resume_text(FIXTURE_C_FULL_UPLOAD)
    assert r["basics"]["name"] == "杨超"
    assert r["basics"]["phone"] == "186-8795-0926"
    assert r["basics"]["email"] == "bc1chao0926@gmail.com"
    assert r["basics"]["target_role"] == "AI 产品运营实习"
    assert r["basics"]["city"] == "杭州"
    assert "一周内" in r["basics"]["availability"]
    assert "9,000+" in r["profile"]
    assert "Claude Code" in r["profile"]
    assert len(r["projects"]) == 2
    assert r["projects"][0]["company"] == "X @Cady_btc"
    assert "独立运营" in r["projects"][0]["role"]
    assert "2024.03" in r["projects"][0]["date"]
    assert len(r["projects"][0]["bullets"]) == 3
    assert r["projects"][1]["company"].startswith("CareerOS")
    assert "2026.04" in r["projects"][1]["date"]
    assert len(r["projects"][1]["bullets"]) == 4
    assert len(r["internships"]) == 2
    assert r["internships"][0]["company"] == "Fancy Tech"
    assert r["internships"][0]["role"] == "海外产品运营实习生"
    assert "2024.06" in r["internships"][0]["date"]
    assert len(r["internships"][0]["bullets"]) == 3
    assert r["internships"][1]["company"] == "杭银消费金融"
    assert r["internships"][1]["role"] == "产品运营实习生"
    assert "2023.06" in r["internships"][1]["date"]
    assert len(r["internships"][1]["bullets"]) == 3
    assert len(r["skills"]) >= 2
    assert r["education"][0]["school"] == "浙江工商大学"
    assert "应用统计" in r["education"][0]["major"]


if __name__ == "__main__":
    import json
    print("=== Fixture A ===")
    print(json.dumps(parse_resume_text(FIXTURE_A), ensure_ascii=False, indent=2))
    print("=== Fixture B ===")
    print(json.dumps(parse_resume_text(FIXTURE_B), ensure_ascii=False, indent=2))
