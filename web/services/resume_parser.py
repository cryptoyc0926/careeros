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


PARSE_SYSTEM = """你是一位简历结构化专家。用户会粘贴一份自由格式的简历文本（PDF/DOCX 提取），你需要把它**准确**拆解到下面的 JSON schema。

## 硬规则
1. 只输出一个合法 JSON 对象，不要有前后文本、markdown 标记或注释
2. **绝对不能编造**任何原文没有的信息。原文没有的字段填空字符串 "" 或空数组 []
3. bullet 项逐字保留，不要改写或总结（允许剪除纯装饰性前缀如 "- " / "• "）
4. 所有数字、公司名、职位名、学校名、时间、URL 照搬原文
5. 数字可以用 <b>xxx</b> 标签包裹以便在 UI 里加粗显示（可选）

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
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("缺少 anthropic SDK") from e

    from config import settings

    if not settings.has_anthropic_key:
        raise RuntimeError("API Key 未配置，请先在「系统设置」填入 Key")

    if not raw_text or len(raw_text.strip()) < 50:
        raise RuntimeError(f"文本太短（{len(raw_text)} 字符），无法解析")

    client_kwargs = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        client_kwargs["base_url"] = settings.anthropic_base_url
    client = Anthropic(**client_kwargs)

    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        system=PARSE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"以下是简历原文，请按 schema 输出 JSON：\n\n{raw_text}",
        }],
    )

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

    # 补齐 schema（防御性：AI 可能漏掉某些字段）
    return _normalize_schema(data)


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
