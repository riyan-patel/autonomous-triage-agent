import os


class Settings:
    def __init__(self) -> None:
        self.llm_provider: str = os.environ.get("LLM_PROVIDER", "anthropic")
        self.anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
        self.llm_model: str = os.environ.get("LLM_MODEL", "claude-sonnet-5")
        self.confidence_threshold: float = float(os.environ.get("AUTONOMY_CONFIDENCE_THRESHOLD", "0.85"))


settings = Settings()
