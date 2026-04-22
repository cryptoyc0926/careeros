"""
Resume Chat — 对话式简历改写编排层
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

职责：接收用户自然语言指令 → 分类意图 → 调用底层改写/建议服务 → 产出统一 response。

支持的 intent（Phase 2）:
  - full_rewrite   : 「整体重写 / 根据 JD 重做」→ 走 tailor_resume
  - section_rewrite: 「重写这段 / 把 profile 改偏增长」→ 走 rewrite_section，产出 patch
  - patch_ops      : 字段级精细改（「第 2 个项目的 bullet 3 改偏数据增长」）→ LLM 产 JSON patch
  - advice_only    : 「帮我看下 / 给点建议」→ 纯 markdown 建议
  - clarify        : 触硬事实（删公司名/改日期/改学历）→ 反问

统一 Response::
    {
      "intent": "...",
      "explanation": "≤60 字",
      "pending_patch": [{"op":"replace","path":"...","value":"..."}, ...] | None,
      "new_data": {...} | None,            # full_rewrite 时有
      "advice_md": "..." | None,
      "clarify_question": "..." | None,
      "error": "..." | None,
      "raw": "...",
    }

调用方约定：
  - pending_patch 非空 → UI 渲染 diff 气泡 + 应用/取消 按钮
  - new_data 非空 → UI 直接 push undo + 替换 tailor_data
  - advice_md 非空 → UI 渲染 markdown（不动数据）
  - clarify_question 非空 → UI 渲染反问气泡（不动数据）
"""

from __future__ import annotations

import json
import re
from typing import Any

from .ai_engine import _call_claude, AIError
from .resume_prompt_rules import FULL_STYLE_RULES, BOLD_RULES_BRIEF
from .resume_tailor import tailor_resume, rewrite_section, extract_jd_intent
from .resume_patch import get_by_path


# ═══════════════════════════════════════════════
# 意图分类（本地 + LLM 兜底）
# ═══════════════════════════════════════════════

_FULL_REWRITE_PATTERNS = [
    r"整体重写", r"全量重写", r"重做(一版|简历)?", r"重新(定制|生成)",
    r"对(准|着) ?JD", r"按 ?JD .*(改|重写|定制)", r"根据 ?JD .*(重做|重写|定制|生成)",
]

_ADVICE_PATTERNS = [
    r"看下?(怎么|如何)样", r"给(点|些)?建议", r"点评", r"评估(一下)?",
    r"有什么问题", r"帮我看看", r"^建议$", r"哪里可以改", r"值得改",
]

# 硬事实字段触发 clarify
_HARD_FACT_PATTERNS = [
    r"(删|改|换).*?(公司名?|company)",
    r"(删|改|换).*?(日期|时间|date|\d{4}[\.\-/]\d{1,2})",
    r"(删|改|换).*?(学校|学历|专业|major|school)",
    r"改成.*?(Google|Meta|字节|腾讯|阿里)",  # 编造公司
]

# section_rewrite 关键词（必须指向某段）
_SECTION_HINTS = [
    r"(重写|改写|优化).*(profile|个人总结|简介)",
    r"(重写|改写|优化).*第 ?\d+.*?(项目|实习|bullet)",
    r"把.*?(profile|个人总结).*?改",
]

# patch_ops 关键词（字段级精细改）
_PATCH_HINTS = [
    r"第 ?\d+.*?(项目|实习).*(bullet|条).*?\d",
    r"bullet ?\d+",
    r"(删掉|去掉).*bullet",
    r"(交换|调换).*(顺序|位置)",
    r"把.*?加粗", r"(加|去).*?加粗",
]


def _match_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def classify_intent(user_msg: str) -> str:
    text = (user_msg or "").strip()
    if not text:
        return "advice_only"
    if _match_any(text, _HARD_FACT_PATTERNS):
        return "clarify"
    if _match_any(text, _FULL_REWRITE_PATTERNS):
        return "full_rewrite"
    if _match_any(text, _SECTION_HINTS):
        return "section_rewrite"
    if _match_any(text, _PATCH_HINTS):
        return "patch_ops"
    if _match_any(text, _ADVICE_PATTERNS):
        return "advice_only"
    return "advice_only"


# ═══════════════════════════════════════════════
# 工具：tailor_data 摘要 & JSON 解析
# ═══════════════════════════════════════════════

def _summarize_tailor_data(data: dict[str, Any], max_chars: int = 1800) -> str:
    lines: list[str] = []
    basics = data.get("basics", {})
    lines.append(f"姓名: {basics.get('name', '')} | 目标: {basics.get('target_role', '')}")
    profile = data.get("profile", "")
    if profile:
        lines.append(f"profile: {str(profile)[:240]}")
    for i, p in enumerate(data.get("projects", []) or []):
        lines.append(f"projects[{i}] {p.get('company', '')} · {p.get('role', '')}")
        for j, b in enumerate(p.get("bullets", []) or []):
            lines.append(f"  projects[{i}].bullets[{j}]: {str(b)[:160]}")
    for i, p in enumerate(data.get("internships", []) or []):
        lines.append(f"internships[{i}] {p.get('company', '')} · {p.get('role', '')}")
        for j, b in enumerate(p.get("bullets", []) or []):
            lines.append(f"  internships[{i}].bullets[{j}]: {str(b)[:160]}")
    for i, s in enumerate(data.get("skills", []) or []):
        lines.append(f"skills[{i}] {s.get('label', '')}: {str(s.get('text', ''))[:120]}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(截断)"
    return text


def _parse_json_response(raw: str) -> dict[str, Any]:
    t = (raw or "").strip()
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
    raise AIError(f"JSON 解析失败：{t[:200]}")


# ═══════════════════════════════════════════════
# System prompts
# ═══════════════════════════════════════════════

_ADVICE_SYSTEM = f"""你是一位顶级中文简历顾问。用户会给你当前版本的简历（摘要）和目标 JD，请给出可执行的改写建议。

## 硬原则
- 不改候选人简历，只给建议
- 建议指向具体字段（例："projects[0].bullets[2] 建议改成偏数据增长"）
- 不编造候选人没写过的事实
- 对硬事实（公司名/日期/学历）只建议保留，不建议改

## 风格约束
{BOLD_RULES_BRIEF}

## 输出格式
一段 Markdown（300 字内），结构：
- **整体评估**（1-2 句）
- **具体建议**（3-5 条 bullet，每条指向某字段 + 具体改写方向）
- **可选优先级**（哪条最值得改）

只输出 Markdown，不要 JSON。"""


_PATCH_SYSTEM = f"""你是简历 JSON Patch 生成器。用户给你一个修改诉求，你只输出一段严格 JSON，不要任何解释、markdown 代码块、前后缀。

## 输入
- tailor_data 的摘要（所有字段路径都已列出）
- 目标 JD 关键词
- 用户的修改诉求

## 输出 schema
{{
  "explanation": "≤60字人话说明你要改什么",
  "patch": [
    {{"op": "replace", "path": "projects[0].bullets[2]", "value": "新 bullet 全文"}},
    ...
  ]
}}

## 硬规则（违反即失败）
- path 用 JSONPath 风格：profile / projects[0].bullets[2] / skills[1].text / internships[0].role
- 绝不修改：公司名（projects[*].company / internships[*].company）、日期（*.date）、学校学历
- 绝不新增/删除 bullet，只 replace
- 新文本中原 bullet 里的数字**一个不能丢**（9,000+ / 1,048万 / 20.6% 等原样保留），**只调整加粗范围和措辞**
- 加粗用 HTML `<b>...</b>`，禁用 Markdown `**...**`
- 结果型数字只粗纯数字（`<b>9,000+</b> 粉` 而非 `<b>9,000+ 粉</b>`）
{FULL_STYLE_RULES}

## 风格约束
{BOLD_RULES_BRIEF}

只输出 JSON 对象，不要任何其他文字。"""


_CLARIFY_SYSTEM = """你是一位谨慎的简历顾问。用户提出的修改触碰了简历硬事实字段（公司名、日期、学校、学历），你必须反问确认而不是执行。

## 输出格式
一段自然中文反问（≤80字），举出你担心的点，并让用户明确：是真的想改事实（比如笔误），还是想改措辞/方向。

只输出反问文本，不要 JSON，不要 markdown。"""


# ═══════════════════════════════════════════════
# 各 intent 的处理器
# ═══════════════════════════════════════════════

def _handle_full_rewrite(
    master: dict, jd_text: str
) -> dict[str, Any]:
    if not master:
        return _err("缺少主简历，无法整体重写", "master 未传入")
    if not (jd_text or "").strip():
        return _err("未提供目标 JD，无法整体重写", "jd_text 为空")
    try:
        new_data = tailor_resume(master, jd_text)
        return {
            "intent": "full_rewrite",
            "explanation": "已按目标 JD 整体重写一版（硬事实保留）",
            "pending_patch": None,
            "new_data": new_data,
            "advice_md": None,
            "clarify_question": None,
            "error": None,
            "raw": "",
        }
    except Exception as e:
        try:
            from .resume_validator import ValidationError
        except Exception:
            ValidationError = None  # type: ignore[assignment]

        if ValidationError is not None and isinstance(e, ValidationError):
            report = e.report
            return {
                "intent": "validation_draft",
                "explanation": (
                    f"AI 已返回草稿，但有 {len(report.hard_errors)} 条硬规则问题，"
                    "未自动应用到简历。"
                ),
                "pending_patch": None,
                "new_data": None,
                "draft": e.draft,
                "validation": report.as_dict(),
                "advice_md": None,
                "clarify_question": None,
                "error": None,
                "raw": e.raw or "",
            }
        if isinstance(e, AIError):
            return _err("整体重写失败", str(e))
        return _err("整体重写失败", f"{type(e).__name__}: {e}")


def _handle_advice(
    tailor_data: dict, jd_text: str, user_msg: str
) -> dict[str, Any]:
    summary = _summarize_tailor_data(tailor_data)
    user_prompt = (
        f"【当前简历】\n{summary}\n\n"
        f"【目标 JD】\n{(jd_text or '(未提供)')[:1500]}\n\n"
        f"【用户提问】\n{user_msg}"
    )
    try:
        md = _call_claude(
            system_prompt=_ADVICE_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=1200,
            temperature=0.5,
        )
        return {
            "intent": "advice_only",
            "explanation": "已给出修改建议（未修改简历）",
            "pending_patch": None,
            "new_data": None,
            "advice_md": md.strip(),
            "clarify_question": None,
            "error": None,
            "raw": md,
        }
    except AIError as e:
        return _err("建议生成失败", str(e))


def _handle_patch_ops(
    tailor_data: dict, jd_text: str, user_msg: str
) -> dict[str, Any]:
    summary = _summarize_tailor_data(tailor_data)
    jd_kw = ""
    if (jd_text or "").strip():
        try:
            intent = extract_jd_intent(jd_text)
            jd_kw = ", ".join(intent.get("top_keywords", [])[:6])
        except Exception:
            jd_kw = ""
    user_prompt = (
        f"【当前简历（含字段路径）】\n{summary}\n\n"
        f"【JD 关键词】\n{jd_kw or '(未提供 JD)'}\n\n"
        f"【用户诉求】\n{user_msg}\n\n"
        "输出 JSON patch。"
    )
    try:
        raw = _call_claude(
            system_prompt=_PATCH_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.4,
        )
        obj = _parse_json_response(raw)
        patch = obj.get("patch") or []
        if not isinstance(patch, list) or not patch:
            # 落到建议分支
            return _handle_advice(tailor_data, jd_text, user_msg)
        # 校验 path 都能解析 + 非硬事实
        safe_patch = []
        errors = []
        for p in patch:
            path = str(p.get("path", ""))
            op = p.get("op", "replace")
            if _path_touches_hard_fact(path):
                errors.append(f"拒绝 · 硬事实字段：{path}")
                continue
            try:
                # 只要 parent 能定位即可；不要求 value 已存在
                get_by_path(tailor_data, path) if op == "replace" else None
                safe_patch.append({"op": op, "path": path, "value": p.get("value")})
            except Exception as e:
                errors.append(f"路径无法解析：{path} ({e})")
        if not safe_patch:
            return _err(
                "Patch 全部不合法",
                "；".join(errors) or "LLM 返回空 patch",
            )
        explanation = obj.get("explanation") or f"准备改 {len(safe_patch)} 处"
        if errors:
            explanation = f"{explanation}（忽略 {len(errors)} 条不合法）"
        return {
            "intent": "patch_ops",
            "explanation": explanation,
            "pending_patch": safe_patch,
            "new_data": None,
            "advice_md": None,
            "clarify_question": None,
            "error": None,
            "raw": raw,
        }
    except AIError as e:
        return _err("Patch 生成失败", str(e))


def _handle_section_rewrite(
    tailor_data: dict, jd_text: str, user_msg: str
) -> dict[str, Any]:
    """从 user_msg 提取目标字段 path + 调 rewrite_section，回成 patch_ops 流。"""
    path = _guess_section_path(user_msg, tailor_data)
    if not path:
        # 无法确定字段 → 交给 patch_ops 处理
        return _handle_patch_ops(tailor_data, jd_text, user_msg)
    try:
        original = get_by_path(tailor_data, path)
        if not isinstance(original, str) or not original.strip():
            return _handle_patch_ops(tailor_data, jd_text, user_msg)
        jd_intent = {}
        if (jd_text or "").strip():
            try:
                jd_intent = extract_jd_intent(jd_text)
            except Exception:
                jd_intent = {}
        new_text = rewrite_section(original, jd_intent, hint=user_msg)
        if not new_text or new_text == original:
            return _err("重写未产生变化", "LLM 返回原文或空")
        return {
            "intent": "section_rewrite",
            "explanation": f"已重写 {path}（待你应用）",
            "pending_patch": [{"op": "replace", "path": path, "value": new_text}],
            "new_data": None,
            "advice_md": None,
            "clarify_question": None,
            "error": None,
            "raw": new_text,
        }
    except AIError as e:
        return _err("段落重写失败", str(e))
    except Exception as e:
        return _err("段落重写失败", f"{type(e).__name__}: {e}")


def _handle_clarify(user_msg: str) -> dict[str, Any]:
    try:
        q = _call_claude(
            system_prompt=_CLARIFY_SYSTEM,
            user_prompt=f"用户原话：{user_msg}",
            max_tokens=200,
            temperature=0.3,
        )
        return {
            "intent": "clarify",
            "explanation": "触碰硬事实字段，需确认后再动",
            "pending_patch": None,
            "new_data": None,
            "advice_md": None,
            "clarify_question": q.strip(),
            "error": None,
            "raw": q,
        }
    except AIError as e:
        return _err("反问生成失败", str(e))


# ═══════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════

def _err(explanation: str, error: str) -> dict[str, Any]:
    return {
        "intent": "error",
        "explanation": explanation,
        "pending_patch": None,
        "new_data": None,
        "advice_md": None,
        "clarify_question": None,
        "error": error,
        "raw": "",
    }


def _path_touches_hard_fact(path: str) -> bool:
    """判断 patch path 是否指向不可改的硬事实字段。"""
    p = path.lower()
    if p.endswith(".company") or p.endswith(".date"):
        return True
    if ".school" in p or ".major" in p or p.startswith("education"):
        return True
    return False


_PATH_FROM_USER_RE = [
    # "第 2 个项目的 bullet 3" → projects[1].bullets[2]
    (r"第 ?(\d+) ?个?项目.*?bullet ?(\d+)",
     lambda m: f"projects[{int(m.group(1))-1}].bullets[{int(m.group(2))-1}]"),
    (r"第 ?(\d+) ?个?实习.*?bullet ?(\d+)",
     lambda m: f"internships[{int(m.group(1))-1}].bullets[{int(m.group(2))-1}]"),
    (r"projects\[(\d+)\]\.bullets\[(\d+)\]",
     lambda m: f"projects[{m.group(1)}].bullets[{m.group(2)}]"),
    (r"internships\[(\d+)\]\.bullets\[(\d+)\]",
     lambda m: f"internships[{m.group(1)}].bullets[{m.group(2)}]"),
]


def _guess_section_path(user_msg: str, tailor_data: dict) -> str | None:
    """从自然语言里猜 path；命中 profile 的直接返回；否则返回 None（让 patch_ops 处理）。"""
    text = user_msg or ""
    if re.search(r"(profile|个人总结|简介|自我介绍)", text, re.IGNORECASE):
        return "profile"
    for pat, builder in _PATH_FROM_USER_RE:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return builder(m)
    return None


# ═══════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════

def handle_user_message(
    user_msg: str,
    tailor_data: dict[str, Any],
    master: dict[str, Any] | None = None,
    jd_text: str = "",
    history: list[dict[str, Any]] | None = None,  # 保留扩展位
) -> dict[str, Any]:
    intent = classify_intent(user_msg)

    if intent == "full_rewrite":
        return _handle_full_rewrite(master or {}, jd_text)
    if intent == "clarify":
        return _handle_clarify(user_msg)
    if intent == "section_rewrite":
        return _handle_section_rewrite(tailor_data, jd_text, user_msg)
    if intent == "patch_ops":
        return _handle_patch_ops(tailor_data, jd_text, user_msg)
    # default advice_only
    return _handle_advice(tailor_data, jd_text, user_msg)


# ═══════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    cases = [
        ("帮我整体重写一版", "full_rewrite"),
        ("根据 JD 重做", "full_rewrite"),
        ("帮我看看这版怎么样", "advice_only"),
        ("给点建议", "advice_only"),
        ("把公司名从 MiniMax 改成 Google", "clarify"),
        ("删掉第 2 个项目的日期", "clarify"),
        ("重写 profile 偏增长方向", "section_rewrite"),
        ("把第 2 个项目的 bullet 3 改成数据增长向", "patch_ops"),
        ("bullet 2 加粗数字", "patch_ops"),
    ]
    bad = 0
    for text, expected in cases:
        got = classify_intent(text)
        ok = got == expected
        mark = "✓" if ok else "✗"
        if not ok:
            bad += 1
        print(f"{mark} {text!r:40s} → {got:16s} (expect {expected})")
    print(f"\n{bad} failures")

    # _path_touches_hard_fact
    assert _path_touches_hard_fact("projects[0].company")
    assert _path_touches_hard_fact("internships[1].date")
    assert _path_touches_hard_fact("education[0].school")
    assert not _path_touches_hard_fact("projects[0].bullets[2]")
    assert not _path_touches_hard_fact("profile")
    print("[OK] hard-fact path guard")

    # _guess_section_path
    assert _guess_section_path("重写 profile", {}) == "profile"
    assert _guess_section_path("第 2 个项目的 bullet 3 改一下", {}) == "projects[1].bullets[2]"
    assert _guess_section_path("第1个实习bullet2", {}) == "internships[0].bullets[1]"
    print("[OK] path guess")
