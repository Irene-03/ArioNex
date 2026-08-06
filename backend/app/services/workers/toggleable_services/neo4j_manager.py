import logging
from app.core.config import settings

logger = logging.getLogger("arionex.toggleable_services")


class Neo4jDatabaseManager:
    """
    /// <summary>
    /// Manager for connecting to the Neo4j graph database (Neo4j Graph Database Manager)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.neo4j
        self.client = None
        if self.is_enabled:
            logger.info("[Toggleable Database] Neo4j Connection requested. Initializing drivers...")

    def insert_relationship(self, source: str, relation: str, target: str) -> bool:
        """
        /// <summary>
        /// Insert a graph relationship edge into the Neo4j database
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Database] Neo4j Graph DB is DISABLED in config.yaml. Relationship not saved.")
            return False
            
        logger.info(f"[Toggleable Database] Neo4j Graph DB is ACTIVE. Mock inserting: ({source})-[{relation}]->({target})")
        return True
