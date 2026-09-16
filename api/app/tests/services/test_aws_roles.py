from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from app.models import AWSAPIConfiguration, User
from app.routers.configuration import AWSConfig, configure_aws, aws_setup
from app.services.aws_service import AWSService, role_client


@pytest.mark.asyncio
async def test_setup_is_stable_and_scoped(monkeypatch):
    monkeypatch.setenv(
        "AWS_INFRASPEND_ROLE_ARN", "arn:aws:iam::111111111111:role/Infraspend"
    )
    user = User(id=1)
    db = Mock()
    db.query.return_value.filter.return_value.with_for_update.return_value.one.return_value = (
        user
    )
    first = await aws_setup(user, db)
    second = await aws_setup(user, db)
    assert first == second
    assert first["external_id"]
    assert (
        first["trust_policy"]["Statement"][0]["Condition"]["StringEquals"][
            "sts:ExternalId"
        ]
        == user.aws_external_id
    )
    assert first["permissions_policy"]["Statement"][0]["Action"] == "ce:GetCostAndUsage"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_failed_probe_preserves_configuration():
    db = Mock()
    with patch(
        "app.routers.configuration.role_client",
        side_effect=RuntimeError("private detail"),
    ):
        with pytest.raises(HTTPException) as error:
            await configure_aws(
                AWSConfig(role_arn="arn:aws:iam::123456789012:role/Costs"),
                User(id=1, aws_external_id="tenant-one"),
                db,
            )
    assert "private detail" not in error.value.detail
    db.commit.assert_not_called()
    db.add.assert_not_called()


def test_role_path_never_reads_customer_keys():
    db = Mock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        AWSAPIConfiguration(role_arn="role", external_id="tenant-one")
    )
    with patch("app.services.aws_service.SecretsService") as secrets, patch(
        "app.services.aws_service.role_client"
    ) as role:
        AWSService(1, db)
        secrets.assert_not_called()
        role.assert_called_once_with("role", "tenant-one", 1)


def test_refresh_includes_external_id_and_session_token():
    sts = Mock()
    sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "temporary",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    }
    session = Mock()
    with patch("app.services.aws_service.boto3.client", return_value=sts), patch(
        "app.services.aws_service.get_session", return_value=session
    ), patch("app.services.aws_service.boto3.Session"):
        role_client("arn:aws:iam::123456789012:role/Costs", "tenant-one", 7)
    credentials = session._credentials.get_frozen_credentials()
    assert credentials.token == "token"
    assert credentials.access_key == "temporary"
    session._credentials._refresh_using()
    assert sts.assume_role.call_count == 2
    assert sts.assume_role.call_args.kwargs["ExternalId"] == "tenant-one"


@pytest.mark.asyncio
async def test_successful_migration_uses_authenticated_tenant_id():
    old = AWSAPIConfiguration(
        id=9, aws_access_key_id="old-key", aws_secret_access_key="old-secret"
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = old
    with patch("app.routers.configuration.role_client") as client:
        result = await configure_aws(
            AWSConfig(role_arn="arn:aws:iam::123456789012:role/Costs"),
            User(id=4, aws_external_id="tenant-four"),
            db,
        )
    client.assert_called_once_with(
        "arn:aws:iam::123456789012:role/Costs", "tenant-four", 4
    )
    assert old.external_id == "tenant-four"
    assert old.aws_access_key_id is None
    assert old.aws_secret_access_key is None
    assert result.id == 9
    db.commit.assert_called_once()


def test_rejects_non_role_arns():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AWSConfig(role_arn="arn:aws:iam::123456789012:root")


def test_role_migration_is_idempotent_and_preserves_legacy_keys():
    from sqlalchemy import create_engine, text
    from app.migrations.add_aws_roles import upgrade
    from app.migrations import MIGRATIONS

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE aws_api_configurations (id INTEGER PRIMARY KEY, "
                "aws_access_key_id VARCHAR, aws_secret_access_key VARCHAR)"
            )
        )
        conn.execute(text("INSERT INTO users VALUES (1)"))
        conn.execute(
            text(
                "INSERT INTO aws_api_configurations VALUES (1, 'legacy-id', 'legacy-ref')"
            )
        )
    with patch("app.migrations.add_aws_roles.engine", engine):
        upgrade()
        upgrade()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT aws_external_id FROM users")).scalar() is None
        assert conn.execute(
            text(
                "SELECT aws_access_key_id, aws_secret_access_key, role_arn, "
                "external_id FROM aws_api_configurations"
            )
        ).one() == ("legacy-id", "legacy-ref", None, None)
    assert upgrade in MIGRATIONS
    engine.dispose()
