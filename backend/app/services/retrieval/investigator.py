"""
/// <summary>
/// Graph investigator agent (The Investigator - Graph RAG Retrieval Agent)
/// </summary>
/// <remarks>
/// This agent extracts key entities from the user's question, matches them against the Postgres graph
/// relationship tables and Neo4j, retrieves the related nodes and edges, and renders them into a structured
/// pseudo-code text format for injection into RAG.
/// </remarks>
"""

import logging
import re
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.database import get_db_connection
from app.services.workers.toggleable_services import neo4j_manager

logger = logging.getLogger("arionex.investigator")

class InvestigatorAgent:
    """
    /// <summary>
    /// Graph investigator agent class for intelligent retrieval of structured graph context
    /// </summary>
    """
    def __init__(self):
        # This agent operates based on whether the entity extraction module is enabled
        self.is_enabled = settings.services.entity_extractor

    def retrieve_graph_context(self, query: str, file_id: Optional[int] = None, max_entities: int = 5) -> str:
        """
        /// <summary>
        /// Retrieve the graph entities and relationships relevant to the question from the database and format them
        /// </summary>
        /// <param name="query">User's standalone question</param>
        /// <param name="file_id">Numeric file ID used to filter results (optional)</param>
        /// <param name="max_entities">Maximum number of selected entities</param>
        /// <returns>Structured graph context string in Persian</returns>
        /// </summary>
        """
        # Soft Enable: even if the toggle is off, we work if data exists in the database
        if not self.is_enabled:
            # Check whether data exists before skipping entirely
            try:
                conn_check = get_db_connection()
                with conn_check.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM extracted_entities")
                    count = cur.fetchone()[0]
                conn_check.close()
                if count == 0:
                    logger.info("[The Investigator] Graph search is disabled and no entities in DB. Skipping.")
                    return ""
                logger.info(f"[The Investigator] Toggle is off but {count} entities found in DB. Activating soft-enable.")
            except Exception:
                return ""


        logger.info(f"[The Investigator] Extracting graph context for query: '{query}' (file_id={file_id})")

        # 1. Extract query words and tokens for matching
        words = [w.strip() for w in re.split(r"[\s،,.;()?!]+", query) if len(w.strip()) > 2]
        if not words:
            return ""

        entities = []
        relationships = []

        # 2. Retrieve matching entities from PostgreSQL
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Search for entities whose names appear in the query, or where the query contains them
                # Use OR to cover both matching directions
                query_param = f"%{query}%"
                cur.execute(
                    """
                    SELECT name, type, description FROM extracted_entities
                    WHERE (file_id = %s OR %s IS NULL)
                      AND (
                           name ILIKE ANY(%s)
                           OR %s ILIKE '%' || name || '%'
                      )
                    LIMIT %s
                    """,
                    (file_id, file_id, [f"%{w}%" for w in words], query, max_entities)
                )
                rows = cur.fetchall()
                for row in rows:
                    entities.append({
                        "name": row[0],
                        "type": row[1],
                        "description": row[2] or ""
                    })

                if entities:
                    entity_names = [ent["name"] for ent in entities]
                    
                    # Retrieve relationships related to the matched entities
                    cur.execute(
                        """
                        SELECT source, target, relationship, description FROM extracted_relationships
                        WHERE (file_id = %s OR %s IS NULL)
                          AND (source = ANY(%s) OR target = ANY(%s))
                        LIMIT 10
                        """,
                        (file_id, file_id, entity_names, entity_names)
                    )
                    rel_rows = cur.fetchall()
                    for rel in rel_rows:
                        relationships.append({
                            "source": rel[0],
                            "target": rel[1],
                            "relationship": rel[2],
                            "description": rel[3] or ""
                        })
        except Exception as e:
            logger.error(f"[The Investigator] Database error during graph context retrieval: {str(e)}")
        finally:
            if conn:
                conn.close()

        # 3. Parallel retrieval from Neo4j if enabled
        if settings.services.neo4j:
            logger.info("[The Investigator] Neo4j is enabled. Querying mock neo4j graph database...")
            # In the real version, a Cypher query is executed via neo4j_manager to extract subgraphs
            for ent in entities:
                neo4j_manager.insert_relationship(ent["name"], "QUERY_MATCHED", "USER_QUESTION")

        # 4. Format the graph output structurally as short statements (pseudo-code)
        if not entities and not relationships:
            return ""

        formatted_lines = ["[اطلاعات ساختاریافته گراف دانش]:"]
        
        # entities
        for ent in entities:
            desc_part = f" (توضیحات: {ent['description']})" if ent["description"] else ""
            formatted_lines.append(f'- موجودیت "{ent["name"]}" از نوع "{ent["type"]}" است.{desc_part}')

        # relationships
        for rel in relationships:
            desc_part = f" (توضیحات: {rel['description']})" if rel['description'] else ""
            formatted_lines.append(f'- "{rel["source"]}" رابطه "{rel["relationship"]}" دارد با "{rel["target"]}".{desc_part}')

        return "\n".join(formatted_lines)

# Global instance for import and use in the RAG chain
investigator_agent = InvestigatorAgent()
