import os


class Settings:
    def __init__(self) -> None:
        # Personal access token for local dev/testing. Production wires the
        # GitHub App (GITHUB_APP_ID / GITHUB_APP_PRIVATE_KEY_PATH in
        # .env.example) to mint short-lived installation tokens instead -
        # that exchange lands when the server is actually deployed.
        self.github_token: str = os.environ.get("GITHUB_TOKEN", "")
        self.dry_run: bool = os.environ.get("DRY_RUN", "true").lower() == "true"


settings = Settings()
