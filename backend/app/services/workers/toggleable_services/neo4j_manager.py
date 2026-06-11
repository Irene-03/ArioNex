import logging
from app.core.config import settings

logger = logging.getLogger("arionex.toggleable_services")


class Neo4jDatabaseManager:
    """
    /// <summary>
    /// مدیر ارتباط با پایگاه داده گرافی نئوفورجی (Neo4j Graph Database Manager)
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
        /// درج یک یال ارتباطی گرافی در پایگاه داده Neo4j
        /// </summary>
        """
        if not self.is_enabled:
            logger.info("[Toggleable Database] Neo4j Graph DB is DISABLED in config.yaml. Relationship not saved.")
            return False
            
        logger.info(f"[Toggleable Database] Neo4j Graph DB is ACTIVE. Mock inserting: ({source})-[{relation}]->({target})")
        return True
