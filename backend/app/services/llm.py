import asyncio
import json
import logging

from anthropic import Anthropic
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError


logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.openai_client = (
            AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.groq_base_url,
            )
            if settings.openai_api_key
            else None
        )

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    async def complete(self, prompt: str, *, task: str) -> str:
        primary_provider = self.settings.llm_provider
        model = {
            "research": self.settings.research_model,
            "summarization": self.settings.summarization_model,
            "drafting": self.settings.drafting_model,
        }[task]
        fallback_provider = "openai" if primary_provider == "anthropic" else "anthropic"

        try:
            return await self._complete_with_provider(primary_provider, prompt, model=model)
        except Exception as primary_error:
            logger.exception(
                "Primary LLM request failed",
                extra={"extra_data": {"provider": primary_provider, "task": task}},
            )
            try:
                return await self._complete_with_provider(
                    fallback_provider,
                    prompt,
                    model=self.settings.llm_model if fallback_provider == "openai" else self.settings.fallback_model,
                )
            except Exception as fallback_error:
                logger.exception(
                    "Fallback LLM request failed",
                    extra={"extra_data": {"provider": fallback_provider, "task": task}},
                )
                raise ServiceUnavailableError(
                    f"LLM request failed on both primary and fallback providers: {primary_error}; {fallback_error}"
                ) from fallback_error

    async def _complete_with_provider(self, provider: str, prompt: str, *, model: str) -> str:
        if provider == "anthropic":
            if self.anthropic_client is None:
                raise RuntimeError("Anthropic API key is not configured.")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model=model,
                    max_tokens=1800,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=self.settings.llm_timeout_seconds,
            )
            return "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            ).strip()

        if provider == "openai":
            if self.openai_client is None:
                raise RuntimeError("OpenAI API key is not configured.")
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                ),
                timeout=self.settings.llm_timeout_seconds,
            )
            message = response.choices[0].message.content if response.choices else ""
            return message.strip() if message else ""

        raise ValueError(f"Unsupported provider: {provider}")

    async def complete_json(self, prompt: str, *, task: str) -> dict:
        response_text = await self.complete(prompt, task=task)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"raw_text": response_text}
