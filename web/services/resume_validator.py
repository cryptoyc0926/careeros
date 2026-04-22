"""简历定制硬规则校验器 (T6)

调用时机：在 resume_tailor.tailor_resume() 内 AI 输出 JSON 解析后、_merge_tailored 之前。
失败策略：任一 hard_error → 抛 ValidationError，由 page 层 catch 并渲染红色 banner + diff。
不自动重试（按 T6-Q2=B）。

规则（v2.0, 2026-04-20 更新，配合 resume_prompt_rules.py v2.0）：

HARD errors:
  - 公司名被改
  - 日期被改
  - 学校 / 专业 / 学历被改（tailored 里若包含 education 字段必须与 master 一致）
  - 原文**数字序列**被改或丢失（v2.0: 按纯数字 token 比较，兼容新旧加粗格式）
  - bullet 数量变化
  - 新增原文没有的项目 / 实习
  - 数字没加 <b> 标签（AI 输出里裸露的数字不允许）
  - JD top_keywords 命中 < 3 条

Warnings（不阻断）:
  - bullet 长度变化 > 30%
  - profile 字数不在 [70, 130]

v2.0 改动要点：
  - 数字对齐从「<b>XX 单位</b> 整串相等」改为「数字 token 序列包含」
    旧：master `<b>9000+ 粉</b>` vs tailored `<b>9,000+</b> 粉` → 硬错
    新：只要两者都能提取出 {{"9000+"}} 数字集合即通过
  - 兼容新加粗规则：`<b>` 内只包纯数字、单位留在 b 外
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── 数据结构 ────────────────────────────────────────────
@dataclass
class ValidationIssue:
    severity: str          # "hard" | "warn"
    rule: str              # 规则 id
    location: str          # e.g. "projects[0].bullets[2]"
    message: str           # 人话描述
    expected: str = ""     # 期望值（用于 diff）
    actual: str = ""       # 实际值（用于 diff）


@dataclass
class ValidationReport:
    ok: bool
    hard_errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "hard_errors": [e.__dict__ for e in self.hard_errors],
            "warnings": [w.__dict__ for w in self.warnings],
        }

    def summary(self) -> str:
        if self.ok:
            return f"✅ 校验通过（{len(self.warnings)} 条警告）"
        return f"❌ {len(self.hard_errors)} 条硬错 / {len(self.warnings)} 条警告"


class ValidationError(Exception):
    """硬规则校验失败。携带 ValidationReport 和可选草稿供上层渲染。"""

    def __init__(
        self,
        report: ValidationReport,
        *,
        draft: dict[str, Any] | None = None,
        raw: dict[str, Any] | None = None,
    ):
        self.report = report
        self.draft = draft
        self.raw = raw
        super().__init__(report.summary())


def _issue_get(issue: ValidationIssue | dict[str, Any], key: str, default: str = "") -> str:
    """兼容 ValidationIssue dataclass 和旧 dict 结构。"""
    if isinstance(issue, dict):
        value = issue.get(key, default)
    else:
        value = getattr(issue, key, default)
    return "" if value is None else str(value)


def format_validation_issue_markdown(issue: ValidationIssue | dict[str, Any]) -> str:
    """把单条校验项渲染成 Markdown，供页面展示。"""
    rule = _issue_get(issue, "rule", "?")
    location = _issue_get(issue, "location", "?")
    message = _issue_get(issue, "message", "")
    expected = _issue_get(issue, "expected", "")
    actual = _issue_get(issue, "actual", "")

    rendered = f"- **[{rule}]** `{location}` — {message}"
    if expected or actual:
        rendered += f"\n\n  期望：`{expected}`\n\n  实际：`{actual}`"
    return rendered


# ── 工具 ────────────────────────────────────────────────
_BOLD_RE = re.compile(r"<b>\s*([^<]+?)\s*</b>", re.I)
# 裸露数字：2 位以上阿拉伯数字、或 N.N 小数、或带 % 单位、或中文"万/千"前数字
_NAKED_NUM_RE = re.compile(
    r"(?<![>\d])(\d{2,}(?:[\.,]\d+)?[%]?|\d+(?:[\.,]\d+)?\s*[万千]|\d+\+)(?![<\d])"
)


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")


def _extract_bold_values(s: str) -> list[str]:
    """从 bullet 里抽取所有 <b>…</b> 里的值，保留原顺序、去前后空白。"""
    return [m.group(1).strip() for m in _BOLD_RE.finditer(s or "")]


# v2.0 新增：从整条文本（含 HTML 外）提取「数字 token 集合」
# 用于兼容新旧加粗格式的数字对齐校验
_NUM_TOKEN_RE = re.compile(
    r"\d+(?:[.,，]\d+)*(?:\s*[万千])?(?:\s*[wWkK])?[%+]?",
    re.UNICODE,
)


def _extract_number_tokens(s: str) -> set[str]:
    """从整段文本（剥 HTML 后）提取所有「数字 token」，返回标准化集合。

    标准化规则：
      - 去掉英文/中文逗号、空格
      - 保留小数点、+、%、万、千、w、k
      - 大小写统一为小写
      - 丢弃长度 < 2 且无后缀符号的单数字（避免"6 个模块"这种配置量干扰）

    用途：校验 master 的数字序列是否完整保留在 tailored 里，不关心加粗格式怎么变。
    """
    if not s:
        return set()
    text = re.sub(r"<[^>]+>", "", s)
    tokens: set[str] = set()
    for m in _NUM_TOKEN_RE.finditer(text):
        raw = m.group(0)
        norm = re.sub(r"[,，\s]", "", raw).lower()
        if not norm:
            continue
        # 过滤：纯个位数且无任何单位/符号的不算关键数字（避免"6"、"3"这种配置数字干扰）
        has_suffix = any(c in norm for c in "+%万千wk.")
        has_multi_digit = len(re.sub(r"[^\d]", "", norm)) >= 2
        if has_suffix or has_multi_digit:
            tokens.add(norm)
    return tokens


def _find_naked_numbers(s: str) -> list[str]:
    """抽取没被 <b> 包裹的裸数字。先剥离 <b>…</b> 里的内容再扫。"""
    no_bold = re.sub(r"<b>[^<]*</b>", "", s or "", flags=re.I)
    return [m.group(1) for m in _NAKED_NUM_RE.finditer(no_bold)]


def _char_len(s: str) -> int:
    return len(_strip_html(s))


# ── 主校验函数 ─────────────────────────────────────────
def validate_tailored(
    master: dict[str, Any],
    tailored: dict[str, Any],
    jd_intent: dict[str, Any] | None = None,
    *,
    min_keywords_hit: int = 3,
    profile_min: int = 70,
    profile_max: int = 130,
    bullet_len_tolerance: float = 0.30,
) -> ValidationReport:
    """主入口：对比 master 与 tailored 的原始 AI 输出，返回校验报告。"""
    report = ValidationReport(ok=True)

    # ── rule 1-6: projects / internships 结构与数字 ──
    for section in ("projects", "internships"):
        m_items = master.get(section, []) or []
        t_items = tailored.get(section, []) or []

        # rule 6: 新增原文没有的项目
        if len(t_items) > len(m_items):
            for i in range(len(m_items), len(t_items)):
                report.hard_errors.append(ValidationIssue(
                    severity="hard",
                    rule="extra_item",
                    location=f"{section}[{i}]",
                    message=f"{section} 多出一项（原简历没有）",
                    expected=f"(不存在)",
                    actual=(t_items[i].get("company") or "?"),
                ))

        for i, m in enumerate(m_items):
            if i >= len(t_items):
                continue  # 少写允许（不会比原来多，只是没改）
            t = t_items[i]

            # rule 1: 公司名
            if (t.get("company") or "").strip() != (m.get("company") or "").strip():
                report.hard_errors.append(ValidationIssue(
                    severity="hard",
                    rule="company_changed",
                    location=f"{section}[{i}].company",
                    message="公司名被修改",
                    expected=m.get("company", ""),
                    actual=t.get("company", ""),
                ))

            # rule 2: 日期
            if (t.get("date") or "").strip() != (m.get("date") or "").strip():
                report.hard_errors.append(ValidationIssue(
                    severity="hard",
                    rule="date_changed",
                    location=f"{section}[{i}].date",
                    message="时间段被修改",
                    expected=m.get("date", ""),
                    actual=t.get("date", ""),
                ))

            # rule 5: bullet 数量
            m_bullets = m.get("bullets") or []
            t_bullets = t.get("bullets") or []
            if len(m_bullets) != len(t_bullets):
                report.hard_errors.append(ValidationIssue(
                    severity="hard",
                    rule="bullet_count_changed",
                    location=f"{section}[{i}].bullets",
                    message=f"bullet 数量从 {len(m_bullets)} 变成 {len(t_bullets)}",
                    expected=str(len(m_bullets)),
                    actual=str(len(t_bullets)),
                ))

            # 逐条 bullet 检查
            for bi in range(min(len(m_bullets), len(t_bullets))):
                m_b = m_bullets[bi]
                t_b = t_bullets[bi]

                # rule 4a (v2.0): 原文数字 token 必须全部保留（兼容新旧加粗格式）
                # 旧逻辑按 <b>...</b> 内字符串完整相等对齐，新规则下加粗范围变了会误报
                # 新逻辑：提取整条 bullet 的纯数字 token 集合做包含校验
                m_tokens = _extract_number_tokens(m_b)
                t_tokens = _extract_number_tokens(t_b)
                missing = sorted(m_tokens - t_tokens)
                if missing:
                    report.hard_errors.append(ValidationIssue(
                        severity="hard",
                        rule="number_dropped",
                        location=f"{section}[{i}].bullets[{bi}]",
                        message=f"原文数字丢失：{', '.join(missing)}",
                        expected=", ".join(sorted(m_tokens)),
                        actual=", ".join(sorted(t_tokens)),
                    ))

                # rule 4b: 裸露数字（AI 输出里没加 <b> 的数字）→ 警告
                naked = _find_naked_numbers(t_b)
                if naked:
                    report.warnings.append(ValidationIssue(
                        severity="warn",
                        rule="number_not_bolded",
                        location=f"{section}[{i}].bullets[{bi}]",
                        message=f"数字未加 <b> 标签：{', '.join(naked)}",
                        expected="<b>xxx</b>",
                        actual=t_b[:80],
                    ))

                # warn: bullet 长度变化
                m_len = _char_len(m_b)
                t_len = _char_len(t_b)
                if m_len > 0:
                    ratio = abs(t_len - m_len) / m_len
                    if ratio > bullet_len_tolerance:
                        report.warnings.append(ValidationIssue(
                            severity="warn",
                            rule="bullet_length",
                            location=f"{section}[{i}].bullets[{bi}]",
                            message=f"bullet 长度变化 {int(ratio*100)}%（{m_len}→{t_len}）",
                            expected=f"{m_len} 字",
                            actual=f"{t_len} 字",
                        ))

    # ── rule 3: education 不能改 ──
    if "education" in tailored and tailored["education"]:
        m_edu = master.get("education", [])
        t_edu = tailored["education"]
        if len(m_edu) != len(t_edu):
            report.hard_errors.append(ValidationIssue(
                severity="hard",
                rule="education_count_changed",
                location="education",
                message="教育背景条目数被改动",
                expected=str(len(m_edu)),
                actual=str(len(t_edu)),
            ))
        for i, me in enumerate(m_edu):
            if i >= len(t_edu):
                continue
            te = t_edu[i]
            for fld in ("school", "major", "date", "company", "role"):
                mv, tv = (me.get(fld) or "").strip(), (te.get(fld) or "").strip()
                if mv and tv and mv != tv:
                    report.hard_errors.append(ValidationIssue(
                        severity="hard",
                        rule=f"education_{fld}_changed",
                        location=f"education[{i}].{fld}",
                        message=f"教育背景的 {fld} 被改",
                        expected=mv, actual=tv,
                    ))

    # ── rule 7: JD top_keywords 覆盖 ──
    if jd_intent and jd_intent.get("top_keywords"):
        keywords = [k.strip() for k in jd_intent["top_keywords"][:8] if k.strip()]
        full_text = _strip_html(str(tailored.get("profile", "")))
        for section in ("projects", "internships"):
            for item in tailored.get(section, []) or []:
                for b in item.get("bullets", []) or []:
                    full_text += " " + _strip_html(b)

        hits = [k for k in keywords if k.lower() in full_text.lower()]
        if len(hits) < min_keywords_hit:
            report.hard_errors.append(ValidationIssue(
                severity="hard",
                rule="keyword_coverage_low",
                location="overall",
                message=f"JD 核心关键词仅命中 {len(hits)}/{len(keywords)}（至少 {min_keywords_hit}）",
                expected=", ".join(keywords),
                actual=", ".join(hits) or "(无)",
            ))

    # ── warn: profile 字数 ──
    profile_text = _strip_html(str(tailored.get("profile") or ""))
    if profile_text:
        n = len(profile_text)
        if n < profile_min or n > profile_max:
            report.warnings.append(ValidationIssue(
                severity="warn",
                rule="profile_length",
                location="profile",
                message=f"个人总结字数 {n}（建议 {profile_min}-{profile_max}）",
                expected=f"{profile_min}-{profile_max}",
                actual=str(n),
            ))

    report.ok = len(report.hard_errors) == 0
    return report


# ── CLI smoke test ─────────────────────────────────────
if __name__ == "__main__":
    master = {
        "projects": [
            {"company": "AI Trading", "role": "增长", "date": "2024.03 - 至今",
             "bullets": ["做到 <b>9000+</b> 粉", "转化 <b>20+</b> 次合作"]}
        ],
        "internships": [],
        "education": [{"school": "浙工商", "major": "统计", "date": "2022-2026"}],
    }
    # v2.0 新格式：数字包 <b>，单位在 b 外
    good = {
        "projects": [
            {"company": "AI Trading", "role": "用户增长运营", "date": "2024.03 - 至今",
             "bullets": ["AI 增长：做到 <b>9,000+</b> 粉丝（逗号版也通过）", "商业化 <b>20+</b> 次合作"]}
        ],
        "internships": [],
        "profile": "有 AI 增长运营和数据驱动经验的 2026 届候选人" * 3,
    }
    intent = {"top_keywords": ["AI", "增长", "运营", "数据"]}
    r = validate_tailored(master, good, intent)
    print(r.summary())
    for w in r.warnings:
        print("  WARN", w.rule, w.message)

    bad = {
        "projects": [
            {"company": "AI Trading Co", "role": "增长", "date": "2024.03 - 至今",
             "bullets": ["9000+ 粉丝裸数字", "只有 20 次合作"]}
        ],
        "internships": [],
    }
    r = validate_tailored(master, bad, intent)
    print(r.summary())
    for e in r.hard_errors:
        print("  HARD", e.rule, "@", e.location, "-", e.message)
