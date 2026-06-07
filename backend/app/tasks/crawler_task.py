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

def safe_run_async(coro):
    """
    /// <summary>
    /// اجرای امن و پایدار یک Coroutine در محیط ناهمزمان یا سنکرون سلری
    /// </summary>
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except Exception:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
    else:
        return loop.run_until_complete(coro)


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
    
    coro = crawler_service.run_crawl_job(
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
    
    safe_run_async(coro)
    logger.info(f"Celery task completed for crawler job_id: {job_id}")

