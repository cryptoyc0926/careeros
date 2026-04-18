#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Career OS — macOS 一键安装 & 启动脚本
# ══════════════════════════════════════════════════════════════
# 用法: 在终端中执行
#   cd career-os
#   chmod +x setup.sh
#   ./setup.sh
# ══════════════════════════════════════════════════════════════

set -e

echo ""
echo "🚀 Career OS — 安装中..."
echo "════════════════════════════════════"

# ── 检查 Python ──
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.11+"
    echo "   brew install python3"
    exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYVER"

# ── 创建虚拟环境 ──
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# ── 激活虚拟环境 ──
source venv/bin/activate
echo "✅ 虚拟环境已激活"

# ── 安装依赖 ──
echo "📦 安装依赖（首次可能需要 1-2 分钟）..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ 依赖安装完成"

# ── 初始化数据库 ──
if [ ! -f "data/career_os.db" ]; then
    echo "🗄️  初始化数据库..."
    python scripts/init_db.py
else
    echo "✅ 数据库已存在"
fi

# ── 检查 .env ──
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，从模板创建..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 填入你的 API Key"
else
    echo "✅ .env 配置文件已就绪"
fi

# ── 启动 ──
echo ""
echo "════════════════════════════════════"
echo "🚀 启动 Career OS..."
echo "   地址: http://127.0.0.1:8501"
echo "   按 Ctrl+C 停止"
echo "════════════════════════════════════"
echo ""

streamlit run app.py
