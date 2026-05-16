from fastapi import FastAPI

from backend.app.routes.alert_routes import router as alert_router

from backend.app.core.database import Base, engine

# création des tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(alert_router)

@app.get("/")
def root():
    return {"message": "API running"}