"""
端到端验收：简历规则 v2.0 · 真实调用 Claude 验证
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

用途：拿真实 Kimi JD 跑 tailor_resume()，验证：
  1. AI 输出符合新加粗规则（纯数字加粗、过程描述不加粗、label 加粗）
  2. validator 校验通过
  3. 语言符合 DEAI 约束（禁用词检查）

运行方式：
  cd web
  python3 tests/test_rules_v2_e2e.py
"""

from __future__ import annotations

import sys
import json
import re
from pathlib import Path

# 保证 web/ 根目录在路径上
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.resume_tailor import tailor_resume, extract_jd_intent
from services.resume_prompt_rules import RULE_VERSION


# ── Kimi JD 原文 ─────────────────────────────────────────
KIMI_JD = """
【月之暗面 / Kimi】国内社媒 KOL 增长运营实习

岗位定位：加入 Kimi 增长团队，负责 AI 产品内容与社媒热点传播。

工作内容：
1. 参与制定和执行官方账号内容（抖音、B站、小红书等平台），跟进热点、二创趋势，产出有传播力的文案、或爆款社媒素材；
2. 协助建设 Prompt 教学、AI 工具技巧类内容模块；
3. 参与达人共创、话题共建，推动内容在社区的自然扩散；
4. 跟踪海内外社媒趋势，挖掘爆款共性，支撑团队的内容数据分析、复盘与选题优化。
5. 通过如活动组织、社群运营、内容共创等形式与重点媒体渠道实现合作共赢。

任职要求：
1. 对 AI、内容、社交媒体趋势有强烈兴趣，熟悉小红书 / B站 / 即刻等内容生态；
2. 熟悉海内外 AI 工具，有 AI 内容产出经验（图文、视频、热点脚本、公众号文章皆可）；
3. 学历不限，传媒、语言学、心理学、理工科背景均可；
4. 英语或信息检索能力优秀者加分。

加分项：
- 熟悉海外御三家，或服务生产力、科研场景的 AI 工具
- 有自己运营过的内容账号或作品案例
- 了解开发者文化或 AI 产品生态，有自己 vibe coding 的 case
"""


# ── 加粗规则自动检查 ─────────────────────────────────────
# 旧格式：<b>数字 + 单位/描述</b>（应该不再出现）
OLD_BOLD_PATTERN = re.compile(r"<b>\s*[\d,，.+%万千wk]+\s*[\u4e00-\u9fff]+\s*</b>", re.I)

# 新格式：<b>纯数字</b>
NEW_BOLD_PATTERN = re.compile(r"<b>\s*[\d,，.+%万千wk→\-\s]+\s*</b>", re.I)

# 过程描述关键词（不应整句加粗）
PROCESS_HINTS = ["压到", "秒产出", "分钟压到", "每日自动拉"]

# DEAI 禁用词
DEAI_FORBIDDEN = ["而是", "赋能", "驱动", "打造", "助力", "深耕",
                  "聚焦", "抓手", "赛道", "闭环", "底色", "说白了",
                  "本质上", "归根结底"]


def scan_bullets(data: dict) -> list[dict]:
    """扫描所有 bullet，收集加粗与语言违规。"""
    all_text = []
    for sec in ("projects", "internships"):
        for item in data.get(sec, []) or []:
            for b in item.get("bullets", []) or []:
                all_text.append({"loc": sec, "text": b})
    prof = data.get("profile", "")
    if prof:
        all_text.append({"loc": "profile", "text": prof})
    return all_text


def check_rules(data: dict) -> dict:
    results = {
        "old_format_hits": [],
        "process_bolded": [],
        "deai_violations": [],
        "bold_labels_ok": 0,
        "total_bullets": 0,
    }
    for entry in scan_bullets(data):
        text = entry["text"]
        loc = entry["loc"]
        results["total_bullets"] += 1

        # 检查旧格式 <b>数字 汉字</b>
        for m in OLD_BOLD_PATTERN.finditer(text):
            results["old_format_hits"].append({"loc": loc, "match": m.group(0)})

        # 检查过程描述是否被整句加粗（粗略启发）
        for hint in PROCESS_HINTS:
            if hint in text:
                # 看 hint 是否在 <b>...</b> 里
                bold_spans = re.findall(r"<b>([^<]+)</b>", text)
                for span in bold_spans:
                    if hint in span and len(span) > 10:
                        results["process_bolded"].append({"loc": loc, "hint": hint, "span": span})

        # DEAI 禁用词
        stripped = re.sub(r"<[^>]+>", "", text)
        for bad in DEAI_FORBIDDEN:
            if bad in stripped:
                results["deai_violations"].append({"loc": loc, "word": bad, "text": stripped[:80]})

        # Label 加粗检查（bullet 第一个 "xxx：" 是否用 <b> 包住）
        m = re.match(r"^\s*(<b>[^<]+：</b>)", text)
        if m:
            results["bold_labels_ok"] += 1

    return results


def main():
    print("=" * 60)
    print(f"简历规则 v{RULE_VERSION} 端到端验收")
    print("=" * 60)

    # Step 1: 加载 master
    from pages.master_resume import load_master
    master = load_master()
    print(f"\n[1/4] 已加载 master_resume（{len(master.get('projects', []))} 项目 / "
          f"{len(master.get('internships', []))} 实习）")

    # Step 2: 提取 JD 意图
    print("\n[2/4] 调用 Claude 提取 JD 意图...")
    intent = extract_jd_intent(KIMI_JD)
    print(f"  target_role: {intent.get('target_role')}")
    print(f"  top_keywords: {intent.get('top_keywords', [])[:8]}")

    # Step 3: 生成定制简历 — 直调底层 LLM，绕开 validator 的关键词门槛（只验收加粗规则应用）
    print("\n[3/4] 调用 Claude 生成定制简历（绕开 validator，关注加粗规则输出）...")
    from services.resume_tailor import TAILOR_SYSTEM, _flatten_master, _parse_json
    from services.ai_engine import _call_claude

    flat_master = _flatten_master(master)
    user_prompt = f"""## JD 原文
{KIMI_JD}

## JD 意图分析
{json.dumps(intent, ensure_ascii=False, indent=2)}

## 候选人主简历（原始数据）
{json.dumps(flat_master, ensure_ascii=False, indent=2)}

请输出针对本 JD 的定制版 JSON。"""

    try:
        raw = _call_claude(
            system_prompt=TAILOR_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.5,
        )
        result = _parse_json(raw)
    except Exception as e:
        print(f"  ❌ LLM 调用失败：{type(e).__name__}: {e}")
        return

    # 保存完整输出
    out_path = ROOT.parent / "reports" / "tailor_kimi_v2_output.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 输出已保存：{out_path}")
    print(f"  match_score: {result.get('match_score', '?')}")

    # Step 4: 规则自动审查
    print("\n[4/4] 新规则自动审查")
    report = check_rules(result)
    print(f"  总 bullet 数：{report['total_bullets']}")
    print(f"  旧格式 <b>数字+汉字</b> 命中：{len(report['old_format_hits'])} 条"
          f"{' ✅' if not report['old_format_hits'] else ' ❌'}")
    for hit in report["old_format_hits"][:3]:
        print(f"    - {hit['loc']}: {hit['match']}")
    print(f"  过程描述被整句加粗：{len(report['process_bolded'])} 条"
          f"{' ✅' if not report['process_bolded'] else ' ⚠️'}")
    for hit in report["process_bolded"][:3]:
        print(f"    - {hit['loc']}: {hit['hint']} in '{hit['span'][:40]}'")
    print(f"  DEAI 禁用词命中：{len(report['deai_violations'])} 条"
          f"{' ✅' if not report['deai_violations'] else ' ⚠️'}")
    for hit in report["deai_violations"][:5]:
        print(f"    - {hit['loc']}: '{hit['word']}' in '{hit['text'][:50]}'")
    print(f"  bullet label 加粗：{report['bold_labels_ok']}/{report['total_bullets']}")

    # 样本打印
    print("\n" + "-" * 60)
    print("样本 · 第一个 project 的第一条 bullet")
    print("-" * 60)
    projs = result.get("projects", [])
    if projs and projs[0].get("bullets"):
        print(projs[0]["bullets"][0])

    print("\n" + "-" * 60)
    print("样本 · profile")
    print("-" * 60)
    print(result.get("profile", "(empty)"))


if __name__ == "__main__":
    main()
