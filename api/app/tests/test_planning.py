from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.helpers.database import get_db
from app.models import Base, User, PlanningRevision
from app.routers.planning import router
from app.routers.budget import get_user


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(sub="planning-owner")
        db.add(user)
        db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_user] = lambda: user
        yield TestClient(app), db
    engine.dispose()


def payload():
    return {
        "plan_id": str(uuid4()),
        "expected_version": 0,
        "payload": {
            "name": "Assistant",
            "month": "2026-09",
            "budget": 1500,
            "variableCost": 1000,
            "fixedCost": 200,
            "growth": 50,
            "reduction": 25,
            "basis": "Manual estimate",
            "evidence": "Synthetic fixture",
        },
    }


def test_roundtrip_history_conflict_and_tenant_isolation(client):
    http, db = client
    body = payload()
    first = http.post("/v1/planning", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["version"] == 1
    assert http.post("/v1/planning", json=body).status_code == 409
    body["expected_version"] = 1
    body["payload"]["reduction"] = 50
    assert http.post("/v1/planning", json=body).json()["data"]["version"] == 2
    history = http.get(f"/v1/planning/{body['plan_id']}/history").json()["data"]
    assert [r["payload"]["reduction"] for r in history] == [50, 25]
    assert len(http.get("/v1/planning").json()["data"]) == 1
    other = User(sub="other-owner")
    db.add(other)
    db.commit()
    http.app.dependency_overrides[get_user] = lambda: other
    assert http.get("/v1/planning").json()["data"] == []
    assert http.get(f"/v1/planning/{body['plan_id']}/history").status_code == 404
    assert http.post("/v1/planning", json=body).status_code == 409
    assert db.query(PlanningRevision).count() == 2


@pytest.mark.parametrize(
    "key,value",
    [
        ("growth", -101),
        ("reduction", 101),
        ("budget", -1),
        ("variableCost", "NaN"),
        ("fixedCost", "Infinity"),
        ("month", "2026-13"),
        ("name", " "),
    ],
)
def test_rejects_invalid_inputs(client, key, value):
    http, _ = client
    body = payload()
    body["payload"][key] = value
    assert http.post("/v1/planning", json=body).status_code == 422


def test_requires_source_for_reported_costs(client):
    http, _ = client
    body = payload()
    body["payload"].update(basis="Provider-reported", evidence="")
    assert http.post("/v1/planning", json=body).status_code == 422


def test_action_evidence_and_negative_outcomes(client):
    http, _ = client
    body = payload()
    body["payload"]["action"] = {"status": "Measured"}
    assert http.post("/v1/planning", json=body).status_code == 422
    body["payload"]["action"].update(
        title="Test model",
        owner="Team",
        criteria="Acceptance >= 95%",
        baselineWindow="August",
        comparisonWindow="September",
        baselineCost=100,
        baselineUnits=100,
        resultCost=120,
        resultUnits=100,
        quality="Failed",
        notes="Regression, no saving",
    )
    assert http.post("/v1/planning", json=body).status_code == 200


def test_migration_is_idempotent():
    from app.migrations.create_planning_revisions import upgrade

    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with patch("app.migrations.create_planning_revisions.engine", engine):
        upgrade()
        upgrade()
    with Session(engine) as db:
        assert db.query(PlanningRevision).count() == 0
    engine.dispose()
