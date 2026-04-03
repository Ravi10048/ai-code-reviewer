from __future__ import annotations

import time

import jwt
from github import Auth, Github, GithubIntegration

from app.config import settings
from app.exceptions import GitHubAuthError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache for installation tokens (they expire after 1 hour)
_token_cache: dict[int, tuple[str, float]] = {}
TOKEN_TTL = 3500  # Refresh 100s before expiry


def _get_jwt() -> str:
    """Generate a JWT for GitHub App authentication.

    GitHub Apps authenticate using short-lived JWTs signed with the app's private key.
    The JWT is valid for up to 10 minutes.
    """
    private_key = settings.github_private_key
    if not private_key:
        raise GitHubAuthError(
            "GitHub private key not found. "
            "Set GITHUB_PRIVATE_KEY_PATH in .env pointing to your .pem file."
        )

    if not settings.github_app_id:
        raise GitHubAuthError("GITHUB_APP_ID is not set in .env")

    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued at (60s in past for clock skew)
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": settings.github_app_id,  # GitHub App ID
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


def get_installation_token(installation_id: int) -> str:
    """Get an installation access token for a specific repo installation.

    Tokens are cached and refreshed automatically before expiry.
    """
    # Check cache
    if installation_id in _token_cache:
        token, expires_at = _token_cache[installation_id]
        if time.time() < expires_at:
            return token

    try:
        app_jwt = _get_jwt()
        auth = Auth.AppAuth(
            app_id=settings.github_app_id,
            private_key=settings.github_private_key,
        )
        gi = GithubIntegration(auth=auth)
        installation_auth = gi.get_access_token(installation_id)

        token = installation_auth.token
        _token_cache[installation_id] = (token, time.time() + TOKEN_TTL)

        logger.info(
            "installation_token_obtained",
            installation_id=installation_id,
        )
        return token

    except Exception as e:
        logger.error(
            "installation_token_failed",
            installation_id=installation_id,
            error=str(e),
        )
        raise GitHubAuthError(f"Failed to get installation token: {str(e)}")


def get_github_client(installation_id: int) -> Github:
    """Get an authenticated PyGithub client for a specific installation."""
    token = get_installation_token(installation_id)
    return Github(auth=Auth.Token(token))


def clear_token_cache() -> None:
    """Clear the token cache (useful for testing)."""
    _token_cache.clear()
