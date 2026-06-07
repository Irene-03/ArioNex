"""
/// <summary>
/// پیکربندی و راه‌اندازی Celery Application برای تسک‌های غیرهمزمان (Celery Task Manager)
/// </summary>
"""

from celery import Celery
from app.core.config import settings

# تعریف اپلیکیشن سلری با استفاده از ردیس به عنوان Broker و Backend
celery_app = Celery(
    "arionex",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.extractor_tasks"]
)

# تنظیمات اضافی برای پایداری و بهبود کارایی
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True
)
