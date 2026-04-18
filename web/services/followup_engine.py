"""
Follow-up 多渠道提醒引擎
~~~~~~~~~~~~~~~~~~~~~~~
6 渠道差异化节奏 + 紧急度计算 + AI 话术生成
"""

from __future__ import annotations

from datetime import datetime, timedelta
from models.database import query

# 各渠道跟进节奏 (天数列表)
CHANNEL_CADENCE = {
    "boss":    [1, 3, 7],
    "email":   [3, 7, 14],
    "referral": [2, 5],
    "portal":  [],       # 门户无法主动跟进
    "maimai":  [3],
    "wechat":  [3, 7],
}

CHANNEL_LABELS = {
    "boss": "Boss直聘",
    "email": "邮件",
    "referral": "内推",
    "portal": "校招门户",
    "maimai": "脉脉",
    "wechat": "企业微信",
}

# 紧急度分级
URGENCY_LEVELS = {
    "urgent": "紧急",
    "overdue": "逾期",
    "upcoming": "即将",
    "waiting": "等待中",
    "done": "已完成",
}
URGENCY_VARIANT = {
    "urgent": "danger",
    "overdue": "warning",
    "upcoming": "warning",
    "waiting": "info",
    "done": "muted",
}


def _days_since(date_str: str) -> int:
    """计算距今天数。"""
    if not date_str:
        return 999
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.now() - d).days
    except (ValueError, TypeError):
        return 999


def get_next_followup_day(channel: str, followup_count: int) -> int | None:
    """获取下一次跟进的天数（距投递日）。None 表示不需要跟进。"""
    cadence = CHANNEL_CADENCE.get(channel, [])
    if followup_count >= len(cadence):
        return None
    return cadence[followup_count]


def calculate_urgency(applied_date: str, channel: str, followup_count: int) -> str:
    """计算跟进紧急度。"""
    next_day = get_next_followup_day(channel, followup_count)
    if next_day is None:
        return "done"

    days_elapsed = _days_since(applied_date)
    gap = next_day - days_elapsed

    if gap < 0:
        return "urgent" if abs(gap) >= 3 else "overdue"
    elif gap == 0:
        return "urgent"
    elif gap <= 2:
        return "upcoming"
    return "waiting"


def get_pending_followups() -> list[dict]:
    """获取所有待跟进的岗位，按紧急度排序。"""
    rows = query(
        """SELECT id, 公司, 岗位名称, 城市, applied_date, apply_channel,
                  last_followup, followup_count, status
           FROM jobs_pool
           WHERE status = '已投递'
             AND apply_channel IS NOT NULL
             AND apply_channel != 'portal'
           ORDER BY applied_date ASC"""
    )

    results = []
    for r in rows:
        channel = r.get("apply_channel", "")
        count = r.get("followup_count", 0) or 0
        urgency = calculate_urgency(r["applied_date"], channel, count)

        if urgency == "done":
            continue

        next_day = get_next_followup_day(channel, count)
        days_elapsed = _days_since(r["applied_date"])

        results.append({
            **r,
            "urgency": urgency,
            "urgency_label": URGENCY_LEVELS[urgency],
            "channel_label": CHANNEL_LABELS.get(channel, channel),
            "days_elapsed": days_elapsed,
            "next_followup_day": next_day,
            "days_until_next": (next_day - days_elapsed) if next_day else None,
        })

    # 按紧急度排序: urgent > overdue > upcoming > waiting
    order = {"urgent": 0, "overdue": 1, "upcoming": 2, "waiting": 3}
    results.sort(key=lambda x: order.get(x["urgency"], 9))
    return results


def generate_followup_message(company: str, position: str, channel: str,
                              followup_count: int, days_elapsed: int) -> str:
    """生成跟进话术（不调用 AI，使用模板）。"""
    round_num = followup_count + 1

    if channel == "boss":
        templates = [
            f"您好，之前投递了贵司{position}岗位，想确认下简历是否收到？方便的话聊聊~",
            f"您好，补充说明下——我在AI社区运营方面有从0到9K粉丝的实战经验，和{position}很匹配。如果有面试机会请告知~",
            f"冒昧再打扰一下，请问{position}还在招聘中吗？如果有其他合适的岗位也很感兴趣。",
        ]
    elif channel == "email":
        templates = [
            f"您好，我于{days_elapsed}天前投递了{company}{position}岗位，想确认申请状态。附件为最新简历，期待回复。",
            f"再次跟进{position}申请。我在AI增长运营方向有深度实践经验，非常期待有机会加入{company}团队。",
            f"最后一次跟进{position}岗位申请。如暂无合适机会，也希望保持联系，未来有合适岗位时优先考虑。",
        ]
    elif channel == "referral":
        templates = [
            f"感谢推荐{company}的{position}！想了解下流程大概多久会有反馈？",
            f"请问{position}的面试流程推进到哪一步了？有什么需要我准备的吗？",
        ]
    elif channel == "maimai":
        templates = [
            f"您好，之前在Boss直聘投递了{company}{position}，想请教下这个岗位目前的招聘进展？",
        ]
    elif channel == "wechat":
        templates = [
            f"老师您好，想跟进下{position}的面试安排，方便时回复即可~",
            f"再次跟进{position}申请，如需补充任何材料请告知，谢谢！",
        ]
    else:
        return f"跟进{company} {position}岗位申请（第{round_num}次）"

    idx = min(followup_count, len(templates) - 1)
    return templates[idx]
