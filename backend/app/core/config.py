from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""
    JWT_SECRET: str = "dev-secret-change-me"
    VISION_PROVIDER: str = "demo"
    AI_PROVIDER_API_KEY: str = ""
    STORAGE_BACKEND: str = "local"
    INSPECTION_IMAGE_DIR: str = "./data/images"
    MAX_UPLOAD_MB: int = 10
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    DEMO_MODE: bool = True

    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()
