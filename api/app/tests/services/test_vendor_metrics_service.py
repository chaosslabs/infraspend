from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    AWSAPIConfiguration,
    Base,
    DatadogAPIConfiguration,
    HerokuAPIConfiguration,
    User,
    VendorMetrics,
)
from app.services.vendor_metrics_service import VendorMetricsService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db_session):
    user = User(sub="test-user-123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def shift_month(date: datetime, months: int) -> datetime:
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    return date.replace(year=year, month=month, day=1)


@pytest.fixture
def mock_costs_response():
    current_month = datetime.now().replace(day=1)
    previous_month = shift_month(current_month, -1)
    return {
        "data": [
            {"month": previous_month.strftime("%m-%Y"), "cost": 100.0},
            {"month": current_month.strftime("%m-%Y"), "cost": 200.0},
        ]
    }


def metrics_by_month(response):
    return {item["month"]: item["cost"] for item in response["data"]}


def add_aws_config(db_session, user, identifier="test-config"):
    config = AWSAPIConfiguration(
        user_id=user.id,
        identifier=identifier,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    db_session.add(config)
    db_session.commit()
    return config


def add_datadog_config(db_session, user, identifier="test-config"):
    config = DatadogAPIConfiguration(
        user_id=user.id,
        identifier=identifier,
        api_key="datadog-key",
        app_key="datadog-app-key",
    )
    db_session.add(config)
    db_session.commit()
    return config


def add_heroku_config(db_session, user, identifier="test-config"):
    config = HerokuAPIConfiguration(
        user_id=user.id,
        identifier=identifier,
        api_key="heroku-key",
    )
    db_session.add(config)
    db_session.commit()
    return config


class TestVendorMetricsService:
    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_aws_success(
        self, db_session, user, mock_costs_response
    ):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        assert metrics_by_month(result) == metrics_by_month(mock_costs_response)
        assert db_session.query(VendorMetrics).count() == 2
        mock_aws_instance.get_monthly_costs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_datadog_success(
        self, db_session, user, mock_costs_response
    ):
        add_datadog_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.DatadogService",
            autospec=True,
        ) as mock_dd_service:
            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.return_value = mock_costs_response
            mock_dd_service.return_value = mock_dd_instance

            result = await service.get_and_store_vendor_metrics(
                "datadog", "test-config"
            )

        assert metrics_by_month(result) == metrics_by_month(mock_costs_response)
        assert db_session.query(VendorMetrics).count() == 2
        mock_dd_instance.get_monthly_costs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_heroku_success(
        self, db_session, user, mock_costs_response
    ):
        add_heroku_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.HerokuService",
            autospec=True,
        ) as mock_heroku_service:
            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = mock_costs_response
            mock_heroku_service.return_value = mock_heroku_instance

            result = await service.get_and_store_vendor_metrics("heroku", "test-config")

        assert metrics_by_month(result) == metrics_by_month(mock_costs_response)
        assert db_session.query(VendorMetrics).count() == 2
        mock_heroku_instance.get_monthly_costs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_update_existing(
        self, db_session, user, mock_costs_response
    ):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        existing_month = mock_costs_response["data"][0]["month"]
        existing_metric = VendorMetrics(
            user_id=user.id,
            vendor="aws",
            identifier="test-config",
            month=existing_month,
            cost=10.0,
        )
        db_session.add(existing_metric)
        db_session.commit()

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        db_session.refresh(existing_metric)
        assert existing_metric.cost == mock_costs_response["data"][0]["cost"]
        assert metrics_by_month(result) == metrics_by_month(mock_costs_response)
        assert db_session.query(VendorMetrics).count() == 2

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_invalid_vendor(self, db_session, user):
        service = VendorMetricsService(user.id, db_session)

        with pytest.raises(ValueError, match="Unsupported vendor: invalid"):
            await service.get_and_store_vendor_metrics("invalid", "test-config")

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_success(
        self, db_session, user, mock_costs_response
    ):
        add_aws_config(db_session, user, "test-aws")
        add_datadog_config(db_session, user, "test-datadog")
        add_heroku_config(db_session, user, "test-heroku")

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service, patch(
            "app.services.vendor_metrics_service.DatadogService",
            autospec=True,
        ) as mock_dd_service, patch(
            "app.services.vendor_metrics_service.HerokuService",
            autospec=True,
        ) as mock_heroku_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.return_value = mock_costs_response
            mock_dd_service.return_value = mock_dd_instance

            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = mock_costs_response
            mock_heroku_service.return_value = mock_heroku_instance

            results = await VendorMetricsService.batch_update_all_vendor_metrics(
                db_session
            )

        assert len(results["success"]) == 3
        assert len(results["failed"]) == 0
        assert any("AWS metrics updated" in msg for msg in results["success"])
        assert any("Datadog metrics updated" in msg for msg in results["success"])
        assert any("Heroku metrics updated" in msg for msg in results["success"])

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_partial_failure(
        self, db_session, user, mock_costs_response
    ):
        add_aws_config(db_session, user, "test-aws")
        add_datadog_config(db_session, user, "test-datadog")
        add_heroku_config(db_session, user, "test-heroku")

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service, patch(
            "app.services.vendor_metrics_service.DatadogService",
            autospec=True,
        ) as mock_dd_service, patch(
            "app.services.vendor_metrics_service.HerokuService",
            autospec=True,
        ) as mock_heroku_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.side_effect = Exception(
                "Datadog API error"
            )
            mock_dd_service.return_value = mock_dd_instance

            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = mock_costs_response
            mock_heroku_service.return_value = mock_heroku_instance

            results = await VendorMetricsService.batch_update_all_vendor_metrics(
                db_session
            )

        assert len(results["success"]) == 2
        assert len(results["failed"]) == 1
        assert any("AWS metrics updated" in msg for msg in results["success"])
        assert any("Heroku metrics updated" in msg for msg in results["success"])
        assert any(
            "Failed to update Datadog metrics" in msg for msg in results["failed"]
        )
