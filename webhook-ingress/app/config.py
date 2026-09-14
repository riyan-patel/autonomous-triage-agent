import os


class Settings:
    def __init__(self) -> None:
        self.github_webhook_secret: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        self.redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.triage_queue_name: str = os.environ.get("TRIAGE_QUEUE_NAME", "triage")


settings = Settings()
