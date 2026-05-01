import pytest

from app.core.config import Settings


def _base_kwargs() -> dict:
    return {
        "app_env": "development",
        "s3_bucket_name": "kourt-documents",
        "database_url": "sqlite+aiosqlite:///./data/test.db",
        "fallback_provider": "none",
    }


def test_groq_provider_accepts_groq_api_key() -> None:
    settings = Settings(_env_file=None, **_base_kwargs(), llm_provider="groq", groq_api_key="groq-test-key")
    assert settings.is_llm_provider_configured("groq")


def test_groq_provider_accepts_openai_api_key_for_backward_compatibility() -> None:
    settings = Settings(_env_file=None, **_base_kwargs(), llm_provider="groq", openai_api_key="openai-test-key")
    assert settings.is_llm_provider_configured("groq")


def test_fallback_provider_requires_provider_key() -> None:
    kwargs = _base_kwargs()
    kwargs["fallback_provider"] = "groq"
    with pytest.raises(ValueError, match="GROQ_API_KEY is required when FALLBACK_PROVIDER=groq"):
        Settings(_env_file=None, **kwargs, llm_provider="anthropic", anthropic_api_key="anthropic-test-key")
