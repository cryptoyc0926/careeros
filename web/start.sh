#!/bin/bash
# Career OS — 日常启动脚本（安装后每次用这个）
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Career OS 启动中... http://127.0.0.1:8501"
streamlit run app.py
