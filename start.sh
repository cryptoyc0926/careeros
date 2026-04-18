#!/bin/bash
# CareerOS Streamlit 启动脚本（带自动重启）
# 用法: ./start.sh  或  bash start.sh

cd "$(dirname "$0")/web" || exit 1

PORT=8501
LOG_FILE="../logs/streamlit.log"
mkdir -p ../logs

echo "🚀 CareerOS 启动中... (端口 $PORT)"

# 如果已有进程在跑，先停掉
existing_pid=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$existing_pid" ]; then
    echo "停止已有进程 (PID: $existing_pid)"
    kill $existing_pid 2>/dev/null
    sleep 1
fi

# 循环重启（进程退出后自动拉起）
while true; do
    echo "[$(date)] 启动 Streamlit..." | tee -a "$LOG_FILE"
    streamlit run app.py \
        --server.port $PORT \
        --server.headless true \
        --browser.gatherUsageStats false \
        >> "$LOG_FILE" 2>&1

    EXIT_CODE=$?
    echo "[$(date)] Streamlit 退出 (code=$EXIT_CODE)，3秒后重启..." | tee -a "$LOG_FILE"
    sleep 3
done
