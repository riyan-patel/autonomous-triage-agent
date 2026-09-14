import os


class Settings:
    def __init__(self) -> None:
        self.redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.triage_queue_name: str = os.environ.get("TRIAGE_QUEUE_NAME", "triage")
        self.max_retries: int = int(os.environ.get("WORKER_MAX_RETRIES", "3"))


settings = Settings()
