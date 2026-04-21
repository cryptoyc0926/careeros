"""
Resume JSON Patch — 简历字段级增量修改
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

用于 chat 驱动的简历定制。LLM 输出 patch 数组，由本模块安全应用到 tailor_data 上。

Patch 操作（op）:
  - replace:  替换某个字段值
  - add:      插入新值（list 追加 / dict 新字段）
  - remove:   删除某个字段（用于 bullets 减项等，但默认禁止删硬事实）
  - reorder:  列表重排序，value=新索引序列

Path 语法（JSONPath 简化版）:
  - "profile"                       → data["profile"]
  - "projects[0].bullets[2]"        → data["projects"][0]["bullets"][2]
  - "skills[1].text"                → data["skills"][1]["text"]
  - "basics.target_role"            → data["basics"]["target_role"]

使用::
    from services.resume_patch import apply_patch, diff_fields

    new_data, errors = apply_patch(old_data, [
        {"op": "replace", "path": "profile", "value": "新总结..."},
        {"op": "replace", "path": "projects[0].bullets[2]", "value": "新 bullet"},
    ])
    if errors:
        # 至少一步失败 → 整体回滚，new_data == old_data
        ...
"""

from __future__ import annotations

import copy
import re
from typing import Any

_PATH_TOKEN_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _parse_path(path: str) -> list[str | int]:
    """
    "projects[0].bullets[2]" → ["projects", 0, "bullets", 2]
    """
    tokens: list[str | int] = []
    for m in _PATH_TOKEN_RE.finditer(path):
        key, idx = m.group(1), m.group(2)
        if key is not None:
            tokens.append(key)
        elif idx is not None:
            tokens.append(int(idx))
    if not tokens:
        raise ValueError(f"invalid path: {path!r}")
    return tokens


def _resolve_parent(root: Any, tokens: list[str | int]) -> tuple[Any, str | int]:
    """沿路径走到倒数第二层，返回 (parent, last_key)。"""
    cur = root
    for t in tokens[:-1]:
        if isinstance(t, int):
            if not isinstance(cur, list) or t >= len(cur) or t < -len(cur):
                raise KeyError(f"index {t} out of range at {cur!r}")
            cur = cur[t]
        else:
            if not isinstance(cur, dict) or t not in cur:
                raise KeyError(f"key {t!r} not found")
            cur = cur[t]
    return cur, tokens[-1]


def get_by_path(root: Any, path: str) -> Any:
    tokens = _parse_path(path)
    parent, last = _resolve_parent(root, tokens)
    if isinstance(last, int):
        return parent[last]
    return parent[last]


def _apply_one(root: Any, op: str, path: str, value: Any) -> None:
    tokens = _parse_path(path)
    parent, last = _resolve_parent(root, tokens)

    if op == "replace":
        if isinstance(last, int):
            parent[last] = value
        else:
            parent[last] = value
    elif op == "add":
        if isinstance(last, int):
            if not isinstance(parent, list):
                raise TypeError("add with int path needs list parent")
            parent.insert(last, value)
        else:
            if not isinstance(parent, dict):
                raise TypeError("add with key path needs dict parent")
            parent[last] = value
    elif op == "remove":
        if isinstance(last, int):
            del parent[last]
        else:
            parent.pop(last, None)
    elif op == "reorder":
        # value 是新顺序的索引列表，针对 parent[last]（必须是 list）
        if isinstance(last, int):
            target = parent[last]
        else:
            target = parent[last]
        if not isinstance(target, list):
            raise TypeError("reorder target must be list")
        if not isinstance(value, list) or sorted(value) != list(range(len(target))):
            raise ValueError("reorder value must be permutation of indices")
        new = [target[i] for i in value]
        if isinstance(last, int):
            parent[last] = new
        else:
            parent[last] = new
    else:
        raise ValueError(f"unknown op: {op!r}")


def apply_patch(
    data: dict[str, Any],
    patch: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    对 data 深拷贝后批量应用 patch。任何一步失败 → 整体回滚，返回原 data 副本 + 错误列表。
    """
    errors: list[str] = []
    if not patch:
        return copy.deepcopy(data), errors
    snapshot = copy.deepcopy(data)
    working = copy.deepcopy(data)
    for i, p in enumerate(patch):
        try:
            op = p.get("op")
            path = p.get("path")
            value = p.get("value")
            if not op or not path:
                raise ValueError(f"patch[{i}] 缺少 op / path")
            _apply_one(working, op, path, value)
        except Exception as e:
            errors.append(f"patch[{i}] {p!r} → {type(e).__name__}: {e}")
    if errors:
        return snapshot, errors
    return working, errors


# ─────────────────────────────────────────────
# 字段级 diff（用于 chat 里显示"改了哪里"）
# ─────────────────────────────────────────────


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """把嵌套 dict/list 压成 {'projects[0].bullets[2]': 'text', ...}。"""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            out.update(_flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.update(_flatten(v, key))
    else:
        out[prefix] = obj
    return out


def diff_fields(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """
    返回两份简历之间变化的字段列表：
      [{"path": "...", "old": "...", "new": "...", "kind": "changed|added|removed"}, ...]
    """
    fo = _flatten(old)
    fn = _flatten(new)
    keys = set(fo) | set(fn)
    changes: list[dict[str, Any]] = []
    for k in sorted(keys):
        ov, nv = fo.get(k, _MISSING), fn.get(k, _MISSING)
        if ov is _MISSING and nv is not _MISSING:
            changes.append({"path": k, "old": None, "new": nv, "kind": "added"})
        elif nv is _MISSING and ov is not _MISSING:
            changes.append({"path": k, "old": ov, "new": None, "kind": "removed"})
        elif ov != nv:
            changes.append({"path": k, "old": ov, "new": nv, "kind": "changed"})
    return changes


class _Missing:
    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _Missing()


# ─────────────────────────────────────────────
# 自测
# ─────────────────────────────────────────────
if __name__ == "__main__":
    data = {
        "profile": "原总结",
        "projects": [
            {"company": "A", "bullets": ["b0", "b1", "b2"]},
            {"company": "B", "bullets": ["x0"]},
        ],
        "skills": [{"label": "工具", "text": "Python"}],
    }
    patch = [
        {"op": "replace", "path": "profile", "value": "新总结"},
        {"op": "replace", "path": "projects[0].bullets[2]", "value": "改过的 b2"},
    ]
    new, errs = apply_patch(data, patch)
    assert not errs, errs
    assert new["profile"] == "新总结"
    assert new["projects"][0]["bullets"][2] == "改过的 b2"
    assert data["profile"] == "原总结"  # 原件未动
    changes = diff_fields(data, new)
    print("changes:", changes)
    print("[OK] resume_patch self-test passed")
