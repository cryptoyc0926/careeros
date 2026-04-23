"""CLI · 3 JD × 2 简历矩阵的**真调** smoke runner。

用法：
    python scripts/tailor_matrix_smoke.py --real     # 真调 Claude API
    python scripts/tailor_matrix_smoke.py            # dry-run（显示计划，不调用）

与 `web/tests/test_tailor_matrix.py` 的区别：
  - pytest 文件 mock `_call_claude`，只校验流水线 / export 格式；
  - 本 CLI 真调 API，产出 `reports/tailor_matrix_YYYYMMDD/` 下的 6 份 PDF + 6 份 JSON，
    供肉眼抽检与对齐 Bug A/B/C 的真实表现。

注意：
  - 真调会消耗 Claude API 配额（6 组 × 2 次调用 ≈ 12 次 `_call_claude`）
  - 默认不跑，必须传 `--real`
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
sys.path.insert(0, str(WEB))

from services import resume_tailor  # noqa: E402
from services import resume_renderer  # noqa: E402
from services.resume_validator import ValidationError  # noqa: E402


FIXTURES = WEB / "tests" / "fixtures"
JD_DIR = FIXTURES / "jd_samples"
RESUME_DIR = FIXTURES / "resume_samples"


def _load_all() -> tuple[dict[str, str], dict[str, dict]]:
    jds = {p.stem: p.read_text(encoding="utf-8") for p in sorted(JD_DIR.glob("*.txt"))}
    resumes = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESUME_DIR.glob("*.json"))}
    return jds, resumes


def _run_one(
    out_dir: Path, jd_key: str, jd_text: str, resume_key: str, master: dict
) -> dict:
    label = f"{resume_key}__{jd_key}"
    row: dict = {"label": label, "ok": False, "error": ""}
    t0 = time.monotonic()
    try:
        result = resume_tailor.tailor_resume(master, jd_text)
        dt = time.monotonic() - t0
        row["ms"] = int(dt * 1000)
        row["target_role"] = result["basics"].get("target_role", "")
        row["match_score"] = result["_meta"].get("match_score", 0)
        row["change_notes"] = result["_meta"].get("change_notes", "")

        data_path = out_dir / f"{label}.json"
        data_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        row["json_path"] = str(data_path)

        # 导出 PDF
        try:
            pdf_bytes = resume_renderer.render_pdf_bytes(result)
            pdf_path = out_dir / f"{label}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            row["pdf_bytes"] = len(pdf_bytes)
            row["pdf_path"] = str(pdf_path)
            row["pdf_magic_ok"] = pdf_bytes.startswith(b"%PDF-")
        except Exception as exp:
            row["pdf_error"] = f"{type(exp).__name__}: {exp}"

        row["ok"] = True
    except ValidationError as e:
        row["error"] = f"ValidationError · {len(e.report.hard_errors)} hard · {len(e.report.warnings)} warn"
        if e.draft:
            (out_dir / f"{label}.draft.json").write_text(
                json.dumps(e.draft, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="actually call Claude API (costs tokens)")
    ap.add_argument(
        "--out",
        default=str(ROOT / "reports" / f"tailor_matrix_{time.strftime('%Y%m%d')}"),
        help="output dir for JSON + PDF artifacts",
    )
    args = ap.parse_args()

    jds, resumes = _load_all()
    pairs = [(j, r) for j in jds for r in resumes]

    if not args.real:
        print("Dry-run · 6 组 tailor 计划（传 --real 真调）：")
        for j, r in pairs:
            print(f"  · {r} × {j}")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Real-mode · artifacts → {out_dir}")

    rows: list[dict] = []
    for jd_key, resume_key in pairs:
        print(f"[run] {resume_key} × {jd_key} ...", flush=True)
        row = _run_one(
            out_dir, jd_key, jds[jd_key], resume_key,
            copy.deepcopy(resumes[resume_key]),
        )
        rows.append(row)
        status = "OK" if row["ok"] else "FAIL"
        print(f"  → {status}  ms={row.get('ms','?')}  target={row.get('target_role','?')}  err={row.get('error','')}")

    summary_path = out_dir / "_summary.json"
    summary_path.write_text(
        json.dumps({"pairs": len(pairs), "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Summary written → {summary_path}")

    ok_count = sum(1 for r in rows if r["ok"])
    print(f"Done · {ok_count}/{len(rows)} OK")
    return 0 if ok_count == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
