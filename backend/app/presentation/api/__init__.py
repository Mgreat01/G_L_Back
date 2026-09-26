from app.routes.alert_routes import router as alert_router
from app.routes.auth_routes import router as auth_router
from app.routes.location_routes import router as location_router
from app.routes.profile_routes import router as profile_router

__all__ = ["alert_router", "auth_router", "location_router", "profile_router"]

