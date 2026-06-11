# -------------------------------------------------------
# بسته مدیریت پرامپت‌های متمرکز ArioNex (Centralized Prompt Templates)
# -------------------------------------------------------
# تمامی قالب‌های پرامپت LLM از این بسته import می‌شوند.
# جداسازی پرامپت‌ها از کد منطقی باعث می‌شود تست و بهینه‌سازی آسان‌تر باشد.
from .rag_prompts import (
    RESPONDER_TEMPLATE,
    STANDALONE_TEMPLATE,
    STANDARD_REFUSAL_MESSAGE,
)
from .analyst_prompts import get_analyst_system_prompt
from .router_prompts import QUERY_ROUTER_PROMPT
from .lawyer_prompts import LAWYER_AUDIT_PROMPT
