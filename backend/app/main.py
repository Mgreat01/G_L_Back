from fastapi import FastAPI

from app.routes.alert_routes import router as alert_router
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Secure Alert Platform"
)

app.include_router(alert_router)

@app.get("/")
def root():
    return {
        "message": "API running"
    }