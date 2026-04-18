"""
规则解析主简历（纯正则/关键词，不走 AI）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
输入：纯文本（由 extract_resume_text 从 PDF/DOCX/TXT 提出）
输出：符合 resume_master schema 的 dict（basics / profile / projects / internships / skills / education）

策略：
1. basics 用正则抓（电话/邮箱/姓名）
2. 识别中文简历常见章节锚点（"项目经验" / "实习经历" / "教育背景" 等）
3. 章节内部：把每段非空行分组为"条目"（item），再按 bullet / 子行识别 company / role / date / bullets

不保证 100% 精准 — 实际做到 70-80% 字段命中率，剩余靠用户手工校对即可。
"""
from __future__ import annotations

import re
from typing import Any


# ═════════════════════════════════════════════════════════════════
# 字段提取正则
# ═════════════════════════════════════════════════════════════════

# 手机号：中国 / 国际常见
_PHONE_RE = re.compile(
    r"(?:(?:\+?86[-\s]?)?1[3-9]\d{9}"   # 中国大陆 11 位
    r"|1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}"  # 186-8795-0926 / 186 8795 0926
    r"|\(?\+?\d{1,4}\)?[-\s]?\d{2,4}[-\s]?\d{4}[-\s]?\d{4})"  # 国际
)

# 邮箱
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# 日期范围：2024.03 - 2024.09 / 2024-03 ~ 2024-09 / 2024.03 至今
_DATE_RANGE_RE = re.compile(
    r"(\d{4}[.\-/年]\s*\d{1,2}(?:[.\-/月]\s*\d{0,2})?)"
    r"\s*[-~至到—–]+\s*"
    r"(\d{4}[.\-/年]\s*\d{1,2}(?:[.\-/月]\s*\d{0,2})?|至今|今|现在|present|now)"
)

# 单个日期（某处只有一个日期）
_SINGLE_DATE_RE = re.compile(r"\d{4}[.\-/年]\s*\d{1,2}")

# 姓名：中文 2-4 字（排除含"简历"等）
_NAME_CN_RE = re.compile(r"^[\u4e00-\u9fa5]{2,4}(?:\s+[\u4e00-\u9fa5]{2,4})?$")

# 章节标题关键词（按优先级）
SECTIONS = {
    "basics":      ["个人信息", "基本信息"],
    "profile":     ["个人简介", "自我评价", "个人总结", "自我介绍", "个人评价", "自评", "summary", "about me"],
    "education":   ["教育背景", "教育经历", "学习经历", "教育", "education"],
    "projects":    ["项目经验", "项目经历", "项目", "主要项目", "projects", "project experience"],
    "internships": ["实习经历", "实习经验", "工作经历", "工作经验", "实习", "工作", "internship", "work experience", "experience"],
    "skills":      ["专业技能", "技能证书", "技能", "核心技能", "技术栈", "工具", "skills", "technical skills"],
}

# 每行最多字符数 — 超过视为段落而非标题
_MAX_HEADING_LEN = 20


# ═════════════════════════════════════════════════════════════════
# 核心解析
# ═════════════════════════════════════════════════════════════════

def parse_resume_text(text: str) -> dict:
    """把简历文本解析为 resume_master schema。"""
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")

    basics = _extract_basics(text)
    sections = _split_sections(text)

    profile_text = _join_section(sections.get("profile", []))

    return {
        "basics": basics,
        "profile": profile_text,
        "projects":    _parse_items(sections.get("projects", [])),
        "internships": _parse_items(sections.get("internships", [])),
        "skills":      _parse_skills(sections.get("skills", [])),
        "education":   _parse_education(sections.get("education", [])),
    }


# ─── basics ──────────────────────────────────────────────────────

def _extract_basics(text: str) -> dict:
    phone = _first(_PHONE_RE.findall(text))
    email = _first(_EMAIL_RE.findall(text))

    # 姓名：取文档前 10 行里，第一行长度 2-4 的纯中文（不含数字/邮箱/电话/章节关键词）
    name = ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()][:15]
    exclude_kw = set(sum(SECTIONS.values(), []))  # 章节关键词
    for ln in lines:
        if _EMAIL_RE.search(ln) or _PHONE_RE.search(ln):
            continue
        # 去空格后检查是否像姓名
        compact = ln.replace(" ", "")
        if _NAME_CN_RE.match(compact) and compact not in exclude_kw and "简历" not in compact and "cv" not in compact.lower():
            name = compact
            break

    # 城市：找"现居 XX" / "杭州/上海" 这种；也可以后续看"期望城市"
    city = ""
    city_match = re.search(r"(?:现居|现在住|地址|所在地|city)[：:：\s]*([^\s,，、|/]{2,10})", text, re.IGNORECASE)
    if city_match:
        city = city_match.group(1).strip()
    else:
        # 简单城市关键词扫
        for c in ["杭州", "上海", "北京", "深圳", "广州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津", "青岛", "大连", "厦门"]:
            if c in text:
                city = c
                break

    # 目标职位：找"求职意向" / "目标岗位" / "期望职位"
    target_role = ""
    role_match = re.search(r"(?:求职意向|目标岗位|期望职位|应聘岗位|意向岗位|target)[：:：\s]*([^\n,，、|/]{2,30})", text, re.IGNORECASE)
    if role_match:
        target_role = role_match.group(1).strip()

    return {
        "name": name,
        "phone": phone or "",
        "email": email or "",
        "target_role": target_role,
        "city": city,
        "availability": "",
        "photo": "",
    }


# ─── 章节切分 ────────────────────────────────────────────────────

def _split_sections(text: str) -> dict[str, list[str]]:
    """把全文按章节锚点切成 dict[section_key] = [段落行...]"""
    lines = text.split("\n")
    # 每行判断是否是章节头：短行 + 匹配关键词 + 独占一行
    section_ranges: list[tuple[int, str]] = []  # (line_idx, section_key)
    for i, ln in enumerate(lines):
        cleaned = ln.strip()
        if not cleaned or len(cleaned) > _MAX_HEADING_LEN:
            continue
        # 去掉装饰字符
        clean_for_match = re.sub(r"[■▎●◆▲\-━—:：|│]+", "", cleaned).strip().lower()
        for key, kws in SECTIONS.items():
            for kw in kws:
                if clean_for_match == kw.lower() or clean_for_match.startswith(kw.lower()):
                    section_ranges.append((i, key))
                    break
            else:
                continue
            break

    # 没找到任何章节：全文丢进 profile
    if not section_ranges:
        return {"profile": [ln for ln in lines if ln.strip()]}

    # 按行号切片
    section_ranges.sort()
    result: dict[str, list[str]] = {}
    for idx, (start, key) in enumerate(section_ranges):
        end = section_ranges[idx + 1][0] if idx + 1 < len(section_ranges) else len(lines)
        content = [ln for ln in lines[start + 1:end] if ln.strip()]
        # 同 key 多段合并
        result.setdefault(key, []).extend(content)

    return result


def _join_section(lines: list[str]) -> str:
    if not lines:
        return ""
    return " ".join(ln.strip() for ln in lines).strip()


# ─── projects / internships ─────────────────────────────────────

def _parse_items(lines: list[str]) -> list[dict]:
    """把章节行切成多个 item。

    规则：
    - 含日期范围的行 = 新 item 的 header
    - 紧随其后的 bullet 行（以 -/•/·/> 或数字. 开头的 / 或不是 header 的）合并为 bullets
    """
    if not lines:
        return []

    items: list[dict] = []
    current: dict | None = None

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue

        # 判断是否是 header
        date_match = _DATE_RANGE_RE.search(ln)
        is_header = bool(date_match)

        if is_header:
            # 新起 item
            if current is not None:
                items.append(current)
            date_str = date_match.group(0).strip()
            header_text = _DATE_RANGE_RE.sub("", ln).strip(" |,，、:：-·").strip()
            company, role = _split_company_role(header_text)
            current = {
                "company": company,
                "role": role,
                "date": _normalize_date(date_str),
                "bullets": [],
            }
        else:
            # 归为 bullet
            bullet = re.sub(r"^[\-•·▪◦○●※>＞\d+\.、)）\s]+", "", ln).strip()
            if not bullet:
                continue
            if current is None:
                # 孤立 bullet（前面没遇到 header）→ 新建一个 item
                current = {"company": "", "role": "", "date": "", "bullets": []}
            current["bullets"].append(bullet)

    if current is not None:
        items.append(current)

    return items


def _split_company_role(text: str) -> tuple[str, str]:
    """把 "公司 + 角色" 这样的 header 文本拆开。
    常见模式：
        MiniMax | AI 增长运营实习生
        Fancy Tech — 海外产品运营实习生
        杭银消费金融股份有限公司 产品运营实习生
    """
    if not text:
        return "", ""
    # 先试分隔符
    for sep in ["|", "｜", "·", "•", "—", "–", " - ", " | ", "/"]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1) if p.strip()]
            if len(parts) == 2:
                return parts[0], parts[1]
    # 尝试用空格切 2 段
    parts = text.split(None, 1)
    if len(parts) == 2 and len(parts[0]) <= 20:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def _normalize_date(date_str: str) -> str:
    """统一日期格式。简单清洗空格。"""
    if not date_str:
        return ""
    s = re.sub(r"\s+", " ", date_str.strip())
    s = s.replace("—", "-").replace("–", "-").replace("~", "-")
    return s


# ─── skills ──────────────────────────────────────────────────────

def _parse_skills(lines: list[str]) -> list[dict]:
    """技能章节：每行可能是 "分类: 具体技能" 或 "分类｜具体"，也可能纯列表。"""
    if not lines:
        return []

    skills = []
    for raw in lines:
        ln = re.sub(r"^[\-•·▪◦○●※>＞\d+\.、)）\s]+", "", raw.strip()).strip()
        if not ln:
            continue
        # 分类: 内容
        m = re.match(r"^([^:：|｜]{1,12})[:：|｜]\s*(.+)$", ln)
        if m:
            label = m.group(1).strip()
            text = m.group(2).strip()
            skills.append({"label": label, "text": text})
        else:
            skills.append({"label": "", "text": ln})

    return skills


# ─── education ───────────────────────────────────────────────────

def _parse_education(lines: list[str]) -> list[dict]:
    """教育经历：日期 + 学校 + 专业 + 荣誉/课程。"""
    if not lines:
        return []

    # 复用 projects 的逻辑 — 用日期切 item
    raw_items = _parse_items(lines)
    # 转成 education schema：把 header 再细拆成 school/major
    out = []
    for it in raw_items:
        school = it["company"]
        major = it["role"]
        # 如果 role 为空但 company 里有多段（例如 "浙江工商大学 应用统计专业"）
        if not major and school:
            parts = school.split(None, 1)
            if len(parts) == 2:
                school, major = parts[0], parts[1]
        out.append({
            "school": school,
            "major": major,
            "date": it["date"],
            "bullets": it["bullets"],
        })

    # 如果什么 item 都没识别出来（因为教育通常 1 段没日期）
    if not out and lines:
        # 把前几行当成 school / major / bullets
        non_empty = [ln.strip() for ln in lines if ln.strip()]
        if non_empty:
            out.append({
                "school": non_empty[0],
                "major": non_empty[1] if len(non_empty) > 1 else "",
                "date": "",
                "bullets": non_empty[2:] if len(non_empty) > 2 else [],
            })
    return out


# ─── helpers ────────────────────────────────────────────────────

def _first(items: list[str]) -> str:
    return items[0] if items else ""
