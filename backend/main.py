from fastapi import FastAPI
from backend.config import settings
from backend.api.routes.health import router as health_check
from backend.api.routes.chat import router as ChatRequest
from backend.api.routes.knowledge import router as knowledge_router
from backend.api.routes.files import router as files_router

# Create the main FastAPI app using settings loaded from the config
app = FastAPI(
    title = settings.app_name,
    description = "Local AI Assistant for Laptop",
    version = settings.app_version,
    debug = settings.debug
)

@app.get("/", tags = ["General"])
def root():
    # Returns basic info about the app — useful to confirm the server is up
    return {
        "app" : settings.app_name,
        "message" : "LappyBrain backend is running",
        "version" : settings.app_version,
    }

# Register the health check and chat routes so FastAPI knows about them
app.include_router(health_check)
app.include_router(ChatRequest)
app.include_router(knowledge_router)
app.include_router(files_router)