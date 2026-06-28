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



# کپی و نصب وابستگی‌های پایتونی پروژه
COPY requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install python-multipart

# کپی کدهای بک‌اند به محیط کاربری کانتینر
COPY . /app/

# پورت پیش‌فرض وب‌سرور FastAPI
EXPOSE 8000

# دستور پیش‌فرض راه‌اندازی سرور بک‌اند با uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
