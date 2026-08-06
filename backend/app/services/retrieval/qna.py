"""
/// <summary>
/// Agent for searching common Q&A patterns and support logs (ArioNex QnA Retrieval Agent)
/// </summary>
/// <remarks>
/// This module performs semantic similarity search over the Q&A patterns stored in the qna_query table.
/// The goal of this agent is to directly find the organization's previous Q&A chat loops and tickets.
/// </remarks>
"""

import logging
from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding_cached

logger = logging.getLogger("arionex.qna")

class QnAAgent:
    """
    /// <summary>
    /// Q&A search agent class for directly matching organizational Q&A patterns
    /// </summary>
    """
    def __init__(self):
        # Check whether the module is enabled in the feature settings
        self.is_enabled = settings.services.qna_processor

    def retrieve_context(self, query: str, threshold: float = 0.5, k: int = 4, file_ids: list[int] = None, filters: dict = None, embedding: list = None) -> list[dict]:
        """
        /// <summary>
        /// Semantic retrieval and direct matching of Q&A patterns from the qna_query table
        /// </summary>
        /// <param name="query">User's rewritten standalone query</param>
        /// <param name="threshold">Cosine similarity threshold (default: 0.5)</param>
        /// <param name="k">Number of returned records (default: 4)</param>
        /// <param name="file_ids">File IDs that limit RAG</param>
        /// <param name="filters">Dynamic customization filters</param>
        /// <param name="embedding">Precomputed query embedding (if available) to avoid a duplicate API call</param>
        /// <returns>List of corresponding Q&A patterns found above the threshold</returns>
        """
        if not self.is_enabled:
            logger.info("Support Lead Agent is disabled in config.yaml. Skipping QnA vector retrieval.")
            return []
            
        logger.info(f"Support Lead Agent starting similarity search for query: '{query}'")
        
        # 1. Extract the 3072-dimensional embedding for the input query (cached if not provided externally)
        if embedding is None:
            embedding = get_embedding_cached(query)
        
        # 2. Dynamic filtering based on IDs and custom filters
        filter_clause = ""
        params = [embedding]
        
        if file_ids:
            placeholders = ",".join(["%s"] * len(file_ids))
            filter_clause += f" AND file_id IN ({placeholders})"
            params.extend(file_ids)
            
        if filters:
            for column, value in filters.items():
                if value:
                    if not isinstance(value, (list, tuple)):
                        value = [value]
                    if column == "content":
                        like_clauses = []
                        for val in value:
                            like_clauses.append(f"{column} ILIKE %s")
                            params.append(f"%{val}%")
                        if like_clauses:
                            filter_clause += f" AND ({' OR '.join(like_clauses)})"
                    else:
                        placeholders = ",".join(["%s"] * len(value))
                        filter_clause += f" AND {column} IN ({placeholders})"
                        params.extend(value)
            
        params.append(k)
        
        # 3. Query the qna_query table
        sql = f"""
        SELECT content, file_id, sequence_id,
               1 - (embedding <=> %s::vector) AS similarity
        FROM qna_query
        WHERE TRUE
        {filter_clause}
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        results = []
        conn = None
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                
            for row in rows:
                content, file_id, seq_id, similarity = row
                
                # Apply the RAG threshold similarity filter
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": f"Support_Logs_ID_{file_id}" if file_id else "QnA_Template",
                        "file_id": file_id or 0,
                        "sequence_id": seq_id or 0,
                        "similarity": similarity,
                        "source_type": "qna"
                    })
                    
            logger.info(f"Support Lead Agent retrieved {len(results)} chunks from qna_query above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Support Lead Agent database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results


# Global Q&A search agent instance
qna_agent = QnAAgent()
