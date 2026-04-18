"""
Boss直聘/脉脉/邮件 消息模板生成
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
各渠道差异化话术，支持 AI 个性化填充。

模板占位符说明：
- {company} / {position} / {title} / {direction} / {name} / {school} / {major} / {year}
- {highlights} — 一段你的核心亮点（从 user_profile.yaml 读）
- {user_email} / {user_name} — 你的联系方式（从 user_profile.yaml 读）
"""

from __future__ import annotations

try:
    # 优先走 user_profile 配置（Phase G 引入），兜底给通用占位
    from config import settings as _settings
    _USER = getattr(_settings, "user_profile", {}) or {}
except Exception:
    _USER = {}

_USER_NAME = _USER.get("name", "<你的姓名>")
_USER_SCHOOL = _USER.get("school", "<你的学校>")
_USER_MAJOR = _USER.get("major", "<你的专业>")
_USER_YEAR = _USER.get("graduation_year", "<届次>")
_USER_EMAIL = _USER.get("email", "<你的邮箱>")
_USER_HIGHLIGHTS = _USER.get("highlights", "<一句话概括你的核心亮点>")


# Boss直聘开场白 (≤50字)
BOSS_TEMPLATES = [
    "您好！我是 {school} {year} 届 {major} 专业，对 {position} 很感兴趣，方便聊聊吗？",
    "您好，{year} 届应届生。看到贵司 {position} 岗位，我的经历与要求很匹配，期待交流~",
    "您好！关注 {company} 很久了，对 {position} 很感兴趣，希望有机会进一步交流。",
]

# 脉脉私信
MAIMAI_TEMPLATES = [
    "{title}您好，看到您在 {company} 做 {direction}，我是 {year} 届 {major} 方向的，想请教几个问题，方便打扰吗？",
    "您好，我是 {school} {year} 届 {major} 专业的 {user_name}。对 {company} 的 {position} 非常感兴趣，想了解下团队情况，可以聊聊吗？",
]

# 邮件（正式）
EMAIL_TEMPLATES = [
    """主题：{year} 届应届生申请 {position} — {user_name}

{title}您好：

我是 {school} {major} 专业 {year} 届本科生 {user_name}，对 {company} {position} 岗位非常感兴趣。

核心经历：
{highlights}

已附简历，期待有机会进一步交流。

{user_name}
{user_email}""",
]

# 内推请求
REFERRAL_TEMPLATES = [
    """您好 {name}，冒昧打扰。

我是 {school} {year} 届 {major} 专业的 {user_name}，对 {company} 的 {position} 很感兴趣。
看到您在 {company} 工作，想请问是否方便帮忙内推？

我的核心优势：{highlights}
简历已准备好，可以随时发您。

非常感谢！""",
]


def _render(tpl: str, **kwargs) -> str:
    """统一 format，注入 user_profile 缺省值，缺字段时保留占位不报错。"""
    defaults = dict(
        school=_USER_SCHOOL,
        major=_USER_MAJOR,
        year=_USER_YEAR,
        user_name=_USER_NAME,
        user_email=_USER_EMAIL,
        highlights=_USER_HIGHLIGHTS,
    )
    defaults.update(kwargs)
    # 缺失字段兜底为 "<字段名>" 占位，不抛 KeyError
    class _SafeDict(dict):
        def __missing__(self, key):
            return "<" + key + ">"
    return tpl.format_map(_SafeDict(defaults))


def get_boss_message(company: str, position: str, template_idx: int = 0) -> str:
    idx = min(template_idx, len(BOSS_TEMPLATES) - 1)
    return _render(BOSS_TEMPLATES[idx], company=company, position=position)


def get_maimai_message(company: str, position: str, direction: str = "",
                       title: str = "老师", template_idx: int = 0) -> str:
    idx = min(template_idx, len(MAIMAI_TEMPLATES) - 1)
    return _render(MAIMAI_TEMPLATES[idx],
                   company=company, position=position,
                   direction=direction or "相关方向", title=title)


def get_email_message(company: str, position: str, title: str = "HR") -> str:
    return _render(EMAIL_TEMPLATES[0], company=company, position=position, title=title)


def get_referral_message(company: str, position: str, name: str = "") -> str:
    return _render(REFERRAL_TEMPLATES[0], company=company, position=position,
                   name=name or "前辈")


def get_all_templates(company: str, position: str) -> dict:
    """获取所有渠道的消息模板。"""
    return {
        "boss": [get_boss_message(company, position, i) for i in range(len(BOSS_TEMPLATES))],
        "maimai": [get_maimai_message(company, position, template_idx=i) for i in range(len(MAIMAI_TEMPLATES))],
        "email": [get_email_message(company, position)],
        "referral": [get_referral_message(company, position)],
    }
