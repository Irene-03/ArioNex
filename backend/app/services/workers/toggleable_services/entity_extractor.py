import logging
from typing import Optional

from app.core.config import settings
from app.core.database import get_db_connection
from app.services.workers.toggleable_services.helpers import _clean_and_parse_json

logger = logging.getLogger("arionex.toggleable_services")


class EntityExtractorWorker:
    """
    /// <summary>
    /// Worker that extracts entities from texts to feed the knowledge graph (Entity Extractor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.entity_extractor

    def extract_entities(self, text: str, file_id: Optional[int] = None) -> dict:
        """
        /// <summary>
        /// Automatically extract entities and their relationships from text using an LLM or a Mock fallback
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Service] Entity Extractor is currently DISABLED in config.yaml. Skipping execution.")
            return {"entities": [], "relationships": []}
            
        logger.info(f"[Toggleable Service] Entity Extractor is ACTIVE. Processing text for file_id={file_id}...")

        extracted_data = {"entities": [], "relationships": []}

        try:
            from langchain_core.prompts import PromptTemplate
            from app.prompts.extractor_prompts import ENTITY_EXTRACTION_TEMPLATE
            from app.core.llm_factory import get_llm

            llm = get_llm(temperature=0.0)
            prompt = PromptTemplate.from_template(ENTITY_EXTRACTION_TEMPLATE)
            chain = prompt | llm
            
            response = chain.invoke({"text": text})
            raw_response = response.content.strip()
            extracted_data = _clean_and_parse_json(raw_response)
        except Exception as e:
            logger.error(f"[Toggleable Service] Entity extraction via LLM failed: {str(e)}")
            return {"entities": [], "relationships": []}

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for ent in extracted_data.get("entities", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_entities (name, type, description, file_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (file_id, name) DO UPDATE SET
                            type = EXCLUDED.type,
                            description = EXCLUDED.description
                        """,
                        (ent.get("name"), ent.get("type"), ent.get("description"), file_id)
                    )
                for rel in extracted_data.get("relationships", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_relationships (source, target, relationship, description, file_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (file_id, source, target, relationship) DO UPDATE SET
                            description = EXCLUDED.description
                        """,
                        (rel.get("source"), rel.get("target"), rel.get("relationship"), rel.get("description"), file_id)
                    )
                    
                    if settings.services.neo4j:
                        from app.services.workers.toggleable_services.neo4j_manager import neo4j_manager
                        neo4j_manager.insert_relationship(
                            rel.get("source"), rel.get("relationship"), rel.get("target")
                        )
                conn.commit()
                logger.info(
                    f"[Toggleable Service] Successfully saved {len(extracted_data.get('entities', []))} entities "
                    f"and {len(extracted_data.get('relationships', []))} relationships for file_id={file_id}."
                )
        except Exception as db_err:
            logger.error(f"[Toggleable Service] Failed to save extracted entities/relationships to Postgres: {str(db_err)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return extracted_data
