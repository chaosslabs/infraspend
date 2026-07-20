import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from app.services.vendor_metrics_service import VendorMetricsService
from app.models import (
    VendorMetrics,
    User,
    AWSAPIConfiguration,
    DatadogAPIConfiguration,
    HerokuAPIConfiguration,
)


@pytest.fixture
def mock_db():
    db = Mock()
    # Setup query.all() to return an empty list by default
    db.query.return_value.all.return_value = []
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
        []
    )
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        Mock()
    )
    return db


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = 1
    return user


@pytest.fixture
def mock_aws_config():
    config = Mock(spec=AWSAPIConfiguration)
    config.identifier = "test-aws"
    return config


@pytest.fixture
def mock_datadog_config():
    config = Mock(spec=DatadogAPIConfiguration)
    config.identifier = "test-datadog"
    return config


@pytest.fixture
def mock_heroku_config():
    config = Mock(spec=HerokuAPIConfiguration)
    config.identifier = "test-heroku"
    return config


@pytest.fixture
def mock_costs_response():
    current_year = datetime.now().year
    return {
        "data": [
            {"month": f"01-{current_year}", "cost": 100.0},
            {"month": f"02-{current_year}", "cost": 200.0},
        ]
    }


def make_metric(month: str, cost: float, updated_at: datetime | None = None):
    metric = Mock(spec=VendorMetrics)
    metric.month = month
    metric.cost = cost
    metric.updated_at = updated_at or datetime.utcnow()
    return metric


def required_months():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    months = []
    current_date = start_date
    while current_date <= end_date:
        months.append(current_date.strftime("%m-%Y"))
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    return months


def configure_metrics_query(mock_db, stored_metrics, all_metrics):
    metrics_query = mock_db.query.return_value
    metrics_filter = metrics_query.filter.return_value
    metrics_order = metrics_filter.order_by.return_value
    metrics_order.all.side_effect = [stored_metrics, all_metrics]


class TestVendorMetricsService:
    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_aws_success(
        self, mock_db, mock_user, mock_costs_response
    ):
        """
        GIVEN a VendorMetricsService instance and AWS vendor
        WHEN get_and_store_vendor_metrics is called
        THEN it should fetch costs and store them in the database
        """
        # GIVEN
        service = VendorMetricsService(mock_user.id, mock_db)
        all_metrics = [
            make_metric(item["month"], item["cost"])
            for item in mock_costs_response["data"]
        ]
        configure_metrics_query(mock_db, [], all_metrics)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            # WHEN
            result = await service.get_and_store_vendor_metrics("aws", "test-config")

            # THEN
            assert result == mock_costs_response
            assert mock_db.add.call_count == 2  # Two months of data
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_datadog_success(
        self, mock_db, mock_user, mock_costs_response
    ):
        """
        GIVEN a VendorMetricsService instance and Datadog vendor
        WHEN get_and_store_vendor_metrics is called
        THEN it should fetch costs and store them in the database
        """
        # GIVEN
        service = VendorMetricsService(mock_user.id, mock_db)
        all_metrics = [
            make_metric(item["month"], item["cost"])
            for item in mock_costs_response["data"]
        ]
        configure_metrics_query(mock_db, [], all_metrics)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "app.services.vendor_metrics_service.DatadogService",
            autospec=True,
        ) as mock_dd_service:
            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.return_value = mock_costs_response
            mock_dd_service.return_value = mock_dd_instance

            # WHEN
            result = await service.get_and_store_vendor_metrics(
                "datadog", "test-config"
            )

            # THEN
            assert result == mock_costs_response
            assert mock_db.add.call_count == 2  # Two months of data
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_heroku_success(
        self, mock_db, mock_user, mock_costs_response
    ):
        """
        GIVEN a VendorMetricsService instance and Heroku vendor
        WHEN get_and_store_vendor_metrics is called
        THEN it should fetch costs and store them in the database
        """
        # GIVEN
        service = VendorMetricsService(mock_user.id, mock_db)
        all_metrics = [
            make_metric(item["month"], item["cost"])
            for item in mock_costs_response["data"]
        ]
        configure_metrics_query(mock_db, [], all_metrics)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "app.services.vendor_metrics_service.HerokuService",
            autospec=True,
        ) as mock_heroku_service:
            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = mock_costs_response
            mock_heroku_service.return_value = mock_heroku_instance

            # WHEN
            result = await service.get_and_store_vendor_metrics("heroku", "test-config")

            # THEN
            assert result == mock_costs_response
            assert mock_db.add.call_count == 2  # Two months of data
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_update_existing(
        self, mock_db, mock_user, mock_costs_response
    ):
        """
        GIVEN a VendorMetricsService instance and existing metrics
        WHEN get_and_store_vendor_metrics is called
        THEN it should update existing metrics instead of creating new ones
        """
        # GIVEN
        service = VendorMetricsService(mock_user.id, mock_db)
        current_month = datetime.now().strftime("%m-%Y")
        existing_metric = make_metric(
            current_month, 25.0, datetime.utcnow() - timedelta(days=2)
        )
        stored_metrics = [
            make_metric(month, 10.0)
            for month in required_months()
            if month != current_month
        ] + [existing_metric]
        mock_costs_response["data"] = [{"month": current_month, "cost": 300.0}]
        configure_metrics_query(mock_db, stored_metrics, stored_metrics)
        mock_db.query.return_value.filter.return_value.first.return_value = (
            existing_metric
        )

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            # WHEN
            result = await service.get_and_store_vendor_metrics("aws", "test-config")

            # THEN
            assert any(
                item["month"] == current_month and item["cost"] == 300.0
                for item in result["data"]
            )
            mock_db.add.assert_not_called()  # Should not add new records
            mock_db.commit.assert_called_once()
            assert existing_metric.cost == mock_costs_response["data"][0]["cost"]

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_invalid_vendor(
        self, mock_db, mock_user
    ):
        """
        GIVEN a VendorMetricsService instance
        WHEN get_and_store_vendor_metrics is called with invalid vendor
        THEN it should raise ValueError
        """
        # GIVEN
        service = VendorMetricsService(mock_user.id, mock_db)
        configure_metrics_query(mock_db, [], [])

        # WHEN/THEN
        with pytest.raises(ValueError, match="Unsupported vendor: invalid"):
            await service.get_and_store_vendor_metrics("invalid", "test-config")

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_success(
        self,
        mock_db,
        mock_user,
        mock_aws_config,
        mock_datadog_config,
        mock_heroku_config,
        mock_costs_response,
    ):
        """
        GIVEN a database with users and their configurations
        WHEN batch_update_all_vendor_metrics is called
        THEN it should update metrics for all users and configurations
        """
        # GIVEN
        mock_db.query.return_value.all.side_effect = [
            [mock_user],  # Users query
        ]
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [mock_aws_config],  # AWS configs query
            [mock_datadog_config],  # Datadog configs query
            [mock_heroku_config],  # Heroku configs query
        ]

        with patch.object(
            VendorMetricsService,
            "get_and_store_vendor_metrics",
            new_callable=AsyncMock,
            return_value=mock_costs_response,
        ):
            # WHEN
            results = await VendorMetricsService.batch_update_all_vendor_metrics(
                mock_db
            )

            # THEN
            assert len(results["success"]) == 3  # One success message for each config
            assert len(results["failed"]) == 0
            assert any("AWS metrics updated" in msg for msg in results["success"])
            assert any("Datadog metrics updated" in msg for msg in results["success"])
            assert any("Heroku metrics updated" in msg for msg in results["success"])

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_partial_failure(
        self,
        mock_db,
        mock_user,
        mock_aws_config,
        mock_datadog_config,
        mock_costs_response,
    ):
        """
        GIVEN a database with users and their configurations
        WHEN batch_update_all_vendor_metrics is called and some updates fail
        THEN it should handle errors gracefully and continue processing
        """
        # GIVEN
        mock_db.query.return_value.all.side_effect = [
            [mock_user],  # Users query
        ]
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [mock_aws_config],  # AWS configs query
            [mock_datadog_config],  # Datadog configs query
            [],  # Heroku configs query
        ]

        with patch.object(
            VendorMetricsService,
            "get_and_store_vendor_metrics",
            new_callable=AsyncMock,
            side_effect=[mock_costs_response, Exception("Datadog API error")],
        ):
            # WHEN
            results = await VendorMetricsService.batch_update_all_vendor_metrics(
                mock_db
            )

            # THEN
            assert len(results["success"]) == 1  # AWS update succeeded
            assert len(results["failed"]) == 1  # Datadog update failed
            assert any("AWS metrics updated" in msg for msg in results["success"])
            assert any(
                "Failed to update Datadog metrics" in msg for msg in results["failed"]
            )
