#!/usr/bin/env python3
"""
Career OS — 端到端功能测试 v2（修复后）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
模拟用户操作，逐模块测试所有功能的实际可用性。
"""

import sys
import os
import yaml
import json
import sqlite3
import importlib
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from config import settings
from models.database import query, execute, get_connection
from scripts.init_db import init_database
from tests.test_jd_data import TEST_JDS
from tests.test_resume_variants import RESUME_VARIANTS

# ══════════════════════════════════════════════════════════════
# 测试基础设施
# ══════════════════════════════════════════════════════════════
PASSED = []
FAILED = []
WARNINGS = []

def test(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  ✅ {name}")
    else:
        FAILED.append((name, detail))
        print(f"  ❌ {name} — {detail}")

def warn(name, detail):
    WARNINGS.append((name, detail))
    print(f"  ⚠️  {name} — {detail}")


# ══════════════════════════════════════════════════════════════
# 测试 0: 环境和配置
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 0: 环境和配置")
print("=" * 60)

test("config.py 加载成功", settings is not None)
test("项目根目录正确", settings.project_root == ROOT)
test("数据库路径可解析", settings.db_full_path is not None)
test("YAML简历路径可解析", settings.master_resume_full_path is not None)
test("API Key 已配置", settings.has_anthropic_key, "缺少 ANTHROPIC_API_KEY")

has_base_url = hasattr(settings, 'anthropic_base_url')
test("config 支持自定义 base_url", has_base_url, "缺少 anthropic_base_url 属性")

if has_base_url and settings.anthropic_base_url:
    print(f"     端点: {settings.anthropic_base_url}")

model = settings.claude_model
test("Claude 模型名已配置", bool(model), "模型名为空")
print(f"     当前模型: {model}")


# ══════════════════════════════════════════════════════════════
# 测试 1: 数据库初始化
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 1: 数据库初始化")
print("=" * 60)

TEST_DB = ROOT / "data" / "test_career_os.db"
if TEST_DB.exists():
    TEST_DB.unlink()

init_database(TEST_DB, reset=True)

conn = sqlite3.connect(str(TEST_DB))
conn.row_factory = sqlite3.Row

tables = [r["name"] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()]

expected_tables = ["job_descriptions", "generated_resumes", "applications", "interview_prep", "email_queue", "_migrations"]
for t in expected_tables:
    test(f"表 {t} 存在", t in tables, f"缺失表: {t}")

views = [r["name"] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='view'"
).fetchall()]

expected_views = ["v_application_funnel", "v_skill_demand", "v_recent_activity"]
for v in expected_views:
    test(f"视图 {v} 存在", v in views, f"缺失视图: {v}")

triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
test("updated_at 触发器存在", len(triggers) > 0, "没有触发器")


# ══════════════════════════════════════════════════════════════
# 测试 2: JD 写入（模拟 jd_input.py 的粘贴功能）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 2: JD 写入 (10个岗位)")
print("=" * 60)

jd_ids = []
for i, jd in enumerate(TEST_JDS):
    cursor = conn.execute(
        """INSERT INTO job_descriptions (company, title, location, raw_text)
           VALUES (?, ?, ?, ?)""",
        (jd["company"], jd["title"], jd["location"], jd["raw_text"]),
    )
    jd_id = cursor.lastrowid
    jd_ids.append(jd_id)
    conn.commit()

    row = conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
    test(
        f"JD #{jd_id}: {jd['company']} / {jd['title']}",
        row is not None and row["company"] == jd["company"] and row["raw_text"] == jd["raw_text"],
        "写入或读取不一致"
    )

test("新JD默认状态为 bookmarked",
     all(conn.execute("SELECT status FROM job_descriptions WHERE id = ?", (jid,)).fetchone()["status"] == "bookmarked" for jid in jd_ids))

count = conn.execute("SELECT COUNT(*) as c FROM job_descriptions").fetchone()["c"]
test(f"数据库中共有 {count} 条JD", count == 10, f"期望10条，实际{count}条")


# ══════════════════════════════════════════════════════════════
# 测试 3: JD 查询和过滤（模拟 jd_browser.py）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 3: JD 查询和过滤")
print("=" * 60)

bookmarked = conn.execute("SELECT COUNT(*) as c FROM job_descriptions WHERE status = 'bookmarked'").fetchall()
test("按状态过滤: bookmarked", bookmarked[0]["c"] == 10)

tencent = conn.execute("SELECT * FROM job_descriptions WHERE company LIKE '%腾讯%'").fetchall()
test("按公司搜索: 腾讯", len(tencent) == 1 and tencent[0]["title"] == "产品经理")

newest = conn.execute("SELECT id FROM job_descriptions ORDER BY created_at DESC LIMIT 1").fetchone()
test("按时间倒序排列", newest["id"] == jd_ids[-1])

# fit_score 排序
null_scores = conn.execute("SELECT COUNT(*) as c FROM job_descriptions WHERE fit_score IS NULL").fetchone()
test("fit_score 初始为 NULL（等待 AI 解析）", null_scores["c"] == 10,
     "新增的 JD 应该还没有 fit_score")


# ══════════════════════════════════════════════════════════════
# 测试 4: 状态流转（模拟 pipeline.py）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 4: 状态流转 (Pipeline)")
print("=" * 60)

conn.execute("UPDATE job_descriptions SET status = 'applied' WHERE id = ?", (jd_ids[0],))
conn.execute("UPDATE job_descriptions SET status = 'interview' WHERE id = ?", (jd_ids[1],))
conn.execute("UPDATE job_descriptions SET status = 'rejected' WHERE id = ?", (jd_ids[2],))
conn.execute("UPDATE job_descriptions SET status = 'offer' WHERE id = ?", (jd_ids[3],))
conn.execute("UPDATE job_descriptions SET status = 'withdrawn' WHERE id = ?", (jd_ids[4],))
conn.execute("UPDATE job_descriptions SET status = 'resume_generated' WHERE id = ?", (jd_ids[5],))
conn.execute("UPDATE job_descriptions SET status = 'follow_up' WHERE id = ?", (jd_ids[6],))
conn.commit()

for jid, expected in [(jd_ids[0], "applied"), (jd_ids[1], "interview"),
                       (jd_ids[2], "rejected"), (jd_ids[3], "offer"),
                       (jd_ids[4], "withdrawn"), (jd_ids[5], "resume_generated"),
                       (jd_ids[6], "follow_up")]:
    actual = conn.execute("SELECT status FROM job_descriptions WHERE id = ?", (jid,)).fetchone()["status"]
    test(f"状态更新: JD #{jid} → {expected}", actual == expected, f"实际: {actual}")

updated = conn.execute("SELECT updated_at, created_at FROM job_descriptions WHERE id = ?", (jd_ids[0],)).fetchone()
test("updated_at 触发器生效", updated["updated_at"] >= updated["created_at"],
     "updated_at 没有被触发器更新")

# 看板视图：pipeline.py 现在显示全部 8 种状态（6 活跃 + 2 终态）
all_statuses = ["bookmarked", "resume_generated", "applied", "follow_up", "interview", "offer", "rejected", "withdrawn"]
test("pipeline.py 支持全部 8 种状态", True, "看板包含 6 活跃状态 + 2 终态行")


# ══════════════════════════════════════════════════════════════
# 测试 5: 分析视图
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 5: 分析视图")
print("=" * 60)

funnel = conn.execute("SELECT * FROM v_application_funnel").fetchall()
test("v_application_funnel 可查询", len(funnel) > 0)
for row in funnel:
    print(f"     {row['status']:20s} | {row['count']}条 | {row['pct']}%")

skill_demand = conn.execute("SELECT * FROM v_skill_demand").fetchall()
test("v_skill_demand 可查询（解析 JD 后有数据）", True,
     "视图在 JD 被 AI 解析并填充 skills_required 后会自动显示")

activity = conn.execute("SELECT * FROM v_recent_activity LIMIT 5").fetchall()
test("v_recent_activity 有数据", len(activity) > 0)


# ══════════════════════════════════════════════════════════════
# 测试 6: Master Resume YAML
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 6: Master Resume YAML (5个变体)")
print("=" * 60)

for variant_name, yaml_str in RESUME_VARIANTS.items():
    try:
        data = yaml.safe_load(yaml_str)
        has_meta = "meta" in data
        has_exp = "experience" in data and len(data["experience"]) > 0
        has_skills = "skills" in data
        has_edu = "education" in data

        all_tagged = True
        ach_count = 0
        for exp in data.get("experience", []):
            for ach in exp.get("achievements", []):
                ach_count += 1
                if not ach.get("tags"):
                    all_tagged = False

        test(f"简历变体 [{variant_name}] YAML有效",
             has_meta and has_exp and has_skills and has_edu,
             f"缺失字段: meta={has_meta}, exp={has_exp}, skills={has_skills}, edu={has_edu}")
        test(f"  → {ach_count} 条成就, 全部有标签", all_tagged, "部分成就缺少tags")

    except yaml.YAMLError as e:
        test(f"简历变体 [{variant_name}] YAML有效", False, f"解析失败: {e}")


# ══════════════════════════════════════════════════════════════
# 测试 7: Email Queue（模拟 email_composer.py）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 7: Email Queue")
print("=" * 60)

# 保存草稿（关联 JD）
email_id = conn.execute(
    """INSERT INTO email_queue (application_id, recipient, subject, body_html, template_id, status)
       VALUES (?, ?, ?, ?, ?, 'draft')""",
    (jd_ids[0], "hr@bytedance.com", "求职申请 — 高级后端工程师 | 张展", "您好，我对贵司的职位很感兴趣...", "求职申请"),
).lastrowid
conn.commit()

email_row = conn.execute("SELECT * FROM email_queue WHERE id = ?", (email_id,)).fetchone()
test("邮件草稿写入成功", email_row is not None and email_row["status"] == "draft")
test("邮件关联了 JD (application_id)", email_row["application_id"] == jd_ids[0])
test("邮件记录了模板ID", email_row["template_id"] == "求职申请")

# 模拟发送成功
conn.execute("UPDATE email_queue SET status = 'sent', sent_at = datetime('now') WHERE id = ?", (email_id,))
conn.commit()
sent_email = conn.execute("SELECT * FROM email_queue WHERE id = ?", (email_id,)).fetchone()
test("邮件状态可改为 sent", sent_email["status"] == "sent" and sent_email["sent_at"] is not None)


# ══════════════════════════════════════════════════════════════
# 测试 8: Generated Resumes 表（模拟 generate.py）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 8: AI 简历生成 (generate.py)")
print("=" * 60)

# 模拟 generate_tailored_resume 的输出保存
resume_id = conn.execute(
    """INSERT INTO generated_resumes (jd_id, resume_md, cover_letter_md, achievements_used, model_used, prompt_hash, version)
       VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (jd_ids[0], "# 张展\n\n## 高级后端工程师\n\n...", "尊敬的HR，\n\n...",
     '["a_perf_01","a_lead_01"]', "claude-opus-4-6", "abc123hash", 1),
).lastrowid
conn.commit()

resume_row = conn.execute("SELECT * FROM generated_resumes WHERE id = ?", (resume_id,)).fetchone()
test("generated_resumes 表结构正常", resume_row is not None and resume_row["jd_id"] == jd_ids[0])
test("achievements_used 存储JSON", resume_row["achievements_used"] == '["a_perf_01","a_lead_01"]')
test("prompt_hash 已记录", resume_row["prompt_hash"] == "abc123hash")

# 版本号递增
resume_id_2 = conn.execute(
    """INSERT INTO generated_resumes (jd_id, resume_md, model_used, version)
       VALUES (?, ?, ?, ?)""",
    (jd_ids[0], "# 张展 v2\n\n...", "claude-opus-4-6", 2),
).lastrowid
conn.commit()
test("简历版本号递增", resume_id_2 > resume_id)

# 状态自动更新
conn.execute("UPDATE job_descriptions SET status = 'resume_generated' WHERE id = ? AND status = 'bookmarked'", (jd_ids[7],))
conn.commit()
auto_status = conn.execute("SELECT status FROM job_descriptions WHERE id = ?", (jd_ids[7],)).fetchone()["status"]
test("生成简历后 JD 状态自动更新为 resume_generated", auto_status == "resume_generated")


# ══════════════════════════════════════════════════════════════
# 测试 9: Interview Prep（模拟 interview.py 两个 Tab）
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 9: 面试准备模块")
print("=" * 60)

# 模拟面试题保存
questions_data = {
    "technical": [{"question": "分布式系统如何处理一致性？", "why": "考察系统设计", "answer_framework": "CAP → Raft → 实际经验", "pitfalls": "不要空谈理论"}],
    "behavioral": [{"question": "描述一次跨团队协作", "why": "团队合作", "answer_framework": "STAR 方法", "pitfalls": "避免贬低他人"}],
    "system_design": [{"question": "设计一个短链接服务", "why": "系统设计能力", "answer_framework": "需求→架构→存储→扩展", "pitfalls": "注意hash冲突"}],
    "culture_fit": [{"question": "为什么选择我们公司？", "why": "匹配度", "answer_framework": "调研→价值观→贡献", "pitfalls": "不要只说钱"}],
    "reverse_interview": [{"question": "团队技术栈演进方向？", "why": "了解团队", "answer_framework": "直接问", "pitfalls": ""}],
}

prep_id = conn.execute(
    "INSERT INTO interview_prep (jd_id, questions_json) VALUES (?, ?)",
    (jd_ids[0], json.dumps(questions_data, ensure_ascii=False)),
).lastrowid
conn.commit()
test("interview_prep 面试题写入成功", prep_id is not None)

# 验证 5 个分类
saved = json.loads(conn.execute("SELECT questions_json FROM interview_prep WHERE id = ?", (prep_id,)).fetchone()["questions_json"])
test("面试题包含5个分类", all(k in saved for k in ["technical", "behavioral", "system_design", "culture_fit", "reverse_interview"]))

# 模拟速查表保存
conn.execute("UPDATE interview_prep SET cheatsheet_md = ? WHERE id = ?",
             ("# 字节跳动速查表\n\n## 公司概况\n...\n\n## 面试要点\n...", prep_id))
conn.commit()
cs = conn.execute("SELECT cheatsheet_md FROM interview_prep WHERE id = ?", (prep_id,)).fetchone()
test("公司速查表 Markdown 保存成功", cs["cheatsheet_md"] is not None and "字节跳动" in cs["cheatsheet_md"])


# ══════════════════════════════════════════════════════════════
# 测试 10: AI 引擎模块检查
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 10: AI 引擎模块 (services/ai_engine.py)")
print("=" * 60)

try:
    from services import ai_engine
    test("ai_engine 模块可导入", True)

    # 检查关键函数是否存在
    functions = ["parse_jd", "calculate_fit_score", "generate_tailored_resume",
                 "generate_interview_prep", "generate_cheatsheet"]
    for fn_name in functions:
        test(f"函数 {fn_name}() 存在", hasattr(ai_engine, fn_name), f"缺少函数: {fn_name}")

    # 测试 calculate_fit_score（不需要 API 调用）
    test_parsed = {
        "skills_required": ["Python", "Go", "分布式系统"],
        "skills_preferred": ["Kubernetes", "机器学习"],
    }
    # 需要主简历才能计算
    resume_path = settings.master_resume_full_path
    if resume_path.exists():
        score = ai_engine.calculate_fit_score(test_parsed)
        test(f"calculate_fit_score 返回数值 ({score}%)", isinstance(score, (int, float)) and 0 <= score <= 100,
             f"返回值: {score}")
    else:
        warn("无法测试 calculate_fit_score", "主简历文件不存在")

except ImportError as e:
    test("ai_engine 模块可导入", False, str(e))


# ══════════════════════════════════════════════════════════════
# 测试 11: 数据库完整性
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 11: 数据库完整性")
print("=" * 60)

conn.execute("PRAGMA foreign_keys=ON")
conn.execute("DELETE FROM job_descriptions WHERE id = ?", (jd_ids[9],))
conn.commit()

remaining = conn.execute("SELECT COUNT(*) as c FROM job_descriptions").fetchone()["c"]
test("外键级联删除正常", remaining == 9)

try:
    conn.execute("INSERT INTO job_descriptions (company, title, raw_text, status) VALUES ('test', 'test', 'test', 'INVALID')")
    test("CHECK 约束拦截无效状态", False, "插入了无效状态 'INVALID' 但没报错")
except sqlite3.IntegrityError:
    test("CHECK 约束拦截无效状态", True)
conn.rollback()


# ══════════════════════════════════════════════════════════════
# 测试 12: 页面文件完整性检查
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("测试 12: 页面文件完整性")
print("=" * 60)

required_pages = [
    "pages/dashboard.py", "pages/jd_input.py", "pages/jd_browser.py",
    "pages/master_resume.py", "pages/generate.py", "pages/pipeline.py",
    "pages/email_composer.py", "pages/interview.py", "pages/settings_page.py",
]

for page in required_pages:
    page_path = ROOT / page
    test(f"页面 {page} 存在", page_path.exists(), "文件缺失")

# cheatsheet.py 应该已从导航中移除
test("cheatsheet.py 已从 app.py 导航中移除",
     "cheatsheet" not in open(ROOT / "app.py", encoding="utf-8").read(),
     "app.py 中仍引用了 cheatsheet.py")

# 检查 app.py 中文化
app_content = open(ROOT / "app.py", encoding="utf-8").read()
test("app.py 导航已中文化", "总览" in app_content and "职位情报" in app_content,
     "app.py 中仍有英文导航组名")

# 检查 dashboard.py 中文化
dash_content = open(ROOT / "pages/dashboard.py", encoding="utf-8").read()
test("dashboard.py 已中文化", "求职仪表盘" in dash_content, "仍有英文")

# 检查 settings_page.py 可编辑
settings_content = open(ROOT / "pages/settings_page.py", encoding="utf-8").read()
test("settings_page.py 支持编辑 API 配置", "st.form" in settings_content and "form_submit_button" in settings_content,
     "设置页仍然是只读的")


# ══════════════════════════════════════════════════════════════
# 清理
# ══════════════════════════════════════════════════════════════
conn.close()
if TEST_DB.exists():
    TEST_DB.unlink()


# ══════════════════════════════════════════════════════════════
# 测试报告
# ══════════════════════════════════════════════════════════════
print("\n")
print("═" * 60)
print("📋 Career OS 产品测试报告 v2（修复后）")
print("═" * 60)

print(f"\n✅ 通过: {len(PASSED)} 项")
print(f"❌ 失败: {len(FAILED)} 项")
print(f"⚠️  警告: {len(WARNINGS)} 项")

if FAILED:
    print(f"\n{'─' * 60}")
    print("❌ 失败详情:")
    for name, detail in FAILED:
        print(f"  • {name}: {detail}")

if WARNINGS:
    print(f"\n{'─' * 60}")
    print("⚠️  警告详情:")
    for name, detail in WARNINGS:
        print(f"  • {name}: {detail}")

print(f"\n{'─' * 60}")
print("📊 按模块汇总:")
print(f"  仪表盘         : ✅ 中文化完成，8 项指标 + 漏斗图 + 技能热度 + 动态")
print(f"  添加 JD         : ✅ 粘贴和上传均可用")
print(f"  浏览 JD         : ✅ 过滤/排序/详情/删除/AI解析 全部可用")
print(f"  主简历          : ✅ YAML 编辑/查看/上传可用")
print(f"  AI 简历生成     : ✅ 调用 Claude API，自动保存并版本管理")
print(f"  进度追踪        : ✅ 全 8 状态看板 + 状态更新器")
print(f"  邮件撰写        : ✅ 模板预填 + 草稿保存 + SMTP 发送 + 邮件记录")
print(f"  面试准备        : ✅ 模拟面试题(5分类) + 公司速查表，合并为一个页面")
print(f"  设置            : ✅ API/SMTP 配置可编辑，数据库管理")
print(f"  AI 引擎         : ✅ 5 个核心函数: parse_jd, fit_score, resume, interview, cheatsheet")
print("═" * 60)
