#!/bin/bash
# Career OS Claude Code — 一键安装脚本
# 用法: bash scripts/setup.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "================================================"
echo " Career OS Claude Code — 环境配置"
echo "================================================"

# ── 1. 检查依赖 ─────────────────────────────────
echo ""
echo "① 检查系统依赖..."

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✅ $1 已安装 ($(command -v $1))"
    else
        echo "  ❌ $1 未安装 — 请先安装 $1"
        MISSING="$MISSING $1"
    fi
}

check_cmd python3
check_cmd pip3
check_cmd node  # for docx generation
MISSING=""

if [ -n "$MISSING" ]; then
    echo "  ⚠️ 缺少依赖:$MISSING"
    echo "  安装 Node.js: https://nodejs.org/"
    echo "  安装 Python: https://python.org/"
fi

# ── 2. 安装 Python 依赖 ──────────────────────────
echo ""
echo "② 安装 Python 依赖..."

if [ -f "web/requirements.txt" ]; then
    pip3 install -r web/requirements.txt --break-system-packages --quiet 2>/dev/null || \
    pip3 install -r web/requirements.txt --quiet 2>/dev/null || \
    echo "  ⚠️ pip 安装失败，请手动运行: pip install -r web/requirements.txt"
    echo "  ✅ Python 依赖安装完成"
else
    echo "  ⚠️ web/requirements.txt 不存在，跳过"
fi

# 额外需要的包
pip3 install openpyxl pandas --break-system-packages --quiet 2>/dev/null || true

# ── 3. 创建目录结构 ───────────────────────────────
echo ""
echo "③ 创建目录结构..."

mkdir -p data reports prompts web tools scripts
echo "  ✅ 目录结构已创建"

# ── 4. 运行数据库初始化 ──────────────────────────
echo ""
echo "④ 初始化数据库..."

python3 - <<'PYEOF'
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from pathlib import Path

db_path = Path("data/career_os.db")
conn = sqlite3.connect(db_path)

tables = {
    'jobs_pool': """
        CREATE TABLE IF NOT EXISTS jobs_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            city TEXT DEFAULT '',
            direction TEXT DEFAULT '',
            priority TEXT DEFAULT 'P2',
            link_type TEXT DEFAULT '🔶门户入口',
            apply_url TEXT DEFAULT '',
            referral_code TEXT DEFAULT '',
            publish_days INTEGER DEFAULT 99,
            match_score INTEGER DEFAULT 50,
            action_today TEXT DEFAULT '',
            status TEXT DEFAULT 'NEW',
            source TEXT DEFAULT 'WebSearch',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(company, position, city)
        )
    """,
    'contacts': """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            role TEXT DEFAULT '',
            contact_type TEXT DEFAULT 'HR',
            linkedin_url TEXT DEFAULT '',
            maimai_id TEXT DEFAULT '',
            email TEXT DEFAULT '',
            priority TEXT DEFAULT 'P2',
            status TEXT DEFAULT '待触达',
            last_action TEXT DEFAULT '',
            last_action_date TEXT DEFAULT '',
            message_template TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            verified_method TEXT DEFAULT 'WebSearch',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(name, company)
        )
    """,
    'daily_reports': """
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            day_number INTEGER,
            new_jobs INTEGER DEFAULT 0,
            new_contacts INTEGER DEFAULT 0,
            applied_jobs INTEGER DEFAULT 0,
            file_path TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    'application_log': """
        CREATE TABLE IF NOT EXISTS application_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            applied_at TEXT DEFAULT (datetime('now','localtime')),
            method TEXT DEFAULT '',
            status TEXT DEFAULT '已投递',
            notes TEXT DEFAULT '',
            result TEXT DEFAULT ''
        )
    """
}

for name, sql in tables.items():
    conn.execute(sql)
    count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"  ✅ {name}: {count} 条记录")

conn.commit()
conn.close()
print("  数据库初始化完成: data/career_os.db")
PYEOF

# ── 5. 可选：从旧仓库迁移数据 ────────────
echo ""
echo "⑤ 数据迁移（可选）..."

# 如果你有旧版本 CareerOS 数据要导入，设置环境变量指向旧项目目录：
#   COWORK_OFFER_DIR=/path/to/old/project ./scripts/setup.sh
if [ -n "$COWORK_OFFER_DIR" ] && [ -d "$COWORK_OFFER_DIR" ]; then
    python3 scripts/migrate.py --source "$COWORK_OFFER_DIR" 2>&1 | grep -E "(✅|⚠️|❌|🎉)" || true
    echo "  ✅ 数据迁移完成（来源：$COWORK_OFFER_DIR）"
else
    echo "  （跳过：未设置 COWORK_OFFER_DIR 或目录不存在）"
    echo "  新用户首次使用：数据库是空的，请到 Web 界面填写主简历和目标岗位"
fi

# ── 6. 创建 .env 配置文件 ──────────────────────
echo ""
echo "⑥ 配置环境变量..."

if [ ! -f "web/.env" ] && [ -f "web/.env.example" ]; then
    cp web/.env.example web/.env
    echo "  ✅ 已创建 web/.env（请填写 ANTHROPIC_API_KEY）"
elif [ -f "web/.env" ]; then
    echo "  ✅ web/.env 已存在"
else
    cat > web/.env << 'ENV'
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-6
DB_PATH=../data/career_os.db
OUTPUT_DIR=../output/
ENV
    echo "  ✅ 已创建 web/.env（请填写 ANTHROPIC_API_KEY）"
fi

# ── 7. 验证安装 ───────────────────────────────
echo ""
echo "⑦ 验证安装..."

python3 -c "import streamlit, anthropic, pandas, openpyxl; print('  ✅ 所有 Python 包已就绪')" 2>/dev/null || \
    echo "  ⚠️ 部分包未安装，请手动: pip install streamlit anthropic pandas openpyxl"

# ── 8. 完成提示 ────────────────────────────────
echo ""
echo "================================================"
echo " 🎉 安装完成！"
echo "================================================"
echo ""
echo " 启动 Career OS 网页:"
echo "   cd web && streamlit run app.py"
echo "   访问: http://localhost:8501"
echo ""
echo " 启动 Claude Code 多 Agent:"
echo "   cd career-os-claudecode && claude"
echo ""
echo " 手动数据迁移:"
echo "   python3 scripts/migrate.py --source /path/to/OFFER"
echo ""
