from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "NutriAI Backend"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/nutriai"
    TEST_USER_ID: str = "00000000-0000-0000-0000-000000000001"
    UPLOAD_DIR: str = "uploads"
    MEDIA_BASE_URL: str = "http://localhost:8000"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL_NAME: str = "deepseek-v4-flash"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()