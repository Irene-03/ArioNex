"""
/// <summary>
/// پیکربندی و راه‌اندازی Celery Application برای تسک‌های غیرهمزمان (Celery Task Manager)
/// </summary>
"""

import logging
import threading

logger = logging.getLogger("arionex.celery")

try:
    from celery import Celery, Task

    class FallbackTask(Task):
        """
        Custom Celery Task class that falls back to running the task locally in a background Python thread
        if the Celery broker (Redis) is down or unreachable.
        """
        def apply_async(self, args=None, kwargs=None, *args_opt, **kwargs_opt):
            try:
                return super().apply_async(args=args, kwargs=kwargs, *args_opt, **kwargs_opt)
            except Exception as e:
                logger.error(
                    f"Celery broker connection failed for task '{self.name}'. "
                    f"Falling back to local background thread execution. Error: {str(e)}"
                )
                thread = threading.Thread(target=self.run, args=args or (), kwargs=kwargs or {})
                thread.daemon = True
                thread.start()

                class MockAsyncResult:
                    id = "fallback-local-task-id"
                    status = "PENDING"
                return MockAsyncResult()

        def delay(self, *args, **kwargs):
            return self.apply_async(args=args, kwargs=kwargs)

except ImportError:
    class MockConf:
        def update(self, *args, **kwargs):
            pass

    class MockCelery:
        def __init__(self, *args, **kwargs):
            self.conf = MockConf()

        def task(self, *args, **kwargs):
            def decorator(func):
                def delay(*args, **kwargs):
                    logger.warning(
                        f"Celery is not installed on host. Running task '{func.__name__}' asynchronously in a background thread."
                    )
                    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
                    thread.daemon = True
                    thread.start()

                    class MockAsyncResult:
                        id = "mock-task-id-12345"
                        status = "PENDING"
                    return MockAsyncResult()
                func.delay = delay
                return func
            return decorator
    Celery = MockCelery
    FallbackTask = None

from app.core.config import settings

# تعریف اپلیکیشن سلری با استفاده از ردیس به عنوان Broker و Backend
celery_args = {
    "broker": settings.redis_url,
    "backend": settings.redis_url,
    "include": ["app.tasks.crawler_task", "app.tasks.extractor_tasks"]
}
if FallbackTask:
    celery_args["task_cls"] = FallbackTask

celery_app = Celery("arionex", **celery_args)

# تنظیمات اضافی برای پایداری و بهبود کارایی
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    task_track_started=True,
    # در صورت قطع اتصال به بروکر، تلاش مجدد در زمان راه‌اندازی
    broker_connection_retry_on_startup=True
)
