"""
/// <summary>
/// General document vector search agent (ArioNex Vector Search Agent)
/// </summary>
/// <remarks>
/// This module performs cosine similarity search on 3072-dimensional embeddings
/// in the pg_supervisor and pg_dummy tables and extracts results with dynamic filters.
/// It also returns file metadata (such as document name, file ID, and sequence number)
/// alongside the text so it can be displayed as precise citation tags (Source Tags)
/// in the chatbot frontend.
/// </remarks>
"""

import logging
from app.core.config import settings
from app.core.database import get_db_connection
from app.core.embeddings import get_embedding_cached

logger = logging.getLogger("arionex.vector_search")

class VectorSearchAgent:
    """
    /// <summary>
    /// Document vector search agent class for semantic retrieval from pg_supervisor
    /// </summary>
    """
    def __init__(self):
        # Check whether the document worker is enabled in the feature settings
        self.is_enabled = settings.services.unstructured_document_processor

    def retrieve_categorical(self, query: str, threshold: float = 0.3, k: int = 5, file_ids: list[int] = None, embedding: list = None) -> list[dict]:
        """
        /// <summary>
        /// Semantic retrieval of chunks from the pg_supervisor table with category / file ID filtering
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("Librarian Agent is disabled. Skipping document vector retrieval.")
            return []
            
        logger.info(f"Librarian Agent starting categorical search for query: '{query}'")
        
        if embedding is None:
            try:
                embedding = get_embedding_cached(query)
            except Exception as emb_err:
                logger.error(f"Librarian Agent failed to generate query embedding: {str(emb_err)}")
                return []
            
        filter_clause = ""
        params = [embedding]
        
        if file_ids:
            placeholders = ",".join(["%s"] * len(file_ids))
            filter_clause = f"AND file_id IN ({placeholders})"
            params.extend(file_ids)
            
        params.append(k)
        
        sql = f"""
        SELECT content, label, file_id, sequence_id,
               1 - (embedding <=> %s::vector) AS similarity
        FROM pg_supervisor
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
                content, label, file_id, seq_id, similarity = row
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": label or "unnamed_document",
                        "file_id": file_id or 0,
                        "sequence_id": seq_id or 0,
                        "similarity": similarity,
                        "source_type": "document"
                    })
            logger.info(f"Librarian Agent categorical search retrieved {len(results)} chunks above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Librarian Agent categorical search database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results

    def retrieve_general(self, query: str, threshold: float = 0.3, k: int = 5, embedding: list = None) -> list[dict]:
        """
        /// <summary>
        /// Semantic retrieval of general chunks from the pg_dummy table
        /// </summary>
        """
        if not self.is_enabled:
            return []
            
        logger.info(f"Librarian Agent starting general search for query: '{query}'")
        
        if embedding is None:
            try:
                embedding = get_embedding_cached(query)
            except Exception as emb_err:
                logger.error(f"Librarian Agent failed to generate query embedding: {str(emb_err)}")
                return []
            
        sql = """
        SELECT content, 
               1 - (embedding <=> %s::vector) AS similarity
        FROM pg_dummy
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        results = []
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, [embedding, k])
                rows = cur.fetchall()
                
            for row in rows:
                content, similarity = row
                if similarity >= threshold:
                    results.append({
                        "content": content,
                        "label": "dummy_general",
                        "file_id": 0,
                        "sequence_id": 0,
                        "similarity": similarity,
                        "source_type": "general"
                    })
            logger.info(f"Librarian Agent general search retrieved {len(results)} chunks above threshold {threshold}.")
        except Exception as e:
            logger.error(f"Librarian Agent general search database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
                
        return results

    def retrieve_context(self, query: str, threshold: float = 0.5, k: int = 4, file_ids: list[int] = None, embedding: list = None) -> list[dict]:
        """
        /// <summary>
        /// Combined retrieval (backward compatibility)
        /// </summary>
        """
        categorical = self.retrieve_categorical(query, threshold=threshold, k=k, file_ids=file_ids, embedding=embedding)
        if len(categorical) >= k:
            return categorical[:k]
            
        remaining = k - len(categorical)
        general = self.retrieve_general(query, threshold=threshold, k=remaining, embedding=embedding)
        return categorical + general

# Global document vector search agent instance
vector_search_agent = VectorSearchAgent()

