"""
/// <summary>
/// تسک‌های Celery برای پردازش پس‌زمینه کرالر وب (Celery Crawler Tasks)
/// </summary>
"""

import logging
import asyncio
from app.core.celery_app import celery_app
from app.services.workers.crawler_service import crawler_service

logger = logging.getLogger("arionex.crawler_task")

@celery_app.task(name="app.tasks.crawler_task.run_crawler_task", bind=True)
def run_crawler_task(
    self,
    job_id: str,
    url: str,
    max_pages: int,
    max_depth: int,
    concurrency: int,
    js_render: bool,
    follow_external: bool,
    respect_robots: bool,
    label: str,
    widget_id: int
):
    """
    /// <summary>
    /// تسک اجرای ناهمزمان کرالر وب با Celery
    /// </summary>
    """
    logger.info(f"Celery task started for crawler job_id: {job_id}")
    # اجرای متد async به صورت سنکرون در تردپارت برای Celery
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # در صورت اجرا درون یک Event Loop فعال
        future = asyncio.run_coroutine_threadsafe(
            crawler_service.run_crawl_job(
                job_id=job_id,
                url=url,
                max_pages=max_pages,
                max_depth=max_depth,
                concurrency=concurrency,
                js_render=js_render,
                follow_external=follow_external,
                respect_robots=respect_robots,
                label=label,
                widget_id=widget_id
            ),
            loop
        )
        future.result()
    else:
        loop.run_until_complete(
            crawler_service.run_crawl_job(
                job_id=job_id,
                url=url,
                max_pages=max_pages,
                max_depth=max_depth,
                concurrency=concurrency,
                js_render=js_render,
                follow_external=follow_external,
                respect_robots=respect_robots,
                label=label,
                widget_id=widget_id
            )
        )
    logger.info(f"Celery task completed for crawler job_id: {job_id}")
