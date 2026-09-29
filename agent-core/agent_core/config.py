import os


class Settings:
    def __init__(self) -> None:
        self.llm_provider: str = os.environ.get("LLM_PROVIDER", "anthropic")
        self.anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
        self.gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
        self.llm_model: str = os.environ.get("LLM_MODEL") or (
            "gemini-flash-lite-latest" if self.llm_provider == "gemini" else "claude-sonnet-5"
        )
        self.confidence_threshold: float = float(os.environ.get("AUTONOMY_CONFIDENCE_THRESHOLD", "0.85"))


settings = Settings()
