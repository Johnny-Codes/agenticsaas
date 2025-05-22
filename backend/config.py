from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    UPLOAD_DIR: str = "../uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
