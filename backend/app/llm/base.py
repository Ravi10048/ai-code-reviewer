from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def total_cost_estimate(self) -> float:
        """Rough cost estimate in USD (for tracking, not billing)."""
        # Most open-source models via Groq/Ollama are free or near-free
        return 0.0


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM.

        Args:
            prompt: The user/main prompt.
            system_prompt: System-level instruction.
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens in response.
            response_format: Optional JSON schema for structured output.

        Returns:
            Standardized LLMResponse.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable and functional."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier being used."""
        ...
