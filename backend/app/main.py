from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.persistence import engine, Base
from app.presentation.api import alert_router, auth_router, location_router, profile_router

# Import models
from app.models.alert_model import Alert
from app.models.location_model import LocationUpdate
from app.models.profile_model import Profile

app = FastAPI(
    title="Secure Alert Platform API",
    version="1.0.0",
    description="E2EE encrypted alert system with GPS tracking"
)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REGISTER ROUTES
app.include_router(auth_router)
app.include_router(alert_router)
app.include_router(location_router)
app.include_router(profile_router)

@app.get("/")
def root():
    return {"message": "API running"}
