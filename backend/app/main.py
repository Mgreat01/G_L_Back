from fastapi import FastAPI

from app.routes.alert_routes import router as alert_router

app = FastAPI(
    title="Secure Alert Platform"
)

app.include_router(alert_router)

@app.get("/")
def root():
    return {
        "message": "API running"
    }