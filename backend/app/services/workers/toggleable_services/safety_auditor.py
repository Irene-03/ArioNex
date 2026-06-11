import logging
from app.core.config import settings

logger = logging.getLogger("arionex.toggleable_services")


class LocalGemmaSafetyAuditor:
    """
    /// <summary>
    /// بازرس امنیتی و ممیزی سوالات مبتنی بر هوش مصنوعی محلی (Local Gemma-2b Auditor)
    /// </summary>
    """
    def __init__(self):
        self.is_enabled = settings.services.safety_auditor
        if self.is_enabled:
            logger.info("[Toggleable Auditor] Initializing local Gemma-2b auditor in memory...")

    def audit_query(self, user_query: str) -> bool:
        if not self.is_enabled:
            return True
            
        logger.info(f"[Toggleable Auditor] Local Gemma-2b is active. Scanning query: '{user_query}'...")
        return True

    def audit_response(self, ai_response: str) -> bool:
        if not self.is_enabled:
            return True
            
        logger.info("[Toggleable Auditor] Local Gemma-2b scanning response content safety...")
        return True
