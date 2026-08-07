# -------------------------------------------------------
# ArioNex Independent FastAPI Routes Package (ArioNex Independent FastAPI Routes)
# -------------------------------------------------------
# Each router file manages a group of related endpoints.
# These routers are fully independent from the frontend and are used for direct backend testing.
from .query_routes import router as query_router
from .upload_routes import router as upload_router
from .config_routes import router as config_router
from .widget_routes import router as widget_router
from .integration_routes import router as integration_router
from .crawler_routes import router as crawler_router
from .auth_routes import router as auth_router
from .knowledge_routes import router as knowledge_router
from .audit_routes import router as audit_router
