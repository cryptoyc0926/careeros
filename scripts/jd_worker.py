"""JD 抓取后台 worker（Phase A：纯 Python，只跑 auto 模式）。

用法：
    # 跑一批 pending 任务（默认 20 条）
    python scripts/jd_worker.py run

    # 跑单条
    python scripts/jd_worker.py one <job_pool_id>

    # 查看队列统计
    python scripts/jd_worker.py stats

    # 按 URL 重新分类所有 jobs_pool 行的 jd_fetch_mode
    python scripts/jd_worker.py classify

Phase B（browser 模式，需 Chrome MCP）不在这里跑，
留给 Claude session 内联处理（在 job_pool 页点「Chrome 抓取」按钮触发）。
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

# 让脚本能 import web.services
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

from config import settings
from services.jd_fetcher import fetch_and_save, classify_mode

DB_PATH = settings.db_full_path
BATCH = 20
SLEEP_BETWEEN = 2  # 秒，温柔点别被封


def stats() -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT jd_fetch_mode, jd_status, COUNT(*) AS c
           FROM jobs_pool GROUP BY jd_fetch_mode, jd_status
           ORDER BY jd_fetch_mode, jd_status"""
    ).fetchall()
    conn.close()
    print(f"{'mode':<10} {'status':<15} {'count':>5}")
    print("-" * 32)
    for mode, status, c in rows:
        print(f"{mode or '-':<10} {status or '-':<15} {c:>5}")


def classify_all() -> None:
    """按 URL 重新给 jobs_pool 所有行打 jd_fetch_mode 标签。"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT id, "链接", "公司" FROM jobs_pool').fetchall()
    updated = 0
    for jid, url, company in rows:
        mode = classify_mode(url or "", company or "")
        conn.execute(
            "UPDATE jobs_pool SET jd_fetch_mode=? WHERE id=?",
            (mode, jid),
        )
        updated += 1
    conn.commit()
    conn.close()
    print(f"✅ classify done: {updated} rows")
    stats()


def run_one(job_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT 链接, jd_fetch_mode, 公司, 岗位名称 FROM jobs_pool WHERE id=?',
        (job_id,),
    ).fetchone()
    conn.close()
    if not row:
        print(f"❌ job_pool_id={job_id} not found")
        return

    url, mode, company, title = row
    print(f"[{job_id}] {company} / {title} mode={mode}")
    print(f"   url: {url}")

    if mode != "auto":
        print(f"   ⏭  skip (mode={mode})")
        return
    if not url or not url.startswith("http"):
        print(f"   ⏭  skip (invalid url)")
        return

    r = fetch_and_save(job_id, url)
    if r.ok:
        print(f"   ✅ {r.adapter_name} · {len(r.raw_text)} 字")
    else:
        print(f"   ❌ {r.adapter_name}: {r.error}")


def run_batch(limit: int = BATCH) -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT id, "链接", "公司", "岗位名称" FROM jobs_pool
           WHERE jd_fetch_mode='auto'
             AND (jd_status IS NULL OR jd_status='pending')
             AND "链接" LIKE 'http%'
           ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        print("🎉 队列空，没有 auto/pending 任务")
        return

    print(f"▶  开始处理 {len(rows)} 条 auto 任务（每条间隔 {SLEEP_BETWEEN}s）")
    ok_cnt = fail_cnt = 0
    for i, (jid, url, company, title) in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] #{jid} {company} / {title}")
        try:
            r = fetch_and_save(jid, url)
            if r.ok:
                print(f"   ✅ {r.adapter_name} · {len(r.raw_text)} 字")
                ok_cnt += 1
            else:
                print(f"   ❌ {r.adapter_name}: {r.error[:100]}")
                fail_cnt += 1
        except Exception as e:
            print(f"   💥 exception: {e}")
            fail_cnt += 1
        time.sleep(SLEEP_BETWEEN)

    print(f"\n─── 汇总 ───")
    print(f"  成功: {ok_cnt}")
    print(f"  失败: {fail_cnt}")
    stats()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "stats":
        stats()
    elif cmd == "classify":
        classify_all()
    elif cmd == "one":
        run_one(int(sys.argv[2]))
    elif cmd == "run":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH
        run_batch(n)
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
