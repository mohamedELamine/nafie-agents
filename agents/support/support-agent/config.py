import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Support Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "support_agent"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # OpenAI
    openai_api_key: str

    # HelpScout
    helpscout_api_key: str
    helpscout_app_id: str

    # Resend (for escalation emails)
    resend_api_key: str

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
