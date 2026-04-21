"""
Resume Chat — 对话式简历改写编排层
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

职责：接收用户自然语言指令 → 分类意图 → 调用底层改写/建议服务 → 产出统一 response。

Phase 1 支持：
  - full_rewrite : 「整体重写 / 根据 JD 重做」→ 走 tailor_resume
  - advice_only  : 「帮我看下这版 / 给点建议」→ 纯 markdown 建议
  （其余 intent patch_ops / section_rewrite / clarify 在 Phase 2 补全）

统一 Response::
    {
      "intent": "full_rewrite" | "advice_only" | "error",
      "explanation": "≤60 字人话",
      "new_data": {...} | None,           # full_rewrite 时有
      "advice_md": "..." | None,          # advice_only 时有
      "error": "..." | None,
      "raw": "...",                       # 原始 LLM 文本（调试用）
    }

使用::
    from services.resume_chat import handle_user_message

    resp = handle_user_message(
        user_msg="帮我整体重写一版，对准 AI 增长运营",
        tailor_data=st.session_state.tailor_data,
        master=master,
        jd_text=st.session_state.tailor_jd,
        history=st.session_state.tailor_chat["messages"][-6:],
    )
"""

from __future__ import annotations

import json
import re
from typing import Any

from .ai_engine import _call_claude, AIError
from .resume_prompt_rules import FULL_STYLE_RULES, BOLD_RULES_BRIEF
from .resume_tailor import tailor_resume


# ═══════════════════════════════════════════════
# 意图分类
# ═══════════════════════════════════════════════

# 关键词级本地分类器（低成本）：命中才走对应分支，否则给 advice_only
_FULL_REWRITE_PATTERNS = [
    r"整体重写", r"全量重写", r"重做(一版|简历)?", r"重新(定制|生成)",
    r"对(准|着) ?JD", r"按 ?JD .*改", r"根据 ?JD",
]
_ADVICE_PATTERNS = [
    r"看下?(怎么|如何)样", r"给(点|些)?建议", r"点评", r"评估", r"有什么问题",
    r"帮我看看", r"建议", r"哪里可以改",
]


def classify_intent(user_msg: str) -> str:
    text = user_msg.strip()
    if not text:
        return "advice_only"
    for pat in _FULL_REWRITE_PATTERNS:
        if re.search(pat, text):
            return "full_rewrite"
    for pat in _ADVICE_PATTERNS:
        if re.search(pat, text):
            return "advice_only"
    # Phase 1 默认落 advice_only（不鲁莽改简历）
    return "advice_only"


# ═══════════════════════════════════════════════
# advice_only: 纯建议 system prompt
# ═══════════════════════════════════════════════

_ADVICE_SYSTEM = f"""你是一位顶级中文简历顾问。用户会给你当前版本的简历（JSON）和目标 JD，请给出可执行的改写建议。

## 硬原则（违反视为失败）
- 不改候选人简历，只给建议
- 建议必须指向具体字段（例："projects[0].bullets[2] 建议改成偏数据增长，强调漏斗和 AB 测试"）
- 不编造候选人没写过的事实
- 对硬事实字段（公司名/日期/学历）只建议保留，不建议改

## 风格约束（继承简历规则）
{BOLD_RULES_BRIEF}

## 输出格式
输出一段 Markdown（300 字内），结构建议：
- **整体评估**（1-2 句）
- **具体建议**（3-5 条 bullet，每条指向某字段 + 具体改写方向）
- **可选优先级**（哪条最值得改）

只输出 Markdown，不要 JSON，不要任何前后缀。"""


def _summarize_tailor_data(data: dict[str, Any], max_chars: int = 1800) -> str:
    """把 tailor_data 压缩成 LLM 易读的简短文本。"""
    lines: list[str] = []
    basics = data.get("basics", {})
    lines.append(f"姓名: {basics.get('name', '')} | 目标: {basics.get('target_role', '')}")
    profile = data.get("profile", "")
    if profile:
        lines.append(f"Profile: {str(profile)[:240]}")
    for i, p in enumerate(data.get("projects", []) or []):
        lines.append(f"projects[{i}] {p.get('company', '')} · {p.get('role', '')}")
        for j, b in enumerate(p.get("bullets", []) or []):
            lines.append(f"  bullets[{j}]: {str(b)[:160]}")
    for i, p in enumerate(data.get("internships", []) or []):
        lines.append(f"internships[{i}] {p.get('company', '')} · {p.get('role', '')}")
        for j, b in enumerate(p.get("bullets", []) or []):
            lines.append(f"  bullets[{j}]: {str(b)[:160]}")
    for i, s in enumerate(data.get("skills", []) or []):
        lines.append(f"skills[{i}] {s.get('label', '')}: {str(s.get('text', ''))[:120]}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(截断)"
    return text


def _advice_call(tailor_data: dict, jd_text: str, user_msg: str) -> str:
    summary = _summarize_tailor_data(tailor_data)
    user_prompt = (
        f"【当前简历摘要】\n{summary}\n\n"
        f"【目标 JD】\n{(jd_text or '(未提供)')[:1500]}\n\n"
        f"【用户提问】\n{user_msg}"
    )
    return _call_claude(
        system_prompt=_ADVICE_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=1200,
        temperature=0.5,
    )


# ═══════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════

def handle_user_message(
    user_msg: str,
    tailor_data: dict[str, Any],
    master: dict[str, Any] | None = None,
    jd_text: str = "",
    history: list[dict[str, Any]] | None = None,  # Phase 1 未使用，保留扩展位
) -> dict[str, Any]:
    """
    Phase 1 的对话入口。分类意图 → 调用对应底层 → 返回统一 response。
    """
    intent = classify_intent(user_msg)

    if intent == "full_rewrite":
        if not master:
            return {
                "intent": "error",
                "explanation": "缺少主简历，无法整体重写",
                "new_data": None,
                "advice_md": None,
                "error": "master 未传入",
                "raw": "",
            }
        if not (jd_text or "").strip():
            return {
                "intent": "error",
                "explanation": "未提供目标 JD，无法整体重写",
                "new_data": None,
                "advice_md": None,
                "error": "jd_text 为空",
                "raw": "",
            }
        try:
            new_data = tailor_resume(master, jd_text)
            return {
                "intent": "full_rewrite",
                "explanation": "已按目标 JD 整体重写一版（公司名/日期/学历已保留）",
                "new_data": new_data,
                "advice_md": None,
                "error": None,
                "raw": "",
            }
        except AIError as e:
            return {
                "intent": "error",
                "explanation": "整体重写失败",
                "new_data": None,
                "advice_md": None,
                "error": str(e),
                "raw": "",
            }

    # advice_only
    try:
        md = _advice_call(tailor_data, jd_text, user_msg)
        return {
            "intent": "advice_only",
            "explanation": "已给出修改建议（未修改简历）",
            "new_data": None,
            "advice_md": md.strip(),
            "error": None,
            "raw": md,
        }
    except AIError as e:
        return {
            "intent": "error",
            "explanation": "建议生成失败",
            "new_data": None,
            "advice_md": None,
            "error": str(e),
            "raw": "",
        }


# ═══════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    # 只测 classify_intent，不联网
    cases = [
        ("帮我整体重写一版", "full_rewrite"),
        ("根据 JD 重新定制", "full_rewrite"),
        ("帮我看看这版怎么样", "advice_only"),
        ("给点建议", "advice_only"),
        ("", "advice_only"),
        ("随便问句", "advice_only"),
    ]
    for text, expected in cases:
        got = classify_intent(text)
        mark = "✓" if got == expected else "✗"
        print(f"{mark} {text!r} → {got} (expect {expected})")
