import json
import logging
from datetime import datetime
from psycopg2.extras import execute_batch
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding
from app.core.minio_client import storage_manager

logger = logging.getLogger("arionex.crawler_service")


def _update_job_in_db(job_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow()
    set_clauses = ", ".join([f"{k} = %s" for k in fields.keys()])
    values = list(fields.values()) + [job_id]
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE crawler_jobs SET {set_clauses} WHERE job_id = %s",
                values
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update crawler job {job_id}: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def _index_chunks_in_db(chunks: list, label: str, source_url: str, job_id: str) -> int:
    conn = None
    indexed = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for idx, chunk in enumerate(chunks):
                embedding = get_embedding(chunk)
                cur.execute(
                    """
                    INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                    VALUES (%s, %s::vector, %s, %s, %s)
                    """,
                    (chunk, embedding, label, 0, idx + 1)
                )
                indexed += 1
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to index chunks for job {job_id}, url {source_url}: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return indexed


def _is_job_cancelled(job_id: str) -> bool:
    """
    بررسی لغو شدن job از دیتابیس.
    از cursor معمولی (tuple) استفاده می‌کند برای یکنواختی.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM crawler_jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if row and row[0] == "cancelled":
                return True
    except Exception as e:
        logger.error(f"Failed to check job cancellation for {job_id}: {str(e)}")
    finally:
        if conn:
            conn.close()
    return False


def _get_embedding_with_retry(text: str, max_retries: int = 5, backoff_factor: float = 2.0) -> list:
    import time
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return get_embedding(text)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(
                f"Embedding API call failed (attempt {attempt + 1}/{max_retries}). "
                f"Retrying in {delay:.1f}s... Error: {str(e)}"
            )
            time.sleep(delay)
            delay *= backoff_factor


def _commit_staged_data(job_id: str, label: str) -> int:
    prefix = f"crawl-staging/{job_id}/"
    staged_files = storage_manager.list_objects(prefix)
    if not staged_files:
        logger.warning(f"[CrawlerJob:{job_id}] No staged files found to commit.")
        return 0

    logger.info(f"[CrawlerJob:{job_id}] Found {len(staged_files)} staged files. Committing via Blue-Green Micro-batches...")

    temp_label = f"crawled_temp:{job_id}"
    batch_size = 20
    total_indexed = 0

    try:
        for i in range(0, len(staged_files), batch_size):
            if _is_job_cancelled(job_id):
                logger.info(f"[CrawlerJob:{job_id}] Cancellation detected during commit batches. Aborting commit.")
                raise InterruptedError("Job was cancelled by the user during database commit.")

            batch_files = staged_files[i:i + batch_size]
            chunks_to_insert = []

            for file_path in batch_files:
                try:
                    content_bytes = storage_manager.get_object_data(file_path)
                    data = json.loads(content_bytes.decode("utf-8"))
                    for idx, chunk in enumerate(data.get("chunks", [])):
                        chunks_to_insert.append({
                            "content": chunk,
                            "sequence_id": idx + 1
                        })
                except Exception as e:
                    logger.error(f"[CrawlerJob:{job_id}] Failed to read/parse staging file {file_path}: {str(e)}")
                    raise e

            if not chunks_to_insert:
                continue

            # تهیه embedding برای هر chunk
            embeddings_data = []
            for item in chunks_to_insert:
                emb = _get_embedding_with_retry(item["content"])
                embeddings_data.append((item["content"], emb, temp_label, 0, item["sequence_id"]))

            # استفاده از execute_batch به جای executemany برای سازگاری کامل با type vector در psycopg2
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    execute_batch(
                        cur,
                        """
                        INSERT INTO pg_supervisor (content, embedding, label, file_id, sequence_id)
                        VALUES (%s, %s::vector, %s, %s, %s)
                        """,
                        embeddings_data,
                        page_size=50
                    )
                    conn.commit()
                total_indexed += len(embeddings_data)
                logger.info(f"[CrawlerJob:{job_id}] Indexed {len(embeddings_data)} chunks in micro-batch {i // batch_size + 1}")
            except Exception as db_err:
                logger.error(f"[CrawlerJob:{job_id}] Staging insert failed in micro-batch: {str(db_err)}")
                if conn:
                    conn.rollback()
                raise db_err
            finally:
                if conn:
                    conn.close()

        conn = None
        try:
            conn = get_db_connection()
            conn.autocommit = False
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM pg_supervisor WHERE label = %s", (temp_label,))
                    row = cur.fetchone()
                    if isinstance(row, dict):
                        temp_count = list(row.values())[0]
                    elif isinstance(row, (tuple, list)):
                        temp_count = row[0]
                    else:
                        temp_count = int(row) if row is not None else 0

                    if temp_count == 0:
                        logger.warning(
                            f"[CrawlerJob:{job_id}] No temporary records found for label '{temp_label}'. "
                            f"Aborting Blue-Green switch to prevent live index deletion."
                        )
                        raise ValueError(f"No temporary crawled data found for job {job_id}")

                    logger.info(
                        f"[CrawlerJob:{job_id}] Performing Blue-Green index switch for label '{label}'. "
                        f"Replacing live index with {temp_count} new chunks."
                    )
                    cur.execute("DELETE FROM pg_supervisor WHERE label = %s", (label,))
                    cur.execute("UPDATE pg_supervisor SET label = %s WHERE label = %s", (label, temp_label))
            logger.info(f"[CrawlerJob:{job_id}] Successfully performed Blue-Green switch. Committed {total_indexed} chunks.")
        except Exception as switch_err:
            logger.error(f"[CrawlerJob:{job_id}] Blue-Green switch transaction failed: {str(switch_err)}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_err:
                    logger.error(f"Rollback failed: {str(rollback_err)}")
            raise switch_err
        finally:
            if conn:
                conn.close()

    except Exception as commit_err:
        logger.error(f"[CrawlerJob:{job_id}] Commit failed. Cleaning up temporary chunks... Error: {str(commit_err)}")
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pg_supervisor WHERE label = %s", (temp_label,))
                conn.commit()
            logger.info(f"[CrawlerJob:{job_id}] Cleaned up temporary database records for '{temp_label}'")
        except Exception as clean_err:
            logger.error(f"[CrawlerJob:{job_id}] Database cleanup failed for '{temp_label}': {str(clean_err)}")
        finally:
            if conn:
                conn.close()
        raise commit_err

    try:
        storage_manager.delete_objects_in_prefix(prefix)
        logger.info(f"[CrawlerJob:{job_id}] Cleaned up MinIO staging prefix: {prefix}")
    except Exception as e:
        logger.warning(f"[CrawlerJob:{job_id}] Staging cleanup failed: {str(e)}")

    return total_indexed
