from dataclasses import dataclass
from dotenv import find_dotenv, load_dotenv
import os


DEFAULT_CORS_ALLOWED_ORIGINS = (
    "https://infraspend.io",
    "https://www.infraspend.io",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


@dataclass
class Config:
    InfisicalClientId: str
    InfisicalClientSecret: str
    InfisicalProjectId: str
    Environment: str
    CorsAllowedOrigins: list[str]

    def __init__(self):
        env_file = find_dotenv()
        if env_file:
            load_dotenv(env_file)
        self.load_config()

    def load_config(self):
        self.InfisicalClientId = os.getenv("INFISICAL_CLIENT_ID")
        self.InfisicalClientSecret = os.getenv("INFISICAL_CLIENT_SECRET")
        self.InfisicalProjectId = os.getenv("INFISICAL_PROJECT_ID")
        self.Environment = os.getenv("ENVIRONMENT", "dev")
        self.CorsAllowedOrigins = self._parse_cors_allowed_origins(
            os.getenv("CORS_ALLOWED_ORIGINS")
        )

    @staticmethod
    def _parse_cors_allowed_origins(value: str | None) -> list[str]:
        if not value:
            return list(DEFAULT_CORS_ALLOWED_ORIGINS)

        origins = []
        for origin in value.split(","):
            normalized_origin = origin.strip().rstrip("/")
            if normalized_origin:
                origins.append(normalized_origin)

        return origins
