from __future__ import annotations

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.exceptions import LLMProviderError, RateLimitError
from app.llm.base import BaseLLMProvider, LLMResponse
from app.utils.logger import get_logger
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq API provider — free tier with Llama, DeepSeek, Mixtral."""

    provider_name = "groq"

    SUPPORTED_MODELS = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self):
        if not settings.groq_api_key:
            raise LLMProviderError("GROQ_API_KEY is not set")

        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        self.rate_limiter = RateLimiter(max_requests=28, window_seconds=60)

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> LLMResponse:
        await self.rate_limiter.acquire()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            usage = response.usage

            logger.info(
                "groq_generation_complete",
                model=self._model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )

            return LLMResponse(
                content=choice.message.content or "",
                model=self._model,
                provider=self.provider_name,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )

        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                logger.warning("groq_rate_limited", model=self._model)
                raise RateLimitError("Groq rate limit hit", retry_after=60)
            logger.error("groq_generation_failed", error=error_msg, model=self._model)
            raise LLMProviderError(f"Groq API error: {error_msg}")

    async def health_check(self) -> bool:
        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False
