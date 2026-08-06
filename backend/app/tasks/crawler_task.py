"""
/// <summary>
/// Celery tasks for background web crawler processing (Celery Crawler Tasks)
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
    /// Task that runs the web crawler asynchronously with Celery
    /// </summary>
    /// <remarks>
    /// Uses asyncio.run directly, which is the safest approach in Celery workers
    /// (which have no active event loop).
    /// </remarks>
    """
    logger.info(f"Celery task started for crawler job_id: {job_id}")

    try:
        asyncio.run(
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
    except Exception as e:
        logger.error(f"Celery task failed for {job_id}: {str(e)}", exc_info=True)
        raise

    logger.info(f"Celery task completed for crawler job_id: {job_id}")
