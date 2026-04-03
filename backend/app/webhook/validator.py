from __future__ import annotations

import hashlib
import hmac

from app.config import settings
from app.exceptions import WebhookValidationError


def verify_webhook_signature(payload: bytes, signature: str) -> None:
    """Verify GitHub webhook signature (HMAC-SHA256).

    GitHub sends the signature in the X-Hub-Signature-256 header as:
        sha256=<hex-digest>
    """
    if not settings.github_webhook_secret:
        # No secret configured — skip validation (development only)
        return

    if not signature:
        raise WebhookValidationError("Missing webhook signature header")

    if not signature.startswith("sha256="):
        raise WebhookValidationError("Invalid signature format")

    expected_sig = signature.removeprefix("sha256=")

    computed = hmac.new(
        key=settings.github_webhook_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, expected_sig):
        raise WebhookValidationError("Webhook signature mismatch")
