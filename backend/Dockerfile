# ================================================================
#   ArioNex backend Dockerfile (ArioNex Backend Dockerfile)
#   Developed based on SRP principles and commercial containerization
# ================================================================

FROM python:3.11-slim

# Set environment variables for correct Python execution and to prevent false buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

WORKDIR /app

# Use faster pip mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn



# Copy and install the project's Python dependencies
COPY requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 300 --retries 5 -r requirements.txt \
    && pip install --timeout 300 python-multipart \
    && (apt-get update -qq --fix-missing && apt-get install -y -qq --no-install-recommends --fix-missing \
        libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
        libasound2 libxshmfence1 libxcomposite1 libxdamage1 libxrandr2 \
        libxtst6 libcups2 libpango-1.0-0 || echo "WARNING: apt-get failed, skipping playwright deps") \
    && rm -rf /var/lib/apt/lists/*

# Copy the backend code into the container working environment
COPY . /app/

# Default FastAPI web server port
EXPOSE 8000

# Default command to start the backend server with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
