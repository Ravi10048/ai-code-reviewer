from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.exceptions import WebhookValidationError
from app.webhook.validator import verify_webhook_signature
from app.webhook.handler import handle_pull_request_event, handle_installation_event
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
):
    """Receive and process GitHub webhook events."""
    body = await request.body()

    # Verify webhook signature
    try:
        verify_webhook_signature(body, x_hub_signature_256)
    except WebhookValidationError as e:
        logger.warning("webhook_signature_invalid")
        return JSONResponse(status_code=403, content={"error": e.message})

    payload = await request.json()

    logger.info("webhook_received", github_event=x_github_event)

    # Route to appropriate handler
    if x_github_event == "pull_request":
        return await handle_pull_request_event(payload)
    elif x_github_event in ("installation", "installation_repositories"):
        return await handle_installation_event(payload)
    elif x_github_event == "ping":
        return {"status": "pong"}
    else:
        return {"status": "ignored", "event": x_github_event}
