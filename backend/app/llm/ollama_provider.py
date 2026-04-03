from __future__ import annotations

import httpx

from app.config import settings
from app.exceptions import LLMProviderError
from app.llm.base import BaseLLMProvider, LLMResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider — self-hosted local LLM inference."""

    provider_name = "ollama"

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),  # LLM can be slow
        )

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "messages": [],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})

        if response_format:
            payload["format"] = "json"

        try:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content", "")
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)

            logger.info(
                "ollama_generation_complete",
                model=self._model,
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.provider_name,
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )

        except httpx.ConnectError:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMProviderError(
                    f"Model '{self._model}' not found in Ollama. "
                    f"Pull it with: ollama pull {self._model}"
                )
            raise LLMProviderError(f"Ollama API error: {e.response.text}")
        except Exception as e:
            logger.error("ollama_generation_failed", error=str(e), model=self._model)
            raise LLMProviderError(f"Ollama error: {str(e)}")

    async def health_check(self) -> bool:
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List all models available in the local Ollama instance."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
