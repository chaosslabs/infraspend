from dataclasses import dataclass
from app.helpers.secrets_service import SecretsService
import os


@dataclass
class Secrets:
    AppSecretKey: str
    Auth0Domain: str
    Auth0Audience: str

    def __init__(self):
        from app.helpers.sandbox import sandbox_enabled, session_secret

        if sandbox_enabled():
            self.AppSecretKey = session_secret
            self.Auth0Domain = os.environ["AUTH0_DOMAIN"]
            self.Auth0Audience = os.environ["AUTH0_AUDIENCE"]
            return
        secrets = SecretsService()
        self.AppSecretKey = secrets.get_secret(
            "APP_SECRET_KEY", os.getenv("APP_SECRET_KEY")
        )
        self.Auth0Domain = secrets.get_secret("AUTH0_DOMAIN", os.getenv("AUTH0_DOMAIN"))
        self.Auth0Audience = secrets.get_secret(
            "AUTH0_AUDIENCE", os.getenv("AUTH0_AUDIENCE", "")
        )
