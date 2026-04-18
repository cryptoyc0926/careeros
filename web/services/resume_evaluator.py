"""深度评估 (T1)

基于 JD + 定制后简历，输出 5 段式评估：
  A 匹配分析（逐条 JD 要求 ✅/⚠️/❌ 挂简历证据）
  B Gap 分析
  C 简历改写建议
  D 预测面试题（5 道）
  E 投递策略

一次 AI 调用产出整个 eval_json，落库 jd_evaluations。
独立按钮触发，不在 tailor_resume 里自动跑。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from config import settings
from services.ai_engine import AIError, _call_claude

DB_PATH = settings.db_full_path


EVAL_SYSTEM = """你是一位顶级的中文校招求职顾问，专长 AI 增长运营岗位评估。
你的任务：给定一份定制后的简历 + 目标 JD，输出结构化评估报告。

## 硬规则
- 只根据简历里真实存在的信息评估，不编造
- 所有"证据"必须引用简历原文片段（20 字以内），不得改写
- 匹配判定要严格：没明确证据就标 ⚠️ 或 ❌，不给免费分

## 输出格式（严格 JSON，禁止任何额外文字）
{
  "overall_score": 0-100 整数,
  "one_line_verdict": "≤40 字的总体结论，建议/不建议投",

  "section_a_match": {
    "title": "匹配分析",
    "requirements": [
      {
        "requirement": "从 JD 抽取的一条具体要求",
        "status": "match|weak|miss",
        "evidence": "简历里的原文证据片段（≤20字），miss 时填空串",
        "note": "≤15 字说明"
      }
    ]
  },

  "section_b_gap": {
    "title": "Gap 分析",
    "critical_gaps": ["硬缺口 1", "硬缺口 2"],
    "soft_gaps": ["弱项 1", "弱项 2"],
    "bridgeable": ["能用相关经验弥补的 gap + 怎么说"]
  },

  "section_c_resume_advice": {
    "title": "简历改写建议",
    "strengthen": ["要突出的 bullet 位置 + 怎么改"],
    "downplay": ["可以弱化的 bullet"],
    "add_keywords": ["应当补进简历的 JD 关键词"]
  },

  "section_d_interview_qa": {
    "title": "预测面试题",
    "questions": [
      {"q": "题目", "why": "为什么会问（≤20字）", "answer_hint": "回答要点（≤40字）"}
    ]
  },

  "section_e_strategy": {
    "title": "投递策略",
    "recommended_channel": "内推 / 邮件直投 / Boss直聘 / 校招门户",
    "best_timing": "建议投递时机",
    "competition_level": "竞争激烈度判断（低/中/高）+ 一句话理由",
    "referral_angle": "如果有内推，应该强调哪个点",
    "risk_warning": "可能的 ghost job / 背景不符 / 门槛过高等风险，没有就填空串"
  }
}

## 注意
- requirements 列 5-10 条（JD 越长越多）
- questions 恰好 5 道
- status=miss 的条目 evidence 填空串 ""
"""


def _jd_hash(jd_text: str) -> str:
    return hashlib.sha1(jd_text.strip().encode("utf-8")).hexdigest()[:16]


def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = "\n".join(t.split("\n")[1:-1])
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        s, e = t.find("{"), t.rfind("}") + 1
        if s >= 0 and e > s:
            return json.loads(t[s:e])
        raise


def deep_evaluate(
    jd_text: str,
    tailored: dict,
    jd_intent: dict | None = None,
) -> dict:
    """调 AI 跑一次深度评估，返回 eval_json（dict）。不落库。"""
    # 把简历精简成纯文本给 AI 看（省 token）
    def flatten_bullets(section: list[dict]) -> list[str]:
        out = []
        for it in section or []:
            header = f"{it.get('company','')} · {it.get('role','')} · {it.get('date','')}"
            out.append(header)
            for b in it.get("bullets", []) or []:
                out.append(f"  • {b}")
        return out

    resume_text = "\n".join([
        f"## 个人总结\n{tailored.get('profile', '')}",
        "## 项目经历",
        *flatten_bullets(tailored.get("projects", [])),
        "## 实习经历",
        *flatten_bullets(tailored.get("internships", [])),
        "## 技能",
        *[f"  - {s.get('label','')}: {s.get('text','')}" for s in tailored.get("skills", [])],
    ])

    user_prompt = f"""## 目标 JD
{jd_text}

## JD 意图分析
{json.dumps(jd_intent or {}, ensure_ascii=False)}

## 定制后的简历内容
{resume_text}

请严格按 system prompt 的 JSON 结构输出评估报告。"""

    raw = _call_claude(
        system_prompt=EVAL_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=4096,
        temperature=0.3,
    )
    return _parse_json(raw)


# ── DB 操作 ──────────────────────────────────────────────
def save_evaluation(
    jd_text: str,
    eval_data: dict,
    *,
    job_pool_id: int | None = None,
    resume_version_id: int | None = None,
    target_role: str = "",
) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """INSERT INTO jd_evaluations
               (job_pool_id, resume_version_id, jd_hash, target_role,
                overall_score, eval_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                job_pool_id,
                resume_version_id,
                _jd_hash(jd_text),
                target_role,
                int(eval_data.get("overall_score") or 0),
                json.dumps(eval_data, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def load_latest_for_jd(jd_text: str) -> dict | None:
    """按 JD hash 查找最近一次评估，避免重复调 AI。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT eval_json FROM jd_evaluations
               WHERE jd_hash = ? ORDER BY created_at DESC LIMIT 1""",
            (_jd_hash(jd_text),),
        ).fetchone()
        return json.loads(row["eval_json"]) if row else None
    finally:
        conn.close()


def list_evaluations(limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT id, target_role, overall_score, created_at
               FROM jd_evaluations ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
