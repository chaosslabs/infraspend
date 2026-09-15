from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.helpers.database import get_db
from app.models import Base, User
from app.routers.budget import router, get_user


@pytest.fixture
def budget_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(sub="budget-user")
        db.add(user)
        db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_user] = lambda: user
        yield TestClient(app), db
    engine.dispose()


@pytest.mark.parametrize(
    "vendor", ["aws", "datadog", "heroku", "openai", "anthropic", "claude", "chatgpt"]
)
def test_budget_roundtrip_accounts_and_legacy(budget_client, vendor):
    client, _ = budget_client
    ids = {}
    for identifier, amount in [(None, 500), ("A", 100), ("B", 200), ("A", 125)]:
        response = client.post(
            "/v1/budget-plans",
            json={
                "vendor": vendor,
                "identifier": identifier,
                "budgets": [{"month": "09-2026", "amount": amount}],
            },
        )
        assert response.status_code == 200, response.text
        plan = response.json()["data"]
        if identifier in ids:
            assert plan["id"] == ids[identifier]
        ids[identifier] = plan["id"]
    plans = client.get(f"/v1/budget-plans?vendor={vendor}").json()["data"]
    assert {
        plan["identifier"]: plan["budgets"]["budgets"][0]["amount"] for plan in plans
    } == {None: 500, "A": 125, "B": 200}
    changed = {"vendor": vendor, "identifier": "A", "budgets": []}
    assert client.put(f"/v1/budget-plans/{ids['A']}", json=changed).status_code == 200
    changed["identifier"] = "B"
    assert client.put(f"/v1/budget-plans/{ids['A']}", json=changed).status_code == 400


def test_budget_cross_user_access_denied(budget_client):
    client, db = budget_client
    payload = {"vendor": "openai", "identifier": "A", "budgets": []}
    plan_id = client.post("/v1/budget-plans", json=payload).json()["data"]["id"]
    other = User(sub="other-budget-user")
    db.add(other)
    db.commit()
    client.app.dependency_overrides[get_user] = lambda: other
    assert client.get("/v1/budget-plans?vendor=openai").json()["data"] == []
    assert client.put(f"/v1/budget-plans/{plan_id}", json=payload).status_code == 404
    assert client.delete(f"/v1/budget-plans/{plan_id}").status_code == 404


@pytest.mark.parametrize(
    "entries",
    [
        [{"month": "13-2026", "amount": 1}],
        [{"month": "01-0000", "amount": 1}],
        [{"month": "01-2026", "amount": -1}],
        [{"month": "01-2026", "amount": "NaN"}],
        [{"month": "01-2026", "amount": 1}] * 2,
    ],
)
def test_invalid_budgets_are_rejected(budget_client, entries):
    client, _ = budget_client
    assert (
        client.post(
            "/v1/budget-plans",
            json={"vendor": "openai", "identifier": "A", "budgets": entries},
        ).status_code
        == 422
    )


def test_scope_migration_preserves_legacy_and_is_idempotent():
    from app.migrations.add_budget_account_scope import upgrade

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE budget_plans (id INTEGER PRIMARY KEY, budgets TEXT)")
        )
        connection.execute(text("INSERT INTO budget_plans VALUES (1, 'preserved')"))
    with patch("app.migrations.add_budget_account_scope.engine", engine):
        upgrade()
        upgrade()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT budgets, identifier FROM budget_plans")
        ).one() == ("preserved", None)
    engine.dispose()
