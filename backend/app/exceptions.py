from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class GitHubAuthError(AppError):
    """GitHub authentication failed."""

    def __init__(self, message: str = "GitHub authentication failed"):
        super().__init__(message, status_code=401)


class WebhookValidationError(AppError):
    """Webhook signature verification failed."""

    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message, status_code=403)


class LLMProviderError(AppError):
    """LLM provider call failed."""

    def __init__(self, message: str = "LLM provider error"):
        super().__init__(message, status_code=502)


class DiffParseError(AppError):
    """Failed to parse diff content."""

    def __init__(self, message: str = "Failed to parse diff"):
        super().__init__(message, status_code=422)


class ReviewError(AppError):
    """Review process failed."""

    def __init__(self, message: str = "Review failed"):
        super().__init__(message, status_code=500)


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)
