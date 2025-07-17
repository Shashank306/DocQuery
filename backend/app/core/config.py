# config.py
from pathlib import Path
from typing import List, Optional
from pydantic import Field, validator, AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --------------------------------------------------------------------- #
    #   App                                                               #
    # --------------------------------------------------------------------- #
    APP_NAME: str = "User-Auth-RAG-Service"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DATA_DIR: Path = Field(default=Path("./data"))
    
    # Text processing
    CHUNK_SIZE: int = 768
    CHUNK_OVERLAP: int = 64
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"]
    
    # Conversation history settings (NEW)
    HISTORY_TURNS: int = 5
    INCLUDE_HISTORY_BY_DEFAULT: bool = True

    # --------------------------------------------------------------------- #
    #   Security & Authentication                                          #
    # --------------------------------------------------------------------- #
    SECRET_KEY: str = Field(default="development-secret-key-change-in-production", env="SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 360000  # 100 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password policy
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True

    # --------------------------------------------------------------------- #
    #   Database                                                          #
    # --------------------------------------------------------------------- #
    DATABASE_URL: str = Field(default="sqlite:///./data/rag.db", env="DATABASE_URL")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, env="POSTGRES_PASSWORD")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # --------------------------------------------------------------------- #
    #   Vector Store (Weaviate)                                           #
    # --------------------------------------------------------------------- #
    WEAVIATE_URL: str = Field(default="http://localhost:8080", env="WEAVIATE_URL")
    WEAVIATE_API_KEY: Optional[str] = Field(default=None, env="WEAVIATE_API_KEY")
    WEAVIATE_CLASS: str = "UserDocumentChunk"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Vector search settings
    DEFAULT_SEARCH_LIMIT: int = 10
    MAX_SEARCH_LIMIT: int = 100

    # --------------------------------------------------------------------- #
    #   LLM (GROQ)                                                        #
    # --------------------------------------------------------------------- #
    GROQ_API_KEY: str = Field(default="placeholder-api-key", env="GROQ_API_KEY")
    GROQ_MODEL: str = "llama3-70b-8192"
    LLM_MAX_TOKENS: int = 5000
    LLM_TEMPERATURE: float = 0.1

    # --------------------------------------------------------------------- #
    #   Security & CORS                                                   #
    # --------------------------------------------------------------------- #
    BACKEND_CORS_ORIGINS: List[str] = Field(default=["http://localhost:8080","http://127.0.0.1:5173","http://localhost:5173"])
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Rate limiting
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_QUERY: str = "100/minute"

    # --------------------------------------------------------------------- #
    #   Monitoring & Observability                                        #
    # --------------------------------------------------------------------- #
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Health check settings
    HEALTH_CHECK_TIMEOUT: int = 5
    
    # --------------------------------------------------------------------- #
    #   Environment                                                       #
    # --------------------------------------------------------------------- #
    # --------------------------------------------------------------------- #
    #   Environment & Misc                                               #
    # --------------------------------------------------------------------- #
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    @validator("DATA_DIR")
    def _create_data_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def _assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields in .env without validation errors

settings = Settings()