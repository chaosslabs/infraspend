from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import (
    Base,
    User,
    AWSAPIConfiguration,
    DatadogAPIConfiguration,
    HerokuAPIConfiguration,
)
from app.services.configuration_service import ConfigurationService


@pytest.mark.parametrize(
    "vendor,model,values,fields",
    [
        (
            "aws",
            AWSAPIConfiguration,
            {"AWS_ACCESS_KEY_ID": "access", "AWS_SECRET_ACCESS_KEY": "secret"},
            ["aws_access_key_id", "aws_secret_access_key"],
        ),
        (
            "datadog",
            DatadogAPIConfiguration,
            {"DATADOG_APP_KEY": "app", "DATADOG_API_KEY": "key"},
            ["app_key", "api_key"],
        ),
        ("heroku", HerokuAPIConfiguration, {"HEROKU_API_KEY": "key"}, ["api_key"]),
    ],
)
def test_accounts_users_and_legacy_references_remain_independent(
    vendor, model, values, fields
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    stored = {"legacy-reference": "legacy-value"}

    def save(name, value, kind):
        stored[name] = value
        return name

    with Session(engine) as db, patch(
        "app.services.configuration_service.SecretsService"
    ) as secrets:
        secrets.return_value.create_customer_secret.side_effect = save
        user = User(sub="auth0|first")
        other = User(sub="auth0|second")
        db.add_all([user, other])
        db.commit()
        legacy = model(
            user_id=user.id,
            identifier="Legacy",
            **{field: "legacy-reference" for field in fields}
        )
        db.add(legacy)
        db.commit()
        service = ConfigurationService(db, user)
        a, _ = service.configure_vendor(vendor, values, "A")
        first = db.get(model, a)
        names = [getattr(first, field) for field in fields]
        b, _ = service.configure_vendor(
            vendor, {key: "different" for key in values}, "B"
        )
        assert set(names).isdisjoint(
            getattr(db.get(model, b), field) for field in fields
        )
        assert [stored[name] for name in names] == list(values.values())
        assert stored["legacy-reference"] == "legacy-value"
        assert all(getattr(legacy, field) == "legacy-reference" for field in fields)
        updated, _ = service.configure_vendor(
            vendor, {key: "updated" for key in values}, "A"
        )
        assert updated == a
        assert [getattr(first, field) for field in fields] == names
        assert all(stored[name] == "updated" for name in names)
        other_id, _ = ConfigurationService(db, other).configure_vendor(
            vendor, values, "A"
        )
        assert set(names).isdisjoint(
            getattr(db.get(model, other_id), field) for field in fields
        )
        service.configure_vendor(vendor, values, "Legacy")
        assert all(getattr(legacy, field) != "legacy-reference" for field in fields)
        assert stored["legacy-reference"] == "legacy-value"
    engine.dispose()
