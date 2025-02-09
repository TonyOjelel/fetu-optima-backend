from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FETU Optima"
    
    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Mobile Money
    MTN_API_KEY: str
    MTN_API_SECRET: str
    AIRTEL_API_KEY: str
    AIRTEL_API_SECRET: str
    
    # AI Service
    OPENAI_API_KEY: str
    
    # Monitoring
    SENTRY_DSN: str
    
    # Environment
    ENVIRONMENT: str
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
