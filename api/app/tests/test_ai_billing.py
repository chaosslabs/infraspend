from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, User, VendorMetrics, AI_CONFIG_MODELS
from app.routers.configuration import router, get_user
from app.helpers.database import get_db
from app.helpers.auth import get_authenticated_user
from app.routers.forecast import router as forecast_router
from app.routers.vendor_metrics import (
    router as metrics_router,
    get_user as metrics_user,
)


@pytest.fixture
def billing():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(sub="billing-user")
        db.add(user)
        db.commit()
        app = FastAPI()
        app.include_router(router)
        app.include_router(metrics_router)
        app.include_router(forecast_router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_user] = lambda: user
        app.dependency_overrides[metrics_user] = lambda: user
        app.dependency_overrides[get_authenticated_user] = lambda: {"sub": user.sub}
        yield TestClient(app), db, user
    engine.dispose()


@pytest.mark.parametrize("vendor", ["claude", "chatgpt"])
def test_subscription_upsert_preserves_other_months_and_accounts(billing, vendor):
    client, db, user = billing
    for identifier, month, cost in [
        ("A", "01-2026", "20.00"),
        ("A", "02-2026", "22.00"),
        ("B", "01-2026", "30.00"),
        ("A", "01-2026", "25.00"),
    ]:
        result = client.post(
            f"/v1/configuration/subscriptions/{vendor}",
            json={"identifier": identifier, "month": month, "cost": cost},
        )
        assert result.status_code == 200, result.text
    assert db.query(VendorMetrics).count() == 3
    result = client.get(f"/v1/vendors-metrics/{vendor}?identifier=A").json()
    assert result["source_kind"] == "manual_subscription"
    assert result["last_success_at"] is None
    assert [(row["month"], row["cost"]) for row in result["data"]] == [
        ("01-2026", 25),
        ("02-2026", 22),
    ]
    assert result["data"][0]["provider_currency"] == "USD"
    forecast = client.get(f"/v1/vendors-forecast/{vendor}?identifier=A")
    assert forecast.status_code == 200
    assert len(forecast.json()["historical"]) == 2
    assert (
        client.get(f"/v1/vendors-forecast/{vendor}?identifier=missing").status_code
        == 404
    )
    other_user = User(sub="other-user")
    db.add(other_user)
    db.commit()
    client.app.dependency_overrides[metrics_user] = lambda: other_user
    assert client.get(f"/v1/vendors-metrics/{vendor}?identifier=A").status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"cost": -1},
        {"cost": "NaN"},
        {"cost": "1.001"},
        {"currency": "EUR"},
        {"month": "13-2026"},
        {"month": "01-0000"},
        {"month": "01-9999"},
        {"identifier": " "},
    ],
)
def test_invalid_subscription_values_rejected(billing, changes):
    client, db, _ = billing
    result = client.post(
        "/v1/configuration/subscriptions/claude",
        json={"month": "01-2026", "cost": "20", **changes},
    )
    assert result.status_code == 422
    assert db.query(VendorMetrics).count() == 0


@pytest.mark.parametrize("vendor", ["openai", "anthropic"])
def test_api_credentials_are_scoped_and_never_listed(billing, vendor):
    client, db, _ = billing
    with patch("app.routers.configuration.SecretsService") as secrets:
        secrets.return_value.create_customer_secret.side_effect = (
            lambda name, value, kind: name
        )
        for identifier in ("A", "B", "A"):
            assert (
                client.post(
                    f"/v1/configuration/ai/{vendor}",
                    json={"identifier": identifier, "api_key": "test-key"},
                ).status_code
                == 200
            )
        calls = secrets.return_value.create_customer_secret.call_args_list
        assert calls[0].args[0] != calls[1].args[0]
        assert calls[0].args[0] == calls[2].args[0]
        assert db.query(AI_CONFIG_MODELS[vendor]).count() == 2
    configurations = client.get("/v1/configuration/list")
    assert len(configurations.json()["data"]) == 2
    assert "test-key" not in configurations.text
    assert "api_key" not in configurations.text
    assert (
        client.post(f"/v1/configuration/ai/{vendor}", json={"api_key": " "}).status_code
        == 422
    )


def test_ai_migration_is_idempotent_and_registered():
    from app.migrations import MIGRATIONS
    from app.migrations.create_ai_configurations import upgrade

    engine = create_engine("sqlite://")
    Base.metadata.tables["users"].create(engine)
    with patch("app.migrations.create_ai_configurations.engine", engine):
        upgrade()
        upgrade()
    assert upgrade in MIGRATIONS
    for model in AI_CONFIG_MODELS.values():
        assert model.__tablename__ in inspect(engine).get_table_names()
    engine.dispose()


@pytest.mark.parametrize("vendor", ["openai", "anthropic"])
def test_api_ingestion_failure_preserves_cache(billing, vendor):
    from datetime import timedelta
    from app.models import VendorMetricIngestionRun
    from app.services.monthly_costs import add_month

    client, db, user = billing
    db.add(AI_CONFIG_MODELS[vendor](user_id=user.id, identifier="Team", api_key="ref"))
    db.commit()
    month = datetime.utcnow().date().replace(day=1)
    record = {
        "month": month.strftime("%m-%Y"),
        "provider": vendor,
        "cost": 32.15,
        "currency": "USD",
        "period_start": month.isoformat(),
        "period_end": add_month(month).isoformat(),
    }
    with patch("app.services.vendor_metrics_service.AICostService") as service:
        service.return_value.get_monthly_costs.return_value = {"data": [record]}
        result = client.get(f"/v1/vendors-metrics/{vendor}?identifier=Team")
        assert result.status_code == 200, result.text
        assert result.json()["data"][0]["cost"] == 32.15
        assert result.json()["last_attempt_status"] == "success"
        db.query(VendorMetrics).one().updated_at = datetime.utcnow() - timedelta(days=2)
        db.commit()
        service.return_value.get_monthly_costs.side_effect = RuntimeError(
            "Provider unavailable"
        )
        result = client.get(f"/v1/vendors-metrics/{vendor}?identifier=Team")
        assert result.status_code == 200
        assert result.json()["data"][0]["cost"] == 32.15
        assert result.json()["last_attempt_status"] == "failed"
    assert db.query(VendorMetricIngestionRun).count() == 2
