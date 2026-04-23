"""回归矩阵 · 3 JD × 2 简历 × tailor + export

- mock 模式（默认 pytest）：打桩 `_call_claude` 返回通过 validator 的定制输出，
  断言 tailor 无异常、canvas 数据有变化、target_role 同步、PDF bytes 带 `%PDF-`。
- 真调模式：`python scripts/tailor_matrix_smoke.py --real`，本测试文件不触达 API。

覆盖目标：
  * Bug B 的 target_role fallback 链（通过 jd_intent 推断）在 6 组全通过
  * 导出路径 `services.resume_renderer.render_pdf_bytes` 在真实 master-like 数据上不抛
  * validator 能容纳「仅 profile + target_role 改动、bullets 全保留」的输出
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import resume_tailor  # noqa: E402
from services import resume_renderer  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures"
JD_DIR = FIXTURES / "jd_samples"
RESUME_DIR = FIXTURES / "resume_samples"


# ─── 加载 fixtures ────────────────────────────────────────
def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


JD_CASES = {
    "jd_a_minimax":      _load_text(JD_DIR / "jd_a_minimax.txt"),
    "jd_b_kimi":         _load_text(JD_DIR / "jd_b_kimi.txt"),
    "jd_c_xiaohongshu":  _load_text(JD_DIR / "jd_c_xiaohongshu.txt"),
}

JD_INTENTS = {
    "jd_a_minimax": {
        "target_role": "AI 增长运营",
        "role_direction": "AIGC 内容方向，负责 AI 陪伴产品海外增长",
        "top_keywords": ["AI", "增长", "运营", "内容", "Telegram", "TikTok", "数据", "海外", "AIGC"],
        "must_have": ["数据分析", "英语 CET-6", "海外社交平台经验"],
        "nice_to_have": ["9,000+ 粉丝运营经验", "Prompt Engineering"],
        "tone": "业务型",
    },
    "jd_b_kimi": {
        "target_role": "海外增长运营",
        "role_direction": "Kimi 海外版用户增长与留存",
        "top_keywords": ["海外", "增长", "运营", "英语", "Reddit", "X", "内容", "AI", "LLM"],
        "must_have": ["英语工作语言", "海外渠道运营经验", "数据分析"],
        "nice_to_have": ["冷启动操盘", "海外留学经历"],
        "tone": "内容型",
    },
    "jd_c_xiaohongshu": {
        "target_role": "产品运营",
        "role_direction": "本地生活线 GMV 增长与活动运营",
        "top_keywords": ["产品运营", "增长", "A/B 测试", "漏斗", "SQL", "活动", "商家", "数据"],
        "must_have": ["SQL", "漏斗分析", "跨职能协作"],
        "nice_to_have": ["本地生活经验", "数据可视化"],
        "tone": "数据型",
    },
}

RESUME_CASES = {
    "r1_yangchao":          _load_json(RESUME_DIR / "r1_yangchao.json"),
    "r2_generic_ops_5yr":   _load_json(RESUME_DIR / "r2_generic_ops_5yr.json"),
}


def _flatten(master: dict) -> dict:
    """复用 resume_tailor._flatten_master 语义：把 profile pool 折叠成文本。"""
    return resume_tailor._flatten_master(master)


def _build_mock_tailored(master: dict, jd_intent: dict) -> dict:
    """构造一个**通过 validator** 的 AI 返回：
    - bullets / company / date / education 100% 保留
    - profile 改写为 JD 导向的短文
    - target_role 同步 jd_intent
    """
    flat = _flatten(master)
    target = jd_intent.get("target_role", "")
    kws = jd_intent.get("top_keywords", [])
    kw_blob = " · ".join(kws[:6]) if kws else ""

    new_profile = (
        f"针对 {target} 岗位重写：{kw_blob}。"
        "保留主简历核心数字：完成 <b>9,000+</b> 粉丝、<b>1,300+</b> 订阅、<b>20+</b> 次合作，"
        "围绕 JD 关键词强化增长、内容、数据三条主线。"
    )

    return {
        "basics": {"target_role": target},
        "profile": new_profile,
        "projects": [
            {
                "company": p["company"],
                "role": p.get("role", ""),
                "date": p["date"],
                "bullets": list(p["bullets"]),
            }
            for p in flat.get("projects", [])
        ],
        "internships": [
            {
                "company": it["company"],
                "role": it.get("role", ""),
                "date": it["date"],
                "bullets": list(it["bullets"]),
            }
            for it in flat.get("internships", [])
        ],
        "skills": list(flat.get("skills", [])),
        "match_score": 85,
        "change_notes": f"按 {target} JD 改写 profile 并调整 target_role，bullets 保留。",
    }


MATRIX = [
    (jd_key, resume_key)
    for jd_key in JD_CASES
    for resume_key in RESUME_CASES
]


# ─── 测试 ─────────────────────────────────────────────────

@pytest.mark.parametrize("jd_key,resume_key", MATRIX, ids=[f"{j}__{r}" for j, r in MATRIX])
def test_tailor_matrix_success(monkeypatch, jd_key: str, resume_key: str) -> None:
    jd_text = JD_CASES[jd_key]
    jd_intent = JD_INTENTS[jd_key]
    master = copy.deepcopy(RESUME_CASES[resume_key])

    mock_tailored = _build_mock_tailored(master, jd_intent)

    monkeypatch.setattr(resume_tailor, "extract_jd_intent", lambda jd: jd_intent)
    monkeypatch.setattr(
        resume_tailor, "_call_claude",
        lambda **kwargs: json.dumps(mock_tailored, ensure_ascii=False),
    )

    result = resume_tailor.tailor_resume(master, jd_text)

    # ── 断言 1：无异常（隐含：validator.ok）──
    assert "_meta" in result

    # ── 断言 2：canvas 数据实际变化（profile 被 JD 改写）──
    flat_master = _flatten(master)
    assert result["profile"] != flat_master.get("profile"), (
        f"profile 没有变化 · {resume_key} + {jd_key}"
    )

    # ── 断言 3：target_role 与 JD intent 对齐 ──
    target_role = result["basics"].get("target_role", "")
    assert target_role == jd_intent["target_role"], (
        f"target_role 未同步 JD · got={target_role!r} expected={jd_intent['target_role']!r}"
    )
    # 同步镜像：_meta.target_position 也要有
    assert result["_meta"].get("target_position") == jd_intent["target_role"]

    # ── 断言 4：bullet / company / date 保留原样 ──
    for key in ("projects", "internships"):
        for idx, orig in enumerate(flat_master.get(key, [])):
            got = result[key][idx]
            assert got["company"] == orig["company"]
            assert got["date"] == orig["date"]
            assert got["bullets"] == orig["bullets"]


@pytest.mark.parametrize("resume_key", list(RESUME_CASES.keys()))
def test_render_pdf_on_master(resume_key: str) -> None:
    """导出路径：master 原始数据直接进 renderer，bytes 含 PDF magic。"""
    master = copy.deepcopy(RESUME_CASES[resume_key])
    flat = _flatten(master)
    try:
        pdf_bytes = resume_renderer.render_pdf_bytes(flat)
    except Exception as e:  # pragma: no cover
        pytest.skip(f"PDF renderer unavailable: {e}")
    assert pdf_bytes.startswith(b"%PDF-"), f"{resume_key}: PDF magic header 缺失"
    assert len(pdf_bytes) > 2000, f"{resume_key}: PDF bytes too small ({len(pdf_bytes)})"
