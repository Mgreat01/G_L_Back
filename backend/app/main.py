from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from starlette.responses import JSONResponse
import time

from app.core.database import engine, Base, ensure_performance_schema

from app.routes.alert_routes import router as alert_router
from app.routes.location_routes import router as location_router
from app.routes.profile_routes import router as profile_router
from app.routes.auth_routes import router as auth_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.notification_routes import router as notification_router

# Import models
from app.models.alert_model import Alert
from app.models.location_model import LocationUpdate
from app.models.profile_model import Profile
from app.models.user_model import User
from app.models.alert_model import AlertHistory, AlertRecipientKey
from app.models.audit_log_model import AuditLog
from app.models.notification_model import Notification
from app.models.location_model import RescueTeamLocation


RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120
_rate_limit_buckets = {}

app = FastAPI(
    title="Secure Alert Platform API",
    version="1.0.0",
    description="E2EE encrypted alert system with GPS tracking"
)

Base.metadata.create_all(bind=engine)
ensure_performance_schema()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:4200",
        "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_and_rate_limit(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_limit_buckets.setdefault(client_ip, [])
    bucket[:] = [
        timestamp
        for timestamp in bucket
        if timestamp > now - RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )

    bucket.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=()"
    return response

# REGISTER ROUTES
app.include_router(auth_router)
app.include_router(alert_router)
app.include_router(location_router)
app.include_router(profile_router)
app.include_router(notification_router)
app.include_router(dashboard_router)

@app.get("/")
def root():
    return {"message": "API running"}
