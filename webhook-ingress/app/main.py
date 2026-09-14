import json
import logging

from fastapi import FastAPI, Header, HTTPException, Request, Response

from .config import settings
from .queue import enqueue_issue_event
from .signature import verify_signature

logger = logging.getLogger("webhook-ingress")

app = FastAPI(title="webhook-ingress")

# issues.opened/edited are the events the agent acts on today; anything else
# is acknowledged (200) but dropped so GitHub doesn't retry it forever.
HANDLED_ACTIONS = {"opened", "edited"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> Response:
    raw_body = await request.body()

    if not verify_signature(raw_body, x_hub_signature_256, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="invalid signature")

    if not x_github_delivery:
        raise HTTPException(status_code=400, detail="missing X-GitHub-Delivery header")

    if x_github_event != "issues":
        return Response(status_code=202)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="malformed JSON payload")

    action = payload.get("action")
    if action not in HANDLED_ACTIONS:
        return Response(status_code=202)

    job_id, was_duplicate = enqueue_issue_event(
        delivery_id=x_github_delivery,
        event=x_github_event,
        payload=payload,
    )

    if was_duplicate:
        logger.info("duplicate delivery %s ignored", x_github_delivery)
    else:
        logger.info("enqueued job %s for delivery %s (action=%s)", job_id, x_github_delivery, action)

    return Response(status_code=202)
