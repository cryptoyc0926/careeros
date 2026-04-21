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
    r"(\d{4}\s*[.\-/年]\s*\d{1,2}(?:\s*[.\-/月]\s*\d{0,2})?)"
    r"\s*[-~至到—–]+\s*"
    r"(\d{4}\s*[.\-/年]\s*\d{1,2}(?:\s*[.\-/月]\s*\d{0,2})?|至今|今|现在|present|now)",
    re.IGNORECASE,
)
_SINGLE_DATE_RE = re.compile(r"\d{4}\s*[.\-/年]\s*\d{1,2}(?:\s*[.\-/月]\s*\d{0,2})?")
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
    "独立运营", "AI 方向内容账号", "求职全流程 AI 工具", "vibe coding 作品",
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

# 公司/机构识别关键词（用于判断 header 里"公司段"的位置）
_COMPANY_KEYWORDS = [
    # 中文企业后缀
    "有限公司", "股份公司", "股份有限公司", "集团", "公司", "科技", "交易所",
    "基金", "实验室", "研究院", "工作室", "研究所", "中心",
    "银行", "金融", "学院", "学校",
    # 英文企业后缀
    "Inc", "Ltd", "Corp", "LLC", "Group", "Labs", "Technologies", "Holdings",
]
_COMPANY_KEYWORDS.sort(key=len, reverse=True)

# 学校识别关键词（教育章节用于判断 school/major 哪个是学校）
_SCHOOL_KEYWORDS = [
    "大学", "学院", "学校", "University", "College", "Institute", "School",
]
_SCHOOL_KEYWORDS.sort(key=len, reverse=True)


def _pick_school_major(candidates: list[str]) -> tuple[str, str]:
    """从 2 段候选里判断谁是学校、谁是专业。

    启发式：含"大学/学院/学校/University/College"等关键词的归为 school，另一段是 major。
    如果两段都含或都不含 → 保持原顺序（第 1 段 school, 第 2 段 major）。
    """
    if not candidates:
        return "", ""
    if len(candidates) == 1:
        return candidates[0], ""

    a, b = candidates[0], candidates[1]
    a_low, b_low = a.lower(), b.lower()
    a_is_school = any(kw.lower() in a_low for kw in _SCHOOL_KEYWORDS)
    b_is_school = any(kw.lower() in b_low for kw in _SCHOOL_KEYWORDS)

    if b_is_school and not a_is_school:
        return b, a  # 颠倒
    return a, b  # 保持顺序


def _find_kw_hits(text: str, keywords: list[str]) -> list[tuple[int, int, str]]:
    """返回文本中所有命中关键词的位置：[(start_pos, end_pos, keyword), ...]"""
    hits: list[tuple[int, int, str]] = []
    lo = text.lower()
    for kw in keywords:
        kl = kw.lower()
        start = 0
        while True:
            idx = lo.find(kl, start)
            if idx < 0:
                break
            hits.append((idx, idx + len(kl), kw))
            start = idx + 1
    return hits

# 章节标题关键词
SECTIONS = {
    "basics":      ["个人信息", "基本信息", "联系方式", "基础信息"],
    "profile":     [
        "个人总结", "个人简介", "自我评价", "自我介绍", "个人评价", "自评",
        "概述", "简介", "Summary", "About Me", "Profile",
    ],
    "education":   ["教育背景", "教育经历", "学习经历", "教育", "学历", "Education"],
    "projects":    ["项目经历", "项目经验", "项目", "主要项目", "核心项目", "作品集", "Projects", "Project Experience"],
    "internships": [
        "实习经历", "实习经验", "工作经历", "工作经验", "职业经历", "职业经验",
        "实习", "工作", "Internship", "Work Experience", "Experience",
    ],
    "skills":      [
        "核心技能", "专业技能", "技能证书", "技能", "技术栈", "工具",
        "个人能力", "其他技能", "语言能力", "语言技能", "兴趣爱好", "证书", "资格证书",
        "Skills", "Technical Skills", "Languages", "Certifications",
    ],
}

_MAX_HEADING_LEN = 20


# ═════════════════════════════════════════════════════════════════
# 顶层
# ═════════════════════════════════════════════════════════════════

def parse_resume_text(text: str) -> dict:
    """把简历文本解析为 resume_master schema。"""
    text = _normalize_text(text)

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
    lines = _explode_inline_section_headings(text.split("\n"))
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


def _normalize_text(text: str) -> str:
    """清理 PDF/DOCX 提取常见空白，尽量保留原文行结构。"""
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n"))


def _explode_inline_section_headings(lines: list[str]) -> list[str]:
    """把“个人总结 xxxxx”这类标题同行内容拆开，避免章节丢失。"""
    heading_words = [kw for kws in SECTIONS.values() for kw in kws]
    heading_words.sort(key=len, reverse=True)
    heading_re = re.compile(r"^(" + "|".join(re.escape(x) for x in heading_words) + r")(?=\s|[:：]|$)", re.IGNORECASE)

    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = heading_re.match(line)
        if m and len(line) > len(m.group(1)):
            out.append(m.group(1))
            rest = line[m.end():].strip(" :：-—–")
            if rest:
                out.append(rest)
        else:
            out.append(line)
    return out


def _split_school_major_inline(text: str) -> tuple[str, str]:
    """从“浙江工商大学 应用统计学 · 本科”拆出学校和专业。"""
    for kw in _SCHOOL_KEYWORDS:
        idx = text.lower().find(kw.lower())
        if idx >= 0:
            school = text[: idx + len(kw)].strip()
            major = text[idx + len(kw):].strip(" ·,，、:：-—–")
            return school, major
    return text, ""


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
        if not date_match:
            single = _SINGLE_DATE_RE.search(ln)
            if single and not (_is_bullet_start(ln) or _NUM_BULLET_RE.match(ln)):
                # 项目经历常见“2026.04”单点时间；要求日期前仍有足够 header 文本，避免误把 bullet 数字当 header。
                head = _SINGLE_DATE_RE.sub("", ln).strip(" |,，、:：-·—–").strip()
                if len(head) >= 4:
                    date_match = single
        if date_match:
            if current is not None:
                items.append(current)
            date_str = date_match.group(0).strip()
            header_text = ln[:date_match.start()] + ln[date_match.end():]
            header_text = header_text.strip(" |,，、:：-·—–").strip()
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

    v3 策略（支持双向顺序）：
    1. 显式分隔符 | ｜ · • — – /
    2. 同时找 role 关键词和 company 关键词的位置
    3. 根据两者相对位置判断顺序：
       - company 在前 role 在后：`AI Trading 社区搭建 用户增长运营`
       - role 在前 company 在后：`数据运营实习生 WEEX 交易所`
    4. 无 company 关键词命中时：按"公司在前职位在后"的传统约定切（从 role 位置往前找空格）
    5. 关键词在开头 → 整段是 role
    """
    if not text:
        return "", ""

    # 1. 显式分隔符
    for sep in ["|", "｜", " - ", " — ", " – ", " / "]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1) if p.strip()]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]

    for sep in ["·", "•"]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep, 1) if p.strip()]
            if len(parts) == 2 and parts[0] and parts[1]:
                left, right = parts
                left_company, left_role = _split_company_role_no_mid_sep(left)
                if left_company and left_role:
                    return left_company, f"{left_role} · {right}"
                return left, right

    # 2. 找 role 关键词 + company 关键词位置
    role_hits = _find_kw_hits(text, _ROLE_KEYWORDS)
    role_hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))  # 位置升序 + 长度降序
    company_hits = _find_kw_hits(text, _COMPANY_KEYWORDS)
    company_hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))

    if role_hits and company_hits:
        role_start, role_end, _ = role_hits[0]
        comp_start, comp_end, _ = company_hits[0]

        # Case A: role 在前 company 在后 → "职位 公司" 顺序
        if role_start < comp_start:
            # 从 role_end 到 comp_start 范围内找**最左**空格作为分界
            # （这样 role 段最短；company 段包含完整公司名 + 前缀如"WEEX"）
            split_pos = text.find(" ", role_end, comp_start)
            if split_pos < 0:
                # 罕见：role 和 company 之间没空格 → 用关键词边界切
                split_pos = comp_start
                role_txt = text[:split_pos].strip(" ,，、:：-·—–")
                company_txt = text[split_pos:].strip()
            else:
                role_txt = text[:split_pos].strip(" ,，、:：-·—–")
                company_txt = text[split_pos + 1:].strip()
            if role_txt and company_txt:
                return company_txt, role_txt

        # Case B: company 在前 role 在后 → "公司 职位" 传统顺序
        else:
            split_pos = text.rfind(" ", comp_end, role_start)
            if split_pos < 0:
                split_pos = role_start - 1 if role_start > comp_end else comp_end
            company_txt = text[:split_pos].strip(" ,，、:：-·—–")
            role_txt = text[split_pos + 1:].strip()
            if company_txt and role_txt:
                return company_txt, role_txt

    # 3. 只有 role 关键词（没公司词）→ 默认 "公司 职位" 顺序，从 role 位置往前找空格
    if role_hits:
        role_start = role_hits[0][0]
        split_pos = text.rfind(" ", 0, role_start)
        if split_pos > 0:
            company = text[:split_pos].strip(" ,，、:：-·—–")
            role = text[split_pos + 1:].strip()
            if company and role:
                return company, role
        # 关键词在最左：整段是 role
        if role_start == 0:
            return "", text.strip()
        # 没空格但关键词不在最左：按关键词位置切
        company = text[:role_start].strip(" ,，、:：-·—–")
        role = text[role_start:].strip()
        if company and role:
            return company, role

    # 4. 只有 company 关键词（没 role）→ 默认公司在前，剩余当 role
    if company_hits:
        comp_end = company_hits[-1][1]  # 取最后一个 company 词的词尾
        # 从 comp_end 之后的内容是 role
        after = text[comp_end:].strip(" ,，、:：-·—–")
        before_and_self = text[:comp_end].strip(" ,，、:：-·—–")
        if after:
            return before_and_self, after
        # company 在末尾 → 前缀是 role
        if comp_end < len(text):
            pass  # 已处理
        split_pos = text.rfind(" ", 0, company_hits[0][0])
        if split_pos > 0:
            role_pre = text[:split_pos].strip(" ,，、:：-·—–")
            company = text[split_pos + 1:].strip()
            if role_pre and company:
                return company, role_pre

    # 5. 兜底：整段当 company
    return text.strip(), ""


def _split_company_role_no_mid_sep(text: str) -> tuple[str, str]:
    """只用关键词在单段内拆 company/role，避免递归处理中点分隔符。"""
    role_hits = _find_kw_hits(text, _ROLE_KEYWORDS)
    role_hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    if not role_hits:
        return text.strip(), ""

    role_start = role_hits[0][0]
    if role_start <= 0:
        return "", text.strip()
    company = text[:role_start].strip(" ,，、:：-·—–")
    role = text[role_start:].strip(" ,，、:：-·—–")
    return company, role


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

            # 没分隔符时把单段用空格切
            if len(parts) == 1:
                single = parts[0]
                # 先尝试按空格切成两段
                sp = single.rsplit(None, 1)  # 从右侧切一次（最后一段可能是学校）
                if len(sp) == 2:
                    parts = sp
                else:
                    parts = [single]

            # school/major 启发式：谁含"大学/学院/学校"谁是 school；同段里也能拆专业。
            if parts:
                inline_school, inline_major = _split_school_major_inline(parts[0])
            else:
                inline_school, inline_major = "", ""

            if inline_school and inline_major:
                school, major = inline_school, inline_major
                bullets_tail = parts[1:]
            else:
                school, major = _pick_school_major(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "", "")
                bullets_tail = parts[2:]

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
