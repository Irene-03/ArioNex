from app.services.retrieval.query_router.router import route_query_intent
from app.services.retrieval.query_router.web_search import perform_tavily_web_search
from app.services.retrieval.query_router.synthesizer import (
    synthesize_rag_response,
    synthesize_rag_response_stream
)

# Expose internal agents and DB helper for test patching compatibility
from app.services.retrieval.vector_search import vector_search_agent
from app.services.retrieval.qna import qna_agent
from app.services.retrieval.analyst import analyst_agent
from app.services.retrieval.investigator import investigator_agent
from app.services.retrieval.lawyer import lawyer_agent
from app.core.database import get_db_connection

