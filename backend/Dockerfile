# ================================================================
#   داکرفایل بک‌اند آریونکس (ArioNex Backend Dockerfile)
#   توسعه داده شده بر اساس اصول SRP و کانتینرسازی تجاری
# ================================================================

FROM python:3.11-slim

# تنظیم متغیرهای محیطی برای اجرای صحیح پایتون و ممانعت از ایجاد بافرهای کاذب
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

WORKDIR /app



# کپی و نصب وابستگی‌های پایتونی پروژه
COPY requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install python-multipart \
    && (apt-get update -qq --fix-missing && apt-get install -y -qq --no-install-recommends --fix-missing \
        libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
        libasound2 libxshmfence1 libxcomposite1 libxdamage1 libxrandr2 \
        libxtst6 libcups2 libpango-1.0-0 || echo "WARNING: apt-get failed, skipping playwright deps") \
    && rm -rf /var/lib/apt/lists/*

# کپی کدهای بک‌اند به محیط کاربری کانتینر
COPY . /app/

# پورت پیش‌فرض وب‌سرور FastAPI
EXPOSE 8000

# دستور پیش‌فرض راه‌اندازی سرور بک‌اند با uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
