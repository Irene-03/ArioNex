"""
/// <summary>
/// تسک‌های Celery برای پردازش پس‌زمینه استخراج موجودیت‌ها و قوانین (Celery Knowledge Extraction Tasks)
/// </summary>
"""

import logging
from app.core.celery_app import celery_app
from app.services.workers.toggleable_services import entity_extractor_worker, rule_extractor_worker

logger = logging.getLogger("arionex.extractor_tasks")

@celery_app.task(name="app.tasks.extractor_tasks.run_extract_entities_task")
def run_extract_entities_task(text_chunk: str, file_id: int):
    """
    /// <summary>
    /// تسک پس‌زمینه سلری برای استخراج موجودیت‌ها و روابط از تکه متن سند
    /// </summary>
    """
    logger.info(f"Celery task started: run_extract_entities_task for file_id={file_id}")
    try:
        entity_extractor_worker.extract_entities(text_chunk, file_id)
    except Exception as e:
        logger.error(f"Failed to execute extract_entities task for file_id={file_id}: {str(e)}")
        raise e


@celery_app.task(name="app.tasks.extractor_tasks.run_extract_rules_task")
def run_extract_rules_task(text_chunk: str, file_id: int):
    """
    /// <summary>
    /// تسک پس‌زمینه سلری برای استخراج قوانین و آیین‌نامه‌ها از تکه متن سند
    /// </summary>
    """
    logger.info(f"Celery task started: run_extract_rules_task for file_id={file_id}")
    try:
        rule_extractor_worker.extract_rules(text_chunk, file_id)
    except Exception as e:
        logger.error(f"Failed to execute extract_rules task for file_id={file_id}: {str(e)}")
        raise e
