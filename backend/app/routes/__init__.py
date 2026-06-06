# -------------------------------------------------------
# بسته روترهای مستقل FastAPI آریونکس (ArioNex Independent FastAPI Routes)
# -------------------------------------------------------
# هر فایل روتر یک گروه از endpoint‌های مرتبط را مدیریت می‌کند.
# این روترها کاملاً مستقل از فرانت‌اند هستند و برای تست مستقیم backend استفاده می‌شوند.
from .query_routes import router as query_router
from .upload_routes import router as upload_router
from .config_routes import router as config_router
from .widget_routes import router as widget_router
from .integration_routes import router as integration_router
