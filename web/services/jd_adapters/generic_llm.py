"""通用 LLM fallback adapter。

所有未被专用 adapter 覆盖的 URL 走这里：
1. 下载 HTML
2. 剥标签得纯文本
3. 塞给 Claude 清洗成结构化 JD 原文

预算控制：单次 max_tokens=1500，约 ¥0.005/次。
"""
from __future__ import annotations

import json

from .base import Adapter, FetchResult, FetchError, http_get, strip_html


CLEANUP_SYSTEM = """你是一个 JD 清洗器。用户会贴一段从网页剥出来的乱糟糟文本，里面混着导航栏、
广告、footer。你的任务：从中提取出岗位描述正文，返回结构化 JSON。

严格按 JSON 输出，不要任何解释：
{
  "found": true | false,
  "company": "公司名或空串",
  "title": "岗位名或空串",
  "location": "城市或空串",
  "raw_text": "清洗后的岗位描述正文（包含职责+要求），没有找到则空串"
}

规则：
- raw_text 必须≥150字，低于则 found=false
- 去掉导航/页脚/版权/cookie 提示
- 保留"职责"和"要求"两部分的原文
- 不编造
"""


class GenericLLMAdapter(Adapter):
    name = "generic_llm"
    priority = 1  # 最后兜底

    def match(self, url: str) -> bool:
        return url.startswith("http")

    def fetch(self, url: str) -> FetchResult:
        try:
            html = http_get(url)
        except FetchError as e:
            return FetchResult(ok=False, source_url=url, adapter_name=self.name, error=str(e))

        text = strip_html(html)
        if len(text) < 200:
            return FetchResult(
                ok=False,
                source_url=url,
                adapter_name=self.name,
                error=f"stripped text too short ({len(text)}字)，可能是 SPA 或反爬页",
            )

        # 截断，避免给 LLM 塞 5 万字
        if len(text) > 8000:
            text = text[:8000]

        try:
            from services.ai_engine import _call_claude
            raw = _call_claude(
                system_prompt=CLEANUP_SYSTEM,
                user_prompt=f"源 URL: {url}\n\n网页正文：\n{text}",
                max_tokens=1500,
                temperature=0.1,
            )
            data = self._parse_json(raw)
        except Exception as e:
            return FetchResult(ok=False, source_url=url, adapter_name=self.name, error=f"llm cleanup failed: {e}")

        if not data.get("found") or len(data.get("raw_text", "")) < 150:
            return FetchResult(
                ok=False,
                source_url=url,
                adapter_name=self.name,
                error="LLM 未能从页面提取出有效 JD",
            )

        return FetchResult(
            ok=True,
            raw_text=data["raw_text"],
            company=data.get("company", ""),
            title=data.get("title", ""),
            location=data.get("location", ""),
            source_url=url,
            adapter_name=self.name,
            meta={"via": "llm_cleanup", "input_chars": len(text)},
        )

    def _parse_json(self, text: str) -> dict:
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
