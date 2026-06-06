# -------------------------------------------------------
# بسته schema های Pydantic آریونکس (ArioNex Pydantic Schemas Package)
# -------------------------------------------------------
# تمامی مدل‌های درخواست و پاسخ API از این بسته import می‌شوند.
# جداسازی schema از endpoint باعث می‌شود مدل‌ها قابل استفاده مجدد باشند.
from .query_schemas import QueryRequest, QueryResponse
from .config_schemas import ConfigUpdateRequest
