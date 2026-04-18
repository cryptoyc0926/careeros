"""
Career OS — AI 引擎（Claude API 封装）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
所有与 Claude API 交互的逻辑集中在此。
支持官方端点和自定义代理端点。
"""

from __future__ import annotations

import json
import hashlib
import yaml
from pathlib import Path
from config import settings

import anthropic


import time
import httpx


def _get_client() -> anthropic.Anthropic:
    """创建 Anthropic 客户端，支持自定义 base_url，配置合理超时。"""
    kwargs = {
        "api_key": settings.anthropic_api_key,
        "timeout": httpx.Timeout(120.0, connect=15.0),  # 连接 15s，总计 120s
        "max_retries": 0,  # 我们自己控制重试逻辑
    }
    if settings.has_custom_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    return anthropic.Anthropic(**kwargs)


class AIError(Exception):
    """AI 调用相关的异常，附带用户友好的错误信息。"""
    pass


def _call_claude(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    retries: int = 2,
) -> str:
    """
    通用 Claude 调用，带重试和友好错误处理。

    重试策略：
      - 504/502/429/timeout → 自动重试（最多 retries 次）
      - 401/403 → 不重试（认证问题）
      - 其他异常 → 重试一次
    """
    client = _get_client()
    last_error = None

    for attempt in range(1 + retries):
        try:
            # 使用流式调用 — 某些代理不支持非流式返回 content
            collected_text = []
            with client.messages.stream(
                model=settings.claude_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    collected_text.append(text)

            result = "".join(collected_text)
            if not result.strip():
                raise AIError(
                    "API 返回了空内容。可能原因：\n"
                    f"1. 代理不支持模型 '{settings.claude_model}'\n"
                    "2. 代理服务异常\n"
                    "请在「设置」页面检查模型名称或更换端点。"
                )
            return result

        except anthropic.AuthenticationError as e:
            raise AIError(
                f"API 认证失败：请检查「设置」中的 API Key 是否正确。\n"
                f"当前端点: {settings.anthropic_base_url or '官方'}\n"
                f"原始错误: {e}"
            )

        except anthropic.RateLimitError as e:
            last_error = e
            if attempt < retries:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue
            raise AIError(f"API 请求频率超限，请稍后再试。（已重试 {retries} 次）")

        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
            last_error = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise AIError(
                f"API 连接超时：代理服务器无响应。\n\n"
                f"当前端点: {settings.anthropic_base_url or '官方'}\n"
                f"可能原因：代理服务不稳定，请稍后重试或更换 API 端点。\n"
                f"（已重试 {retries} 次）"
            )

        except anthropic.APIStatusError as e:
            last_error = e
            status = getattr(e, "status_code", 0)
            # 5xx 服务端错误 → 重试
            if status >= 500 and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            # 提取可读错误（避免把整个 HTML 页面显示出来）
            err_msg = str(e)
            if "<html" in err_msg.lower() or "<!doctype" in err_msg.lower():
                err_msg = f"API 返回了 HTTP {status} 错误（服务端异常）"
            raise AIError(
                f"API 调用失败 (HTTP {status})：{err_msg}\n\n"
                f"当前端点: {settings.anthropic_base_url or '官方'}\n"
                f"（已重试 {attempt} 次）"
            )

        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(2)
                continue
            err_msg = str(e)
            if "<html" in err_msg.lower() or "<!doctype" in err_msg.lower():
                err_msg = "API 返回了非预期的 HTML 响应（代理服务异常）"
            raise AIError(f"AI 调用异常：{err_msg}")

    raise AIError(f"AI 调用失败（所有重试已用尽）: {last_error}")


# ═══════════════════════════════════════════════════════════════
# JD 解析
# ═══════════════════════════════════════════════════════════════

JD_PARSE_SYSTEM = """你是一个专业的职位描述解析器。用户会给你一段职位描述原文，你需要提取结构化信息。

请严格按照以下 JSON 格式输出（不要输出其他内容）：
{
  "skills_required": ["技能1", "技能2", ...],
  "skills_preferred": ["技能1", "技能2", ...],
  "experience_min": 数字或null,
  "experience_max": 数字或null,
  "salary_min": 数字或null,
  "salary_max": 数字或null,
  "location_type": "remote" 或 "hybrid" 或 "onsite",
  "responsibilities": ["职责1", "职责2", ...],
  "education": "学历要求" 或 null
}

规则：
- skills_required：JD 中明确要求的技能（必须掌握的）
- skills_preferred：JD 中提到的加分项或优先考虑的技能
- 薪资数字单位统一为"元/月"，如果是年薪则除以12，如果没有提到则为 null
- experience_min/max 单位为年，如"3-5年"则 min=3, max=5
- 只输出 JSON，不要有任何解释文字"""


def parse_jd(raw_text: str) -> dict:
    """调用 Claude 解析 JD，返回结构化 dict。"""
    result_text = _call_claude(
        system_prompt=JD_PARSE_SYSTEM,
        user_prompt=f"请解析以下职位描述：\n\n{raw_text}",
        max_tokens=2048,
        temperature=0.1,
    )

    # 提取 JSON（兼容 Claude 可能输出 markdown code block）
    text = result_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取花括号之间的内容
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {}


# ═══════════════════════════════════════════════════════════════
# Fit Score 计算
# ═══════════════════════════════════════════════════════════════

def calculate_fit_score(jd_parsed: dict, master_resume_path: Path = None) -> float:
    """计算 JD 与主简历的匹配分（0-100）。"""
    if master_resume_path is None:
        master_resume_path = settings.master_resume_full_path

    if not master_resume_path.exists():
        return 0.0

    resume = yaml.safe_load(master_resume_path.read_text(encoding="utf-8"))
    if not resume:
        return 0.0

    # 收集简历中所有技能（小写比较）
    resume_skills = set()
    for category_skills in resume.get("skills", {}).values():
        for s in category_skills:
            resume_skills.add(s.lower())

    # 收集简历中所有成就标签
    for exp in resume.get("experience", []):
        for ach in exp.get("achievements", []):
            for tag in ach.get("tags", []):
                resume_skills.add(tag.lower())

    # JD 要求的技能
    required = {s.lower() for s in jd_parsed.get("skills_required", [])}
    preferred = {s.lower() for s in jd_parsed.get("skills_preferred", [])}

    if not required and not preferred:
        return 50.0  # 无法计算时给中间分

    # 匹配率
    req_match = len(required & resume_skills) / max(len(required), 1)
    pref_match = len(preferred & resume_skills) / max(len(preferred), 1)

    # 加权计算
    score = (req_match * 0.60 + pref_match * 0.40) * 100
    return round(min(score, 100.0), 1)


# ═══════════════════════════════════════════════════════════════
# 简历生成
# ═══════════════════════════════════════════════════════════════

RESUME_SYSTEM = """你是一位资深的简历撰写专家。你的任务是根据目标职位描述和候选人的经历素材，生成一份量身定制的简历和求职信。

## 内容规则
1. 只使用提供的素材中的成就，不要编造。
2. 保留原始数据和指标，不夸大。
3. 改写要点时匹配 JD 的用语和关注点。
4. 简历控制在一页以内。

## 风格规则（避免 AI 检测）
5. 句式长短交替：短陈述句（5-8字）与长复合句混合。
6. 禁用词：利用、赋能、驱动、深耕、赋能、助力、打造、抓手。
7. 用量化结果开头（如"延迟降低62%"而非"成功降低了延迟"）。
8. 自然使用行业术语，不堆砌关键词。
9. 包含具体细节，展示真实实操经验。
10. 语气直接自信，不用虚词和修饰语。

## 输出格式（严格遵守，不要加其他内容）
---RESUME_START---
[Markdown 格式的简历]
---RESUME_END---
---COVER_LETTER_START---
[3-4段的求职信]
---COVER_LETTER_END---"""


def _pre_select_achievements(jd_parsed: dict, resume_data: dict) -> list[dict]:
    """根据 JD 技能要求预选相关成就。"""
    required = {s.lower() for s in jd_parsed.get("skills_required", [])}
    preferred = {s.lower() for s in jd_parsed.get("skills_preferred", [])}
    all_target = required | preferred

    scored = []
    for exp in resume_data.get("experience", []):
        for ach in exp.get("achievements", []):
            tags = {t.lower() for t in ach.get("tags", [])}
            overlap = len(tags & all_target)
            impact_bonus = {"high": 2, "medium": 1, "low": 0}.get(ach.get("impact", "medium"), 1)
            score = overlap * 3 + impact_bonus
            scored.append({
                "company": exp.get("company", ""),
                "title": exp.get("title", ""),
                "period": f"{exp.get('start', '')} — {exp.get('end', '至今')}",
                "achievement": ach,
                "relevance_score": score,
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:15]  # 最多取 15 条最相关的


def generate_tailored_resume(
    jd_raw_text: str,
    jd_parsed: dict,
    resume_data: dict,
    temperature: float = 0.7,
    include_cover_letter: bool = True,
) -> dict:
    """生成定制简历和求职信。返回 {resume_md, cover_letter_md, achievements_used, prompt_hash}。"""

    # 预选相关成就
    selected = _pre_select_achievements(jd_parsed, resume_data)
    if not selected:
        return {"error": "没有找到与该 JD 匹配的成就，请先完善主简历。"}

    # 构建 prompt
    meta = resume_data.get("meta", {})
    skills = resume_data.get("skills", {})
    education = resume_data.get("education", [])

    achievements_text = ""
    for s in selected:
        ach = s["achievement"]
        achievements_text += f"- [{s['company']} / {s['title']}] {ach['text']}\n"

    skills_text = ""
    for cat, items in skills.items():
        skills_text += f"  {cat}: {', '.join(items)}\n"

    edu_text = ""
    for edu in education:
        edu_text += f"  {edu.get('degree', '')} — {edu.get('institution', '')} ({edu.get('year', '')})\n"

    user_prompt = f"""## 目标职位描述
{jd_raw_text}

## 候选人信息
姓名: {meta.get('name', '')}
邮箱: {meta.get('email', '')}
电话: {meta.get('phone', '')}
所在地: {meta.get('location', '')}

## 候选人技能
{skills_text}

## 候选人教育背景
{edu_text}

## 候选人相关成就（按相关度排序，请从中选择最匹配的）
{achievements_text}

请根据以上信息，为该职位生成一份量身定制的中文简历{' 和求职信' if include_cover_letter else ''}。"""

    prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]

    # 调用 Claude
    result = _call_claude(
        system_prompt=RESUME_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=4096,
        temperature=temperature,
    )

    # 解析输出
    resume_md = ""
    cover_letter_md = ""

    if "---RESUME_START---" in result and "---RESUME_END---" in result:
        resume_md = result.split("---RESUME_START---")[1].split("---RESUME_END---")[0].strip()
    else:
        resume_md = result.strip()

    if "---COVER_LETTER_START---" in result and "---COVER_LETTER_END---" in result:
        cover_letter_md = result.split("---COVER_LETTER_START---")[1].split("---COVER_LETTER_END---")[0].strip()

    return {
        "resume_md": resume_md,
        "cover_letter_md": cover_letter_md,
        "achievements_used": [s["achievement"].get("id", "") for s in selected if s["achievement"].get("id")],
        "prompt_hash": prompt_hash,
    }


# ═══════════════════════════════════════════════════════════════
# 面试准备
# ═══════════════════════════════════════════════════════════════

INTERVIEW_SYSTEM = """你是一位资深面试教练。根据职位描述和候选人简历，生成面试准备材料。

请严格按以下 JSON 格式输出（不要有其他内容）：
{
  "technical": [
    {"question": "问题", "why": "为什么会问", "answer_framework": "答题框架", "pitfalls": "注意事项"}
  ],
  "behavioral": [...],
  "system_design": [...],
  "culture_fit": [...],
  "reverse_interview": [...]
}

每个类别生成 3-5 个问题。behavioral 类型请用 STAR 格式给出答题框架。
所有内容用中文。"""


def generate_interview_prep(jd_raw_text: str, resume_summary: str, company: str) -> dict:
    """生成面试准备材料。"""
    user_prompt = f"""## 目标公司
{company}

## 职位描述
{jd_raw_text}

## 候选人简历摘要
{resume_summary}

请生成全面的面试准备材料。"""

    result = _call_claude(
        system_prompt=INTERVIEW_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=4096,
        temperature=0.5,
    )

    text = result.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"error": "解析失败，请重试", "raw": result}


# ═══════════════════════════════════════════════════════════════
# Auto-Pipeline 一键全流程
# ═══════════════════════════════════════════════════════════════

def auto_pipeline(
    jd_raw_text: str,
    resume_data: dict,
    temperature: float = 0.7,
) -> dict:
    """一键处理：解析 JD → 匹配打分 → 生成简历。

    Returns:
        {jd_parsed, fit_score, resume_md, cover_letter_md, prompt_hash}
    """
    # Step 1: 解析 JD
    jd_parsed = parse_jd(jd_raw_text)
    if not jd_parsed:
        return {"error": "JD 解析失败，请检查 JD 内容是否完整。"}

    # Step 2: 计算匹配分
    fit_score = calculate_fit_score(jd_parsed)

    # Step 3: 生成简历
    result = generate_tailored_resume(
        jd_raw_text=jd_raw_text,
        jd_parsed=jd_parsed,
        resume_data=resume_data,
        temperature=temperature,
        include_cover_letter=True,
    )

    if "error" in result:
        return result

    result["jd_parsed"] = jd_parsed
    result["fit_score"] = fit_score
    return result


# ═══════════════════════════════════════════════════════════════
# 5 段式深度评估
# ═══════════════════════════════════════════════════════════════

DEEP_EVAL_SYSTEM = """你是一位资深校招求职顾问。根据 JD 和候选人简历，输出 5 段深度评估。

严格按以下 Markdown 格式输出（不要输出其他内容）：

## A. JD-简历匹配分析
逐条对比 JD 要求 vs 候选人经历，每条标注：
- ✅ 匹配：JD 要求 → 对应经历
- ⚠️ 弱匹配：JD 要求 → 部分相关经历
- ❌ 缺失：JD 要求 → 无直接经历

## B. 经验 Gap 分析
列出候选人不满足的要求，以及可以用哪些相关经验弥补。

## C. 简历个性化建议
针对这个 JD，简历哪些部分需要强调、弱化或补充。给出具体的修改建议。

## D. 面试预测题（5题）
基于 JD 预测 5 个高概率面试题，每题给出：
- 问题
- 为什么会问
- 回答要点（2-3句）

## E. 投递策略建议
- 推荐投递渠道（内推/Boss直聘/校招门户）及理由
- 竞争激烈度判断
- 最佳投递时间建议

所有内容用中文。"""


def deep_evaluate(jd_raw_text: str, resume_summary: str) -> str:
    """5 段式深度评估，返回 Markdown 文本。"""
    user_prompt = f"""## 目标职位描述
{jd_raw_text}

## 候选人简历摘要
{resume_summary}

请输出 5 段深度评估。"""

    return _call_claude(
        system_prompt=DEEP_EVAL_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=4096,
        temperature=0.5,
    )


# ═══════════════════════════════════════════════════════════════
# Ghost Job 检测（中国特色）
# ═══════════════════════════════════════════════════════════════

GHOST_CHECK_SYSTEM = """你是一位中国校招市场分析专家。分析以下 JD 是否可能是「虚假岗位」。

中国校招中常见的虚假岗位类型：
1. **养鱼岗**：JD描述模糊、无具体项目、常年挂着
2. **KPI岗**：HR为完成面试KPI发的岗位
3. **背调岗**：面试深挖方案细节但不给offer，实为套方案
4. **万年岗**：同一岗位挂3个月以上
5. **内定岗**：JD要求极度精准匹配特定人背景

分析以下信号并给出判断：
- JD 具体度（是否有具体项目/产品/团队描述）
- 岗位要求合理性（是否过于宽泛或过于精准）
- 薪资透明度
- 职责描述质量

严格按 JSON 格式输出：
{
  "credibility": "高" 或 "中" 或 "低",
  "score": 1-10的可信度分数,
  "risk_type": "正常" 或 "疑似养鱼" 或 "疑似KPI" 或 "疑似内定" 或 "疑似背调" 或 "疑似万年岗",
  "signals": ["信号1", "信号2"],
  "recommendation": "建议文字"
}"""


def ghost_check(jd_text: str, company: str) -> dict:
    """Ghost Job 检测，返回可信度评估。"""
    result_text = _call_claude(
        system_prompt=GHOST_CHECK_SYSTEM,
        user_prompt=f"公司: {company}\n\nJD 原文:\n{jd_text}",
        max_tokens=1024,
        temperature=0.3,
    )

    text = result_text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {"credibility": "中", "score": 5, "risk_type": "未知", "signals": ["解析失败"], "recommendation": "建议人工判断"}


CHEATSHEET_SYSTEM = """你是一位企业研究专家。根据公司名称和目标岗位，生成一份面试速查表。

用 Markdown 格式输出，包含以下部分：
# {公司名} — 面试速查表

## 公司概况
（简介、规模、融资/营收、主要产品）

## 技术栈与工程文化
（根据公开信息推断）

## 核心价值观与文化
（列出价值观，并给出你的经历如何匹配的话术建议）

## 近期动态
（可能的产品发布、业务变化、组织调整）

## 竞争格局
（主要竞对及差异化定位）

## "为什么选择这家公司" 话术
（结合候选人背景的推荐话术）

所有内容用中文。"""


def generate_cheatsheet(company: str, role: str, resume_summary: str) -> str:
    """生成公司速查表（Markdown）。"""
    user_prompt = f"公司: {company}\n岗位: {role}\n候选人背景摘要: {resume_summary}"
    return _call_claude(
        system_prompt=CHEATSHEET_SYSTEM,
        user_prompt=user_prompt,
        max_tokens=3000,
        temperature=0.5,
    )
