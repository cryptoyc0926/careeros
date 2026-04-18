# CareerOS — HuggingFace Spaces / Railway / VPS 通用 Docker 镜像
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FROM python:3.11-slim

WORKDIR /app

# 系统依赖：WeasyPrint 需要 pango / cairo；Playwright 可选
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-noto-cjk \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Playwright（SPA JD 抓取用，失败不阻塞 build）
RUN pip install --no-cache-dir playwright \
    && (playwright install --with-deps chromium || echo "Playwright chromium install skipped")

# 应用代码
COPY . /app

# 持久化数据目录：HF Spaces 会挂 /data，其他平台可 mount -v
RUN mkdir -p /data \
    && if [ ! -f /data/user_profile.yaml ] && [ -f /app/data/user_profile.example.yaml ]; then \
         cp /app/data/user_profile.example.yaml /data/user_profile.yaml ; \
       fi

ENV DATA_DIR=/data \
    DEMO_MODE=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:7860/_stcore/health || exit 1

CMD ["streamlit", "run", "web/app.py"]
