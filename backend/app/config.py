from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://oppscraper:password@postgres:5432/oppscraper"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # LDAP
    LDAP_SERVER_URI: str = "ldap://ldap:389"
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""
    LDAP_USER_SEARCH_BASE: str = ""
    LDAP_USER_SEARCH_FILTER: str = "(sAMAccountName={username})"
    LDAP_GROUP_SEARCH_BASE: str = ""
    LDAP_GROUP_SEARCH_FILTER: str = "(member={user_dn})"
    LDAP_USE_TLS: bool = True
    AUTH_BYPASS: bool = False

    # AI
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3

    # SAM.gov
    SAM_GOV_API_KEY: str = ""

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # File storage
    UPLOAD_DIR: str = "/app/uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
