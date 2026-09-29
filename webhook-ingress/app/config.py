import os


class Settings:
    def __init__(self) -> None:
        self.github_webhook_secret: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        self.redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.triage_queue_name: str = os.environ.get("TRIAGE_QUEUE_NAME", "triage")
        # Shared secret the dashboard presents to trigger approval execution
        # (see /internal/approvals/{id}/execute) - not a GitHub-facing
        # secret, just service-to-service auth on webhook-ingress's
        # publicly-exposed port. Unset means the endpoint is closed
        # (fails closed, same posture as an unset GITHUB_WEBHOOK_SECRET).
        self.internal_api_token: str = os.environ.get("INTERNAL_API_TOKEN", "")


settings = Settings()
