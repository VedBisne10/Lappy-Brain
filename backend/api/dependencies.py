from backend.config.settings import Settings, settings

def get_settings() -> Settings:
    # Returns the shared settings object so FastAPI can inject it into route handlers via Depends()
    return settings
