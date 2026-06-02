# ================================================================
#   داکرفایل بک‌اند آریونکس (ArioNex Backend Dockerfile)
#   توسعه داده شده بر اساس اصول SRP و کانتینرسازی تجاری
# ================================================================

FROM python:3.11-slim

# تنظیم متغیرهای محیطی برای اجرای صحیح پایتون و ممانعت از ایجاد بافرهای کاذب
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# نصب پیش‌نیازهای فیزیکی سیستم‌عامل جهت کامپایل بدون نقص psycopg2 و hazm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب وابستگی‌های پایتونی پروژه
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir python-multipart

# کپی کدهای بک‌اند به محیط کاربری کانتینر
COPY . /app/

# پورت پیش‌فرض وب‌سرور FastAPI
EXPOSE 8000

# دستور پیش‌فرض راه‌اندازی سرور بک‌اند با uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
