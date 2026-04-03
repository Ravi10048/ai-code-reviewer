from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LLMProvider(str, Enum):
    GROQ = "groq"
    OLLAMA = "ollama"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"

    @property
    def rank(self) -> int:
        return {"critical": 3, "warning": 2, "suggestion": 1}[self.value]

    def __ge__(self, other: "Severity") -> bool:
        return self.rank >= other.rank

    def __gt__(self, other: "Severity") -> bool:
        return self.rank > other.rank

    def __le__(self, other: "Severity") -> bool:
        return self.rank <= other.rank

    def __lt__(self, other: "Severity") -> bool:
        return self.rank < other.rank


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── GitHub App ──
    github_app_id: str = ""
    github_private_key_path: str = str(PROJECT_ROOT / "github-app.pem")
    github_webhook_secret: str = ""

    # ── LLM Provider ──
    llm_provider: LLMProvider = LLMProvider.GROQ

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-coder-v2"

    # ── Review Settings ──
    min_inline_severity: Severity = Severity.WARNING
    max_files_per_review: int = 50
    max_diff_lines_per_file: int = 500

    # ── Server ──
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'reviews.db'}"
    log_level: str = "INFO"

    @property
    def github_private_key(self) -> str:
        key_path = Path(self.github_private_key_path)
        if key_path.exists():
            return key_path.read_text()
        return ""


settings = Settings()
