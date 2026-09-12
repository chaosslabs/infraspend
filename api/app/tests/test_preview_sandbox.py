"""Exercise real sandbox startup, without the suite's migration/Infisical mocks."""

import os
import subprocess
import sys


def test_sandbox_startup_and_isolation(tmp_path):
    script = """
from unittest.mock import patch
from fastapi.testclient import TestClient
with patch("infisical_sdk.InfisicalSDKClient", side_effect=AssertionError("Infisical used")):
    from app.main import app
    from app.helpers.database import SessionLocal, engine
    from app.helpers.sandbox import seed_user
    from app.helpers.auth import get_authenticated_user
    from app.models import User, Base
    assert engine.url.drivername == "sqlite"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = User(sub="preview-test")
        db.add(user)
        db.commit()
        seed_user(db, user.id)
    client = TestClient(app)
    assert client.get("/health").json()["sandbox"] is True
    assert client.get("/v1/configuration/list").status_code == 403
    headers = {"Origin": "https://pr-41.infraspend.pages.dev",
               "Access-Control-Request-Method": "GET",
               "Access-Control-Request-Headers": "authorization,content-type"}
    assert client.options("/v1/configuration/list", headers=headers).status_code == 200
    headers["Origin"] = "https://pr-41.infraspend.pages.dev.evil.com"
    assert client.options("/v1/configuration/list", headers=headers).status_code == 400
    app.dependency_overrides[get_authenticated_user] = lambda: {"sub": "preview-test"}
    assert len(client.get("/v1/configuration/list").json()["data"]) == 3
    response = client.get("/v1/vendors-metrics/aws")
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 12
    assert client.get("/v1/budget-plans?vendor=aws").status_code == 200
    response = client.post("/v1/configuration/aws", json={
        "aws_access_key_id": "fake", "aws_secret_access_key": "fake"})
    assert response.status_code == 403, response.text
    Base.metadata.drop_all(engine)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "PREVIEW_SANDBOX": "true",
            "AUTH0_DOMAIN": "test.auth0.com",
            "AUTH0_AUDIENCE": "https://test-api",
            "DATABASE_URL": "postgresql://invalid",
            "PREVIEW_DB_PATH": str(tmp_path / "preview.db"),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
