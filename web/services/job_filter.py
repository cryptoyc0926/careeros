"""
排除公司过滤器 — 实现 CLAUDE.md「明确排除」规则的代码层兜底。

排除来源：CLAUDE.md §目标公司 → 明确排除（禁止推荐、禁止出现在岗位池）
    - 字节跳动 / 蚂蚁集团 / 腾讯 / 网易

覆盖面：导入层 early reject + 展示层 DataFrame 过滤 + DB 层清洗脚本。

用法：
    from services.job_filter import is_excluded_company, filter_excluded_df, EXCLUDED_COMPANIES

    # 早期拦截（JD 导入、爬虫）
    if is_excluded_company(company_name):
        return None

    # DataFrame 过滤（展示层）
    df = filter_excluded_df(df, company_col="公司")
"""

from __future__ import annotations
from typing import Iterable
import pandas as pd


# 排除公司关键字集合（命中任一即排除）
# 小写 + 中英文变体。匹配用「包含」而非精确相等，覆盖「字节跳动（杭州）」「腾讯云」等子公司/变体。
EXCLUDED_COMPANIES: tuple[str, ...] = (
    "字节跳动", "字节",
    "bytedance", "byte dance",
    "腾讯",
    "tencent",
    "蚂蚁集团", "蚂蚁金服", "蚂蚁",
    "ant group", "ant financial",
    "网易",
    "netease",
)


def is_excluded_company(company: str | None) -> bool:
    """判断公司名是否命中排除列表。None / 空串返回 False（不拦截）。"""
    if not company:
        return False
    name = str(company).strip().lower()
    if not name:
        return False
    return any(kw in name for kw in EXCLUDED_COMPANIES)


def filter_excluded_df(df: pd.DataFrame, company_col: str = "公司") -> pd.DataFrame:
    """从 DataFrame 中移除排除公司的行。列不存在或 df 为空时原样返回。"""
    if df is None or df.empty or company_col not in df.columns:
        return df
    mask = df[company_col].apply(is_excluded_company)
    return df[~mask].reset_index(drop=True)


def filter_excluded_rows(rows: Iterable[dict], company_key: str = "company") -> list[dict]:
    """从 dict list 中移除排除公司的行。"""
    return [r for r in rows if not is_excluded_company(r.get(company_key))]
