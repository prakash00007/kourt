from typing import Annotated
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "Kourt AI Copilot API"
    app_version: str = "0.2.0"
    api_prefix: str = "/api"
    frontend_url: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    enable_docs: bool = True
    sentry_dsn: str | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.0

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama3-70b-8192"
    llm_provider: str = "anthropic"
    research_model: str = "claude-3-7-sonnet-20250219"
    summarization_model: str = "claude-3-7-sonnet-20250219"
    drafting_model: str = "claude-3-7-sonnet-20250219"
    fallback_model: str = "gpt-4.1-mini"

    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    chroma_path: str = str(BASE_DIR / "data" / "chroma")
    chroma_collection_name: str = "indian_legal_corpus"
    retrieval_k: int = 6
    max_context_documents: int = 8
    min_similarity_score: float = 0.15
    llm_timeout_seconds: int = 60

    uploads_dir: str = str(BASE_DIR / "data" / "uploads")
    extracted_dir: str = str(BASE_DIR / "data" / "extracted")
    max_upload_size_mb: int = 25
    max_upload_pages: int = 500
    allowed_upload_extensions: Annotated[list[str], NoDecode] = Field(default_factory=lambda: [".pdf"])
    draft_daily_limit: int = 10

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    cache_ttl_seconds: int = 300
    max_prompt_context_chars: int = 18000
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "kourt"
    s3_bucket_name: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region_name: str = "ap-south-1"
    s3_use_ssl: bool = True
    s3_verify_ssl: bool = True
    s3_presign_expiry_seconds: int = 900

    aws_region: str | None = None
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kourt"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    allow_anonymous_demo: bool = False
    demo_user_email: str = "demo@kourt.local"

    disclaimer_text: str = "AI-generated content. Please verify before use."

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        allowed = {"anthropic", "openai"}
        if value not in allowed:
            raise ValueError(f"llm_provider must be one of {sorted(allowed)}")
        return value

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, value: str) -> str:
        allowed = {"sentence-transformers", "openai"}
        if value not in allowed:
            raise ValueError(f"embedding_provider must be one of {sorted(allowed)}")
        return value

    @field_validator("frontend_url", mode="before")
    @classmethod
    def normalize_frontend_urls(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("allowed_upload_extensions", mode="before")
    @classmethod
    def normalize_upload_extensions(cls, value):
        if isinstance(value, str):
            return [ext.strip().lower() for ext in value.split(",") if ext.strip()]
        return [str(ext).lower() for ext in value]

    @field_validator("demo_user_email")
    @classmethod
    def normalize_demo_user_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_provider_keys(self):
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        if not self.jwt_secret_key or self.jwt_secret_key == "change-me-in-production":
            if self.app_env == "production":
                raise ValueError("JWT_SECRET_KEY must be set to a secure value in production")
        if not self.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is required")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.extracted_dir).mkdir(parents=True, exist_ok=True)
    return settings
