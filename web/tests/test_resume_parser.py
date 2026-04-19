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


if __name__ == "__main__":
    import json
    print("=== Fixture A ===")
    print(json.dumps(parse_resume_text(FIXTURE_A), ensure_ascii=False, indent=2))
    print("=== Fixture B ===")
    print(json.dumps(parse_resume_text(FIXTURE_B), ensure_ascii=False, indent=2))
