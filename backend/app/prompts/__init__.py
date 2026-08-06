# -------------------------------------------------------
# ArioNex centralized prompt management package (Centralized Prompt Templates)
# -------------------------------------------------------
# All LLM prompt templates are imported from this package.
# Separating prompts from the logic code makes testing and optimization easier.
from .rag_prompts import (
    RESPONDER_TEMPLATE,
    RESPONDER_TEMPLATE_OPEN,
    STANDALONE_TEMPLATE,
    STANDARD_REFUSAL_MESSAGE,
)
from .analyst_prompts import get_analyst_system_prompt
from .router_prompts import QUERY_ROUTER_PROMPT
from .lawyer_prompts import LAWYER_AUDIT_PROMPT
