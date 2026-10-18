from fastapi import FastAPI
from backend.config import settings
from backend.api.routes.health import router as health_check

app = FastAPI(
    title = settings.app_name,
    description = "Local AI Assistant for Laptop",
    version = settings.app_version,
    debug = settings.debug
)

@app.get("/", tags = ["General"])
def root():
    return {
        "app" : settings.app_name,
        "message" : "LappyBrain backend is running",
        "version" : settings.app_version,
    }

app.include_router(health_check)

