from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelOps"
    ENVIRONMENT: str = "development"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "sentinel_runbooks"
    POSTGRES_URI: str = "postgresql://sentinel:sentinel_password@localhost:5432/sentinelops"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    MAX_INVESTIGATION_STEPS: int = 10
    REQUIRE_HUMAN_APPROVAL: bool = True
    AWS_REGION: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
