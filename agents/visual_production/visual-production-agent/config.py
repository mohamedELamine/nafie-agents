from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Keys
    flux_api_key: str
    ideogram_api_key: str
    claude_api_key: str
    resend_api_key: str

    # Storage
    storage_path: str = "/app/storage"
    storage_type: str = "local"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "visual_production"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Application
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"

    # Budget
    budget_limit_usd: float = 2.00

    # Review Queue
    review_timeout_hours: int = 48
    review_reminder_hours: int = 24

    # Video preview (optional)
    enable_video_preview: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
