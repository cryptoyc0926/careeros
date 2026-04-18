"""
规则解析主简历（纯正则/关键词，不走 AI）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
输入：纯文本（由 extract_resume_text 从 PDF/DOCX/TXT 提出）
输出：匹配 resume_master schema 的 dict

v2 改进：
- 项目/实习 header 用**后缀职位关键词**反向匹配识别 company/role 边界
- bullets 合并：只把 •●※▪ 等开头的行作为新 bullet，其他行续接到上一 bullet
- education 专门处理 | 分隔的 "学校 | 专业 | 日期 | 荣誉" 格式
- 章节识别：容忍装饰符、粘连空白、不同关键词变体
"""
from __future__ import annotations

import re
from typing import Any


# ═════════════════════════════════════════════════════════════════
# 字段提取正则
# ═════════════════════════════════════════════════════════════════

_PHONE_RE = re.compile(
    r"(?:(?:\+?86[-\s]?)?1[3-9]\d{9}"
    r"|1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}"
    r"|\(?\+?\d{1,4}\)?[-\s]?\d{2,4}[-\s]?\d{4}[-\s]?\d{4})"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_DATE_RANGE_RE = re.compile(
    r"(\d{4}[.\-/年]\s*\d{1,2}(?:[.\-/月]\s*\d{0,2})?)"
    r"\s*[-~至到—–]+\s*"
    r"(\d{4}[.\-/年]\s*\d{1,2}(?:[.\-/月]\s*\d{0,2})?|至今|今|现在|present|now)"
)
_NAME_CN_RE = re.compile(r"^[\u4e00-\u9fa5]{2,4}$")

# Bullet 开头的装饰符：• ● ※ ▪ ▫ ◦ ○ ◆ ◇ ■ □ · ・ ⭐ ► ▶ ◆
_BULLET_START_RE = re.compile(r"^[•●※▪▫◦○◆◇■□·・⭐►▶\-–—]+\s*")

# 带数字前缀的 bullet：1. 2) ①
_NUM_BULLET_RE = re.compile(r"^[\d①②③④⑤⑥⑦⑧⑨⑩]+[.\)）、]\s*")

# 职位关键词（尽可能覆盖中英文常见岗位名末尾词）
_ROLE_KEYWORDS = [
    # 中文完整职位
    "用户增长运营", "增长运营", "内容运营", "社区运营", "海外运营", "社媒运营",
    "产品运营", "活动运营", "数据运营", "营销运营", "品牌运营",
    "运营实习生", "产品实习生", "设计实习生", "技术实习生", "开发实习生",
    "产品经理", "产品助理", "产品设计", "交互设计", "UI 设计师", "UX 设计师",
    "算法工程师", "前端工程师", "后端工程师", "测试工程师", "全栈工程师",
    "数据分析师", "数据科学家", "机器学习工程师", "AI 工程师",
    "市场经理", "市场专员", "品牌经理",
    "项目经理", "项目助理", "项目管理",
    "咨询顾问", "战略顾问", "业务分析师",
    "管培生", "实习生", "合伙人",
    # 通用后缀（单字/短词）
    "运营", "产品", "设计", "开发", "工程师", "经理", "分析师", "设计师", "总监", "架构师",
    "顾问", "助理", "主管", "策划", "市场", "品牌", "管理", "销售", "编辑", "采购",
    # 英文
    "Intern", "Manager", "Engineer", "Designer", "Analyst", "Lead", "Director",
    "Consultant", "Specialist", "Developer", "Researcher", "Scientist",
]
# 反向按长度排序（长的先匹配，避免"运营"抢在"增长运营"前）
_ROLE_KEYWORDS.sort(key=len, reverse=True)
_ROLE_PATTERN = re.compile(
    r"(?P<role>[\w\s\u4e00-\u9fa5]*?(?:" + "|".join(re.escape(k) for k in _ROLE_KEYWORDS) + r")[\w\s\u4e00-\u9fa5\(\)（）]*)\s*$"
)

# 章节标题关键词
SECTIONS = {
    "basics":      ["个人信息", "基本信息", "联系方式"],
    "profile":     ["个人总结", "个人简介", "自我评价", "自我介绍", "个人评价", "自评", "Summary", "About Me"],
    "education":   ["教育背景", "教育经历", "学习经历", "教育", "Education"],
    "projects":    ["项目经历", "项目经验", "项目", "主要项目", "核心项目", "Projects", "Project Experience"],
    "internships": ["实习经历", "实习经验", "工作经历", "工作经验", "实习", "工作", "Internship", "Work Experience", "Experience"],
    "skills":      ["核心技能", "专业技能", "技能证书", "技能", "技术栈", "工具", "Skills", "Technical Skills"],
}

_MAX_HEADING_LEN = 20


# ═════════════════════════════════════════════════════════════════
# 顶层
# ═════════════════════════════════════════════════════════════════

def parse_resume_text(text: str) -> dict:
    """把简历文本解析为 resume_master schema。"""
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")

    basics = _extract_basics(text)
    sections = _split_sections(text)

    return {
        "basics":      basics,
        "profile":     _join_section(sections.get("profile", [])),
        "projects":    _parse_items(sections.get("projects", [])),
        "internships": _parse_items(sections.get("internships", [])),
        "skills":      _parse_skills(sections.get("skills", [])),
        "education":   _parse_education(sections.get("education", [])),
    }


# ═════════════════════════════════════════════════════════════════
# basics
# ═════════════════════════════════════════════════════════════════

def _extract_basics(text: str) -> dict:
    phone = _first(_PHONE_RE.findall(text))
    email = _first(_EMAIL_RE.findall(text))

    # 姓名：文档前 15 行中，第一个符合 2-4 字纯中文（去掉空格后）的非章节行
    name = ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()][:15]
    exclude_kw = set(sum(SECTIONS.values(), []))
    for ln in lines:
        if _EMAIL_RE.search(ln) or _PHONE_RE.search(ln):
            continue
        compact = ln.replace(" ", "")
        if _NAME_CN_RE.match(compact) and compact not in exclude_kw and "简历" not in compact and "cv" not in compact.lower():
            name = compact
            break

    # 先拆开第三行那种 "求职意向：X | 期望城市：Y | 到岗时间：Z" 横线分隔
    target_role = _find_field(text, r"(?:求职意向|目标岗位|期望职位|应聘岗位|意向岗位|target)")
    city = _find_field(text, r"(?:期望城市|现居|现在住|地址|所在地|目标城市|city)")
    availability = _find_field(text, r"(?:到岗时间|入职时间|可入职|availability)")

    # city fallback：扫主要城市关键词
    if not city:
        for c in ["杭州", "上海", "北京", "深圳", "广州", "成都", "南京", "苏州", "武汉", "西安", "重庆", "天津", "青岛", "大连", "厦门", "长沙", "合肥"]:
            if c in text:
                city = c
                break

    return {
        "name": name,
        "phone": phone or "",
        "email": email or "",
        "target_role": target_role,
        "city": city,
        "availability": availability,
        "photo": "",
    }


def _find_field(text: str, label_pattern: str) -> str:
    """找 "标签: 值" 格式的字段值。终止符：换行、 |、全角 ｜、。、；"""
    m = re.search(
        label_pattern + r"[：:：\s]*([^\n|｜。；;]{1,40}?)(?=\s*(?:[|｜]|$|\n|。|；))",
        text,
        re.IGNORECASE,
    )
    if not m:
        return ""
    val = m.group(1).strip(" ·,，、:：-")
    return val


# ═════════════════════════════════════════════════════════════════
# 章节切分
# ═════════════════════════════════════════════════════════════════

def _split_sections(text: str) -> dict[str, list[str]]:
    """按章节锚点切分。"""
    lines = text.split("\n")
    section_ranges: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        cleaned = ln.strip()
        if not cleaned or len(cleaned) > _MAX_HEADING_LEN:
            continue
        # 去掉装饰字符
        clean_for_match = re.sub(r"[■▎●◆▲\-━—:：|│◆▪#]+", "", cleaned).strip().lower()
        if not clean_for_match:
            continue
        for key, kws in SECTIONS.items():
            for kw in kws:
                if clean_for_match == kw.lower() or (
                    clean_for_match.startswith(kw.lower()) and len(clean_for_match) <= len(kw) + 3
                ):
                    section_ranges.append((i, key))
                    break
            else:
                continue
            break

    if not section_ranges:
        return {"profile": [ln for ln in lines if ln.strip()]}

    section_ranges.sort()
    result: dict[str, list[str]] = {}
    for idx, (start, key) in enumerate(section_ranges):
        end = section_ranges[idx + 1][0] if idx + 1 < len(section_ranges) else len(lines)
        content = [ln for ln in lines[start + 1:end] if ln.strip()]
        result.setdefault(key, []).extend(content)

    return result


def _join_section(lines: list[str]) -> str:
    if not lines:
        return ""
    # 合并连续行（PDF 排版会把一段文本拆成多行）
    merged: list[str] = []
    buf = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if _is_bullet_start(ln) or _NUM_BULLET_RE.match(ln):
            if buf:
                merged.append(buf)
            buf = _strip_bullet(ln)
        else:
            buf = _concat_cn_en(buf, ln)
    if buf:
        merged.append(buf)
    return "\n".join(merged).strip() if merged else " ".join(lines).strip()


# ═════════════════════════════════════════════════════════════════
# projects / internships
# ═════════════════════════════════════════════════════════════════

def _parse_items(lines: list[str]) -> list[dict]:
    """把章节行切成 item 列表。

    规则：
    - 含日期范围的行 → 新 item 的 header
    - bullet 符号开头的行 → 新 bullet
    - 其他行 → 续接到上一个 bullet（PDF 换行合并）
    """
    if not lines:
        return []

    items: list[dict] = []
    current: dict | None = None
    last_bullet_idx: int | None = None  # 当前 item 最后一个 bullet 的索引

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue

        # --- header 检测 ---
        date_match = _DATE_RANGE_RE.search(ln)
        if date_match:
            if current is not None:
                items.append(current)
            date_str = date_match.group(0).strip()
            header_text = _DATE_RANGE_RE.sub("", ln).strip(" |,，、:：-·—–").strip()
            company, role = _split_company_role(header_text)
            current = {
                "company": company,
                "role": role,
                "date": _normalize_date(date_str),
                "bullets": [],
            }
            last_bullet_idx = None
            continue

        # --- bullet 开头 ---
        if _is_bullet_start(ln) or _NUM_BULLET_RE.match(ln):
            bullet = _strip_bullet(ln)
            if not bullet:
                continue
            if current is None:
                current = {"company": "", "role": "", "date": "", "bullets": []}
            current["bullets"].append(bullet)
            last_bullet_idx = len(current["bullets"]) - 1
            continue

        # --- 续行：合并到上一个 bullet 末尾 ---
        if current is None:
            current = {"company": "", "role": "", "date": "", "bullets": []}

        if last_bullet_idx is None:
            # 没有 bullet 但有 header 后的第一行描述 — 作为 bullet 开新
            current["bullets"].append(ln)
            last_bullet_idx = len(current["bullets"]) - 1
        else:
            prev = current["bullets"][last_bullet_idx]
            current["bullets"][last_bullet_idx] = _concat_cn_en(prev, ln)

    if current is not None:
        items.append(current)

    return items


def _split_company_role(text: str) -> tuple[str, str]:
    """拆 header 文本 → (company, role)。

    策略（按优先级）：
    1. 显式分隔符 | ｜ · • — – /
    2. 职位关键词定位：找到**最左、最长**的关键词位置，从该位置往前找最后一个空格作为 company/role 分隔
    3. 都失败：整段当 company
    """
    if not text:
        return "", ""

    # 1. 显式分隔符（长的先试）
    for sep in ["|", "｜", " - ", " — ", " – ", " / "]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1) if p.strip()]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]

    for sep in ["·", "•"]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1) if p.strip()]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]

    # 2. 职位关键词定位
    # 找所有关键词出现位置，排序：位置升序 + 长度降序（同位置取长关键词）
    hits: list[tuple[int, int, str]] = []  # (pos, -len, keyword)
    lo = text.lower()
    for kw in _ROLE_KEYWORDS:
        idx = lo.find(kw.lower())
        if idx >= 0:
            hits.append((idx, -len(kw), kw))
    if hits:
        hits.sort()
        role_hit_pos = hits[0][0]
        # 从命中位置往前找最后一个空格（company/role 分界）
        split_pos = text.rfind(" ", 0, role_hit_pos)
        if split_pos > 0:
            # 空格后从 split_pos+1 开始是 role；但如果 role 起点还不到关键词位置（有额外前缀如"海外"），把前缀也归 role
            company = text[:split_pos].strip(" ,，、:：-·—–")
            role = text[split_pos + 1:].strip()
            if company and role:
                return company, role
        # 没空格 / 空格在 0 位：把关键词位置当分界
        if role_hit_pos > 0:
            company = text[:role_hit_pos].strip(" ,，、:：-·—–")
            role = text[role_hit_pos:].strip()
            if company and role:
                return company, role
        # 关键词在开头 → 整段是 role
        return "", text.strip()

    # 3. 兜底
    return text.strip(), ""


def _normalize_date(date_str: str) -> str:
    if not date_str:
        return ""
    s = re.sub(r"\s+", " ", date_str.strip())
    s = s.replace("—", "-").replace("–", "-").replace("~", "-")
    return s


# ═════════════════════════════════════════════════════════════════
# skills
# ═════════════════════════════════════════════════════════════════

def _parse_skills(lines: list[str]) -> list[dict]:
    """技能章节：每行 "分类: 内容" 或纯列表。"""
    if not lines:
        return []

    # 先合并连续非空行（跟 bullets 一样的续行逻辑）
    merged = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # skills 一般每行就是一类，先当独立行处理
        merged.append(ln)

    skills = []
    for raw in merged:
        ln = _strip_bullet(raw)
        if not ln:
            continue
        # 优先 "标签: 值" 格式（中文 / 英文冒号 / | ｜）
        m = re.match(r"^([^:：|｜]{1,12})[:：|｜]\s*(.+)$", ln)
        if m:
            label = m.group(1).strip()
            text = m.group(2).strip()
            if label and text:
                skills.append({"label": label, "text": text})
                continue
        skills.append({"label": "", "text": ln})

    return skills


# ═════════════════════════════════════════════════════════════════
# education
# ═════════════════════════════════════════════════════════════════

def _parse_education(lines: list[str]) -> list[dict]:
    """教育背景：专门处理 "学校 | 专业 | 日期 | 荣誉/课程" 格式。"""
    if not lines:
        return []

    out: list[dict] = []

    # 合并：用日期切 item（每段教育一个 item）
    # 先找所有含日期的行，每行作为一个教育条目 header
    current: dict | None = None
    pending_bullets: list[str] = []

    def _flush():
        nonlocal current, pending_bullets
        if current is not None:
            current["bullets"] = pending_bullets[:]
            out.append(current)
        current = None
        pending_bullets = []

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue

        date_match = _DATE_RANGE_RE.search(ln)
        if date_match:
            _flush()
            date_str = date_match.group(0).strip()
            left_right = _DATE_RANGE_RE.sub("|", ln)  # 用 | 占位日期那段
            # 按 | 切所有段
            parts = [p.strip(" ·,，、:：-—–") for p in re.split(r"[|｜]", left_right) if p.strip(" ·,，、:：-—–")]
            school = parts[0] if len(parts) > 0 else ""
            major = parts[1] if len(parts) > 1 else ""
            bullets_tail = parts[2:]  # 日期后面的内容（已被 | 替代所以顺序变了）
            # 如果没有 | 分隔，尝试空格拆
            if not major and school:
                sp = school.split(None, 1)
                if len(sp) == 2:
                    school, major = sp[0], sp[1]
            current = {
                "school": school,
                "major": major,
                "date": _normalize_date(date_str),
                "bullets": [],
            }
            pending_bullets = list(bullets_tail)
            continue

        # 非日期行 → 补充当前 item 的 bullet
        if current is None:
            # 第一段没日期 — 把这行当 school
            current = {"school": ln, "major": "", "date": "", "bullets": []}
        else:
            pending_bullets.append(_strip_bullet(ln))

    _flush()
    return out


# ═════════════════════════════════════════════════════════════════
# helpers
# ═════════════════════════════════════════════════════════════════

def _is_bullet_start(line: str) -> bool:
    return bool(_BULLET_START_RE.match(line))


def _strip_bullet(line: str) -> str:
    s = _BULLET_START_RE.sub("", line)
    s = _NUM_BULLET_RE.sub("", s)
    return s.strip()


def _concat_cn_en(prev: str, curr: str) -> str:
    """合并前一段 + 当前行。中英文衔接时处理空格。"""
    if not prev:
        return curr
    if not curr:
        return prev
    # 去掉前一段行尾连字符（PDF 折行用的）
    prev = prev.rstrip(" -—–")
    # 判断衔接点是否都是 ASCII
    last = prev[-1] if prev else ""
    first = curr[0] if curr else ""
    # 两边都是中文 → 直接拼
    if _is_cjk(last) and _is_cjk(first):
        return prev + curr
    # 一边中文一边英文 / 符号 → 不加空格（中英衔接已有天然间隔）
    return prev + curr


def _is_cjk(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    return (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF) or (0x20000 <= code <= 0x2A6DF)


def _first(items: list[str]) -> str:
    return items[0] if items else ""
