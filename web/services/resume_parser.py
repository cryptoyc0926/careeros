"""
AI 主简历解析：纯文本 → resume_master schema JSON
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
输入：上传文件提取出的 raw text
输出：匹配 resume_master 结构的 dict（basics / profile / projects / internships / skills / education）

用法：
    from services.resume_parser import parse_resume_text
    data = parse_resume_text(raw_text)  # 需要 Anthropic API Key 已配置
"""
from __future__ import annotations

import json
import re
from typing import Any


PARSE_SYSTEM = """你是一位简历结构化专家。用户会粘贴一份自由格式的简历文本（PDF/DOCX 提取），你需要把它**准确**拆解到下面的 JSON schema。

## 硬规则
1. 只输出一个合法 JSON 对象，不要有前后文本、markdown 标记或注释
2. **绝对不能编造**任何原文没有的信息。原文没有的字段填空字符串 "" 或空数组 []
3. bullet 项逐字保留，不要改写或总结（允许剪除纯装饰性前缀如 "- " / "• "）
4. 所有数字、公司名、职位名、学校名、时间、URL 照搬原文
5. 数字可以用 <b>xxx</b> 标签包裹以便在 UI 里加粗显示（可选）
6. 如果 profile 为空，但原文里有一段明显的个人总结/个人陈述/简介段落，请把「除基本信息和教育外的首段完整文本」放入 profile
7. 如果 projects 为空，但 internships 里有明显是项目/开源作品/个人作品的条目，请把这些条目迁到 projects，internships 只保留真实公司/组织经历

## 输出 Schema
{
  "basics": {
    "name": "",
    "phone": "",
    "email": "",
    "target_role": "",
    "city": "",
    "availability": "",
    "photo": ""
  },
  "profile": "个人总结/自我介绍段落（如果原文有）",
  "projects": [
    {
      "company": "项目/作品名",
      "role": "角色（如用户增长运营）",
      "date": "YYYY.MM - YYYY.MM 或 YYYY.MM - 至今",
      "bullets": ["要点1", "要点2", ...]
    }
  ],
  "internships": [
    { "company": "", "role": "", "date": "", "bullets": [] }
  ],
  "skills": [
    { "label": "分类", "text": "具体技能" }
  ],
  "education": [
    { "school": "", "major": "", "date": "", "bullets": ["核心课程:...", "奖项:..."] }
  ]
}

开始处理用户提供的文本。"""


def parse_resume_text(raw_text: str) -> dict:
    """调 Claude 把自由格式文本转成 resume_master schema dict。

    Raises:
        RuntimeError: API 未配置、API 调用失败、返回不是合法 JSON
    """
    from services.llm_client import make_client, friendly_error
    from config import settings

    if not raw_text or len(raw_text.strip()) < 50:
        raise RuntimeError(f"文本太短（{len(raw_text)} 字符），无法解析")

    client = make_client()

    try:
        resp = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=PARSE_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"以下是简历原文，请按 schema 输出 JSON：\n\n{raw_text}",
            }],
        )
    except Exception as e:
        raise RuntimeError(friendly_error(e)) from e

    reply = ""
    for block in resp.content:
        if hasattr(block, "text"):
            reply += block.text

    # 有些模型会在 JSON 前后输出解释，尝试提取
    reply = reply.strip()
    if reply.startswith("```"):
        reply = re.sub(r"^```(?:json)?\s*", "", reply)
        reply = re.sub(r"\s*```$", "", reply)

    try:
        data = json.loads(reply)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI 返回的不是合法 JSON：{e}\n\n原始回复：{reply[:500]}")

    # 补齐 schema，并对常见漏判做一次本地修正
    return _repair_parsed_schema(raw_text, data)


def _normalize_schema(data: dict) -> dict:
    """填充缺失字段，统一 schema。"""
    out = {
        "basics": {
            "name": "", "phone": "", "email": "",
            "target_role": "", "city": "", "availability": "", "photo": "",
        },
        "profile": "",
        "projects": [],
        "internships": [],
        "skills": [],
        "education": [],
    }
    if not isinstance(data, dict):
        return out

    b = data.get("basics", {}) or {}
    if isinstance(b, dict):
        for k in out["basics"].keys():
            out["basics"][k] = str(b.get(k, "") or "")

    out["profile"] = str(data.get("profile", "") or "")

    for key in ("projects", "internships"):
        items = data.get(key, []) or []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                out[key].append({
                    "company": str(item.get("company", "") or ""),
                    "role":    str(item.get("role", "") or ""),
                    "date":    str(item.get("date", "") or ""),
                    "bullets": [str(x) for x in (item.get("bullets", []) or []) if x],
                })

    skills = data.get("skills", []) or []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict):
                out["skills"].append({
                    "label": str(s.get("label", "") or ""),
                    "text":  str(s.get("text", "") or ""),
                })

    edu = data.get("education", []) or []
    if isinstance(edu, list):
        for e in edu:
            if isinstance(e, dict):
                out["education"].append({
                    "school": str(e.get("school", "") or ""),
                    "major":  str(e.get("major", "") or ""),
                    "date":   str(e.get("date", "") or ""),
                    "bullets": [str(x) for x in (e.get("bullets", []) or []) if x],
                })

    return out


_PROFILE_HEADINGS = {
    "个人总结", "个人简介", "个人陈述", "自我评价", "自我介绍", "个人评价",
    "概述", "简介", "Summary", "About Me", "Profile",
}
_NON_PROFILE_HEADINGS = {
    "教育背景", "教育经历", "学习经历", "教育", "学历", "Education",
    "项目经历", "项目经验", "项目实践", "项目作品", "项目实战", "项目", "主要项目", "核心项目", "作品集",
    "实习经历", "实习经验", "工作经历", "工作经验", "职业经历", "职业经验", "Internship", "Work Experience",
    "技能", "核心技能", "专业技能", "技能证书", "技术栈", "Tools", "Skills", "Languages",
}
_PROJECT_LIKE_HINTS = ("careeros", "项目", "作品", "开源", "系统", "社区", "账号", "@")
_EMPLOYER_HINTS = ("有限公司", "科技", "tech", "交易所", "基金", "银行", "金融", "大学", "研究院", "studio", "corp", "inc")
_ROLE_PROJECT_HINTS = ("独立运营", "个人项目", "项目负责人", "产品与自动化实践")


def _repair_parsed_schema(raw_text: str, data: dict[str, Any]) -> dict[str, Any]:
    repaired = _normalize_schema(data)

    if not repaired["profile"]:
        inferred_profile = _infer_profile_from_raw_text(raw_text)
        if inferred_profile:
            repaired["profile"] = inferred_profile

    if not repaired["projects"] and repaired["internships"]:
        migrated_projects = []
        remaining_internships = []
        for item in repaired["internships"]:
            if _looks_like_project_item(item):
                migrated_projects.append(item)
            else:
                remaining_internships.append(item)
        if migrated_projects:
            repaired["projects"] = migrated_projects
            repaired["internships"] = remaining_internships

    return repaired


def _infer_profile_from_raw_text(raw_text: str) -> str:
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text or "") if block.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        first_line = lines[0].strip("：: ")
        if first_line in _NON_PROFILE_HEADINGS:
            continue
        if first_line in _PROFILE_HEADINGS:
            lines = lines[1:]
        if not lines:
            continue

        candidate = " ".join(lines).strip()
        if len(candidate) < 20:
            continue
        if re.search(r"@|邮箱|email|电话|手机|\b\d{11}\b", candidate, re.IGNORECASE):
            continue
        if re.search(r"\b\d{4}[./-]\d{1,2}\b", candidate):
            continue
        if any(line.startswith(("•", "-", "*")) for line in lines):
            continue
        return candidate
    return ""


def _looks_like_project_item(item: dict[str, Any]) -> bool:
    company = str(item.get("company", "") or "")
    role = str(item.get("role", "") or "")
    company_lower = company.lower()
    role_lower = role.lower()
    combined_lower = f"{company} {role}".lower()

    if any(hint in combined_lower for hint in _PROJECT_LIKE_HINTS):
        return True
    if company and not any(hint in company_lower for hint in _EMPLOYER_HINTS):
        return any(hint.lower() in role_lower for hint in _ROLE_PROJECT_HINTS)
    return False
