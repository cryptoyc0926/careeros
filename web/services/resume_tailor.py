"""
Resume Tailor — JD 定制简历改写引擎
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
三步链路：
  1. extract_jd_intent(jd_text)      → {target_role, top_keywords, must_have, nice_to_have}
  2. tailor_resume(master, intent)   → 完整 data dict（可直接喂 renderer）
  3. rewrite_section(...)            → 单段重写（profile / project bullets / internship bullets）

约束（硬规则，写进 prompt）：
  - 公司名、时间、学历等事实不可改
  - 数字必须保留 <b> 加粗
  - bullet 数量不减不加，保持原结构
  - 只改措辞和侧重方向
"""

from __future__ import annotations

import json
import copy
import hashlib
from typing import Any

from .ai_engine import _call_claude, AIError
from .resume_prompt_rules import FULL_STYLE_RULES, BOLD_RULES_BRIEF, RULE_VERSION


# ── Step 1: JD 意图提取 ─────────────────────────────────
JD_INTENT_SYSTEM = """你是一个 JD 意图分析器。用户提供一段中国互联网/AI 公司的 JD 原文，你输出结构化意图。

严格按 JSON 输出，不要有任何其他内容：
{
  "target_role": "AI增长运营" | "增长运营" | "产品运营" | "数据运营" | "内容运营" | "用户运营" | "需求分析师" | "其他（具体名字）",
  "role_direction": "一句话总结这个岗位的核心方向（≤30字）",
  "top_keywords": ["关键词1", "关键词2", ...],   // 8-12 个
  "must_have": ["硬性要求1", ...],               // JD 明确要求
  "nice_to_have": ["加分项1", ...],
  "tone": "技术型" | "业务型" | "内容型" | "数据型"
}"""


def extract_jd_intent(jd_text: str) -> dict:
    raw = _call_claude(
        system_prompt=JD_INTENT_SYSTEM,
        user_prompt=f"JD 原文：\n\n{jd_text}",
        max_tokens=1024,
        temperature=0.2,
    )
    return _parse_json(raw)


# ── Step 2: 整份简历定制 ─────────────────────────────────
TAILOR_SYSTEM = f"""你是一位顶级的中文简历定制顾问，服务对象是求职候选人（见下方主简历提供的个人信息）。

你的任务：根据目标 JD 的意图，把候选人的「主简历」改写成「针对本岗位的定制版」。

## 硬规则（违反即失败）
1. **公司名、时间、学校、专业、学历** 不可修改
2. **原文中出现的所有数字必须全部保留**（数值、百分比、倍数、单位一个都不能丢；格式可以按下方加粗规则重新包裹）
3. **bullet 数量** 保持不变
4. **不编造** 任何未在原素材中出现的项目、数据、技能
5. 只改：职位 title 朝 JD 方向靠、bullet 措辞和关键词、profile 总结语

## 改写方向
- 如果 JD 是「数据运营」→ 把 bullet 的措辞往"数据驱动、漏斗、AB测试、归因"靠
- 如果 JD 是「AI 增长」→ 突出 AI 工具使用、自动化、增长杠杆
- 如果 JD 是「产品运营」→ 突出产品迭代、需求洞察、用户反馈
- Profile 个人总结整段重写，融入 JD 的 top_keywords

{FULL_STYLE_RULES}

## 输出格式（严格 JSON，不要任何其他文字）
{
  "basics": {
    "target_role": "定制后的求职意向文案（例如：AI 增长运营）",
    "_name": "姓名不修改",
    "_phone": "...",
    "_email": "...",
    "_city": "...",
    "_availability": "..."
  },
  "profile": "针对本 JD 重写后的个人总结（70-130 字，含 <b>数字</b>）",
  "projects": [
    { "company": "原公司名(不变)", "role": "可微调", "date": "原日期(不变)",
      "bullets": ["重写后的 bullet 1（保留 <b>数字</b>）", "..."] }
  ],
  "internships": [
    { "company": "原(不变)", "role": "可朝 JD 方向微调", "date": "原(不变)", "bullets": [...] }
  ],
  "skills": [
    { "label": "重新排序/改写", "text": "朝 JD 方向" }
  ],
  "match_score": 0-100 的匹配度整数,
  "change_notes": "一段话说明你做了哪些改动及为什么（≤150字）"
}"""


def tailor_resume(master: dict, jd_text: str, jd_intent: dict | None = None) -> dict:
    """输入主简历 + JD，输出定制后的完整 data dict + 匹配度 + 改动说明。"""
    if jd_intent is None:
        jd_intent = extract_jd_intent(jd_text)

    # 简化 master：把 profile pool 折叠成默认文本
    flat_master = _flatten_master(master)

    # ── T3: 从 STAR 素材池召回候选，给 AI 做选料参考 ──
    star_candidates: list[dict] = []
    star_ids_used: list[int] = []
    try:
        from services.star_pool import find_best_matches, bump_used
        matches = find_best_matches(jd_intent, n=8)
        star_ids_used = [m.id for m in matches if m.id]
        star_candidates = [
            {
                "id": m.id,
                "bullet": m.bullet_text,
                "source": f"{m.source_type}:{m.source_company}",
                "direction_tags": m.direction_tags,
                "outcome_tags": m.outcome_tags,
                "impact": m.impact,
            }
            for m in matches
        ]
    except Exception:
        pass  # 素材池为空或表不存在时降级为纯原文改写

    star_section = ""
    if star_candidates:
        star_section = (
            "\n## STAR 素材池候选（按匹配度排序，可优先采用）\n"
            "改写 bullet 时，如果候选池里有更贴合 JD 的素材，可以直接采用其正文（"
            "替换原 bullet），但必须满足：\n"
            "  - source 的 company 与对应位置的主简历经历一致；\n"
            "  - 数字 <b> 标签、bullet 数量不变。\n\n"
            + json.dumps(star_candidates, ensure_ascii=False, indent=2)
        )

    user_prompt = f"""## JD 原文
{jd_text}

## JD 意图分析
{json.dumps(jd_intent, ensure_ascii=False, indent=2)}

## 候选人主简历（原始数据）
{json.dumps(flat_master, ensure_ascii=False, indent=2)}
{star_section}

请输出针对本 JD 的定制版 JSON。"""

    raw = _call_claude(
        system_prompt=TAILOR_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=4096,
        temperature=0.5,
    )
    result = _parse_json(raw)

    # ── T6 硬规则校验（失败直接抛，不自动重试）──
    from services.resume_validator import validate_tailored, ValidationError
    report = validate_tailored(flat_master, result, jd_intent)
    if not report.ok:
        raise ValidationError(report)

    # 合并回完整 data 结构（renderer 需要的扁平格式）
    merged = _merge_tailored(flat_master, result, jd_intent)
    # 把校验报告 + 素材池使用信息附到 _meta
    meta = merged.setdefault("_meta", {})
    meta["validation"] = report.as_dict()
    meta["star_candidates_offered"] = len(star_candidates)

    # 更新素材池 used_count（召回过就 +1，不管 AI 最终选没选，作为相关度信号）
    try:
        if star_ids_used:
            from services.star_pool import bump_used
            bump_used(star_ids_used)
    except Exception:
        pass

    return merged


# ── Step 3: 单段重写 ─────────────────────────────────────
SECTION_REWRITE_SYSTEM = f"""你是简历单段改写器。用户给你一段原文 + JD 方向，你返回改写后的同等长度文本。

硬规则：
- 原文所有数字必须全部保留（数值、百分比、单位一个都不能丢）
- 长度误差 ±15% 以内
- 不编造新事实
- 只输出改写后的纯文本，不要解释、不要 markdown、不要 JSON

{BOLD_RULES_BRIEF}"""


def rewrite_section(original: str, jd_intent: dict, hint: str = "") -> str:
    """针对单个 bullet 或 profile 段落重写。"""
    user_prompt = f"""原文：
{original}

目标岗位方向：{jd_intent.get("target_role", "")}
核心关键词：{", ".join(jd_intent.get("top_keywords", [])[:6])}
{"额外要求：" + hint if hint else ""}

请输出改写后的版本（一行，不要解释）。"""
    return _call_claude(
        system_prompt=SECTION_REWRITE_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=512,
        temperature=0.6,
    ).strip()


# ── 工具函数 ─────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = "\n".join(t.split("\n")[1:-1])
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(t[start:end])
            except json.JSONDecodeError:
                pass
    raise AIError(f"JSON 解析失败：{text[:200]}...")


def _flatten_master(master: dict) -> dict:
    """把 resume_master 的 profile pool 折叠成默认文本，得到 renderer 直接可用的扁平结构。"""
    flat = copy.deepcopy(master)
    profile = flat.get("profile")
    if isinstance(profile, dict) and "pool" in profile:
        default_id = profile.get("default")
        text = next(
            (p["text"] for p in profile["pool"] if p["id"] == default_id),
            profile["pool"][0]["text"],
        )
        flat["profile"] = text
    return flat


def _merge_tailored(flat_master: dict, tailored: dict, jd_intent: dict) -> dict:
    """把 tailor 模型输出合并回完整 data 结构，保留事实字段不变。"""
    result = copy.deepcopy(flat_master)

    # basics：只允许改 target_role
    basics = result.get("basics", {})
    if "basics" in tailored:
        new_role = tailored["basics"].get("target_role")
        if new_role:
            basics["target_role"] = new_role
    result["basics"] = basics

    # profile：整段替换
    if tailored.get("profile"):
        result["profile"] = tailored["profile"]

    # projects / internships：保持结构，只替换可改字段
    for key in ("projects", "internships"):
        if key not in tailored:
            continue
        new_items = tailored[key]
        old_items = result.get(key, [])
        merged = []
        for idx, old in enumerate(old_items):
            if idx >= len(new_items):
                merged.append(old)
                continue
            new = new_items[idx]
            merged.append({
                "company": old["company"],  # 硬保留
                "role": new.get("role") or old["role"],
                "date": old["date"],        # 硬保留
                "bullets": new.get("bullets") or old["bullets"],
            })
        result[key] = merged

    # skills：允许改 text 和顺序，label 可微调
    if tailored.get("skills"):
        result["skills"] = tailored["skills"]

    # education：完全不可改
    # （忽略 tailored.education）

    result["_meta"] = {
        "match_score": tailored.get("match_score", 0),
        "change_notes": tailored.get("change_notes", ""),
        "jd_intent": jd_intent,
    }
    return result


# ── 便捷入口：给定 master_id + jd_text 直接出定制简历 ───

def tailor_from_db(master_id: int, jd_text: str) -> dict:
    """从 DB 读主简历，定制后返回 data dict（未写回 DB，由调用方决定）。"""
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).resolve().parents[2] / "data" / "career_os.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM resume_master WHERE id = ?", (master_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise AIError(f"resume_master id={master_id} 不存在")

    master = {
        "basics": json.loads(row["basics_json"]),
        "profile": json.loads(row["profile_json"]),
        "projects": json.loads(row["projects_json"]),
        "internships": json.loads(row["internships_json"]),
        "skills": json.loads(row["skills_json"]),
        "education": json.loads(row["education_json"]),
    }
    return tailor_resume(master, jd_text)
