"""JD 抓取 adapter 层。

每个 adapter 负责一类 ATS 或招聘站，输入 URL，输出 FetchResult。
主路由 `jd_fetcher.fetch_jd()` 根据 URL 域名匹配 adapter，按优先级回落。
"""
from .base import Adapter, FetchResult, FetchError
from .feishu import FeishuAdapter
from .lever import LeverAdapter
from .generic_llm import GenericLLMAdapter

# 注册顺序 = 匹配优先级
REGISTERED: list[Adapter] = [
    FeishuAdapter(),
    LeverAdapter(),
    GenericLLMAdapter(),  # 兜底，match 所有
]


def pick(url: str) -> Adapter | None:
    for a in REGISTERED:
        if a.match(url):
            return a
    return None
