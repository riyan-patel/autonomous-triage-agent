import logging

from .pipeline import run_triage

logger = logging.getLogger("worker.jobs")


def process_issue_event(event: str, payload: dict, delivery_id: str) -> dict:
    """Entry point the queue worker invokes for each `issues` webhook job.

    Referenced by import path from webhook-ingress (app/queue.py) so the
    two services stay decoupled — ingress never imports worker code.
    `delivery_id` doubles as the RQ job ID (for queue-level idempotency)
    and is threaded through to the audit log (actions.delivery_id) so a
    retried job's second write is a DB-level no-op too.

    A malformed payload is logged and skipped rather than raised: RQ's
    retry policy (set at enqueue time) is meant for transient failures, and
    retrying a permanently-bad payload would just burn all 3 attempts on a
    guaranteed failure.
    """
    try:
        issue = payload["issue"]
        repo = payload["repository"]["full_name"]
        issue_number = issue["number"]
    except KeyError as exc:
        logger.warning("skipping malformed %s payload: missing %s", event, exc)
        return {"status": "invalid_payload", "error": str(exc)}

    logger.info("processing %s issue #%s in %s", event, issue_number, repo)

    result = run_triage(payload, delivery_id=delivery_id)

    logger.info("triage result for %s#%s: %s", repo, issue_number, result.status)
    return {
        "repo": result.repo,
        "issue_number": result.issue_number,
        "status": result.status,
        "confidence": result.confidence,
    }
