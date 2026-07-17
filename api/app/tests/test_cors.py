from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.helpers.config import Config


def build_cors_test_client() -> TestClient:
    config = Config()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CorsAllowedOrigins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/v1/configuration/list")
    def list_configurations():
        return {"data": []}

    return TestClient(app)


def test_cors_preflight_allows_production_dashboard_origin(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "https://infraspend.io,https://www.infraspend.io/"
    )
    client = build_cors_test_client()

    response = client.options(
        "/v1/configuration/list",
        headers={
            "Origin": "https://infraspend.io",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://infraspend.io"
    assert "authorization" in response.headers["access-control-allow-headers"]


def test_cors_response_allows_production_dashboard_origin(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "https://infraspend.io,https://www.infraspend.io/"
    )
    client = build_cors_test_client()

    response = client.get(
        "/v1/configuration/list",
        headers={"Origin": "https://www.infraspend.io"},
    )

    assert response.headers["access-control-allow-origin"] == "https://www.infraspend.io"
