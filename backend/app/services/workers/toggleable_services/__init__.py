from app.services.workers.toggleable_services.entity_extractor import EntityExtractorWorker
from app.services.workers.toggleable_services.rule_extractor import RuleExtractorWorker
from app.services.workers.toggleable_services.neo4j_manager import Neo4jDatabaseManager
from app.services.workers.toggleable_services.safety_auditor import LocalGemmaSafetyAuditor
from app.services.workers.toggleable_services.helpers import _clean_and_parse_json

entity_extractor_worker = EntityExtractorWorker()
rule_extractor_worker = RuleExtractorWorker()
neo4j_manager = Neo4jDatabaseManager()
local_gemma_auditor = LocalGemmaSafetyAuditor()
