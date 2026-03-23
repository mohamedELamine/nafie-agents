from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/supervisor"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Resend
    resend_api_key: str = ""
    owner_email: str = "admin@yourdomain.com"

    # Heartbeat settings
    heartbeat_timeout_sec: int = 120
    health_check_interval_sec: int = 60

    # Application
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
