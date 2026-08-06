"""
/// <summary>
/// Celery tasks for background extraction of entities and rules (Celery Knowledge Extraction Tasks)
/// </summary>
"""

import logging
from app.core.celery_app import celery_app
from app.services.workers.toggleable_services import entity_extractor_worker, rule_extractor_worker

logger = logging.getLogger("arionex.extractor_tasks")


@celery_app.task(name="app.tasks.extractor_tasks.run_knowledge_extraction_pipeline_task")
def run_knowledge_extraction_pipeline_task(text: str, file_id: int, run_entities: bool, run_rules: bool):
    """
    /// <summary>
    /// Single background task that runs the entire knowledge extraction pipeline (entities and rules) from a document with semantic segmentation
    /// </summary>
    """
    logger.info(f"Celery knowledge extraction pipeline task started for file_id={file_id}")
    
    # Import the segmentation function dynamically to avoid Circular Import
    from app.services.workers.unstructured_processor import split_into_semantic_windows
    
    text_windows = split_into_semantic_windows(text, window_size=3000, overlap=500)
    logger.info(f"Consolidated pipeline generated {len(text_windows)} semantic windows for processing file_id={file_id}")
    
    for idx, window in enumerate(text_windows):
        logger.info(f"Processing semantic window {idx + 1}/{len(text_windows)} for file_id={file_id}...")
        
        # Extract entities
        if run_entities:
            try:
                entity_extractor_worker.extract_entities(window, file_id)
            except Exception as e:
                logger.error(f"Failed to extract entities at window {idx + 1} for file_id={file_id}: {str(e)}")
                # Continue processing the remaining windows even if one window fails
                
        # Extract rules
        if run_rules:
            try:
                rule_extractor_worker.extract_rules(window, file_id)
            except Exception as e:
                logger.error(f"Failed to extract rules at window {idx + 1} for file_id={file_id}: {str(e)}")
                
    logger.info(f"Celery knowledge extraction pipeline task completed for file_id={file_id}")
