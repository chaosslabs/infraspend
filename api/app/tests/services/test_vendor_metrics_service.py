from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import (
    AWSAPIConfiguration,
    Base,
    DatadogAPIConfiguration,
    HerokuAPIConfiguration,
    User,
    VendorMetricIngestionRun,
    VendorMetrics,
)
from app.services.monthly_costs import build_monthly_cost_record
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


def required_months_for_service():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    current_date = start_date
    months = []
    while current_date <= end_date:
        months.append(current_date.strftime("%m-%Y"))
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    return months


def add_successful_ingestion_run(
    db_session,
    user,
    vendor="aws",
    identifier="test-config",
    completed_at=None,
):
    completed_at = completed_at or datetime.utcnow()
    run = VendorMetricIngestionRun(
        user_id=user.id,
        vendor=vendor,
        identifier=identifier,
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        requested_period_start=completed_at.date().replace(day=1),
        requested_period_end=shift_month(completed_at, 1).date(),
        source_period_start=completed_at.date().replace(day=1),
        source_period_end=shift_month(completed_at, 1).date(),
        status="success",
        records_received=1,
        records_stored=1,
    )
    db_session.add(run)
    db_session.commit()
    return run


def seed_required_metrics(db_session, user, vendor="aws", identifier="test-config"):
    for index, month in enumerate(required_months_for_service()):
        db_session.add(
            VendorMetrics(
                user_id=user.id,
                vendor=vendor,
                identifier=identifier,
                month=month,
                cost=100 + index,
            )
        )
    db_session.commit()


@pytest.fixture
def cost_response_for():
    current_month = datetime.now().replace(day=1)
    previous_month = shift_month(current_month, -1)

    def _factory(provider):
        return {
            "data": [
                build_monthly_cost_record(
                    provider=provider,
                    period_start=previous_month.date(),
                    period_end=shift_month(previous_month, 1).date(),
                    cost=100.0,
                    currency="USD" if provider == "aws" else None,
                ),
                build_monthly_cost_record(
                    provider=provider,
                    period_start=current_month.date(),
                    period_end=shift_month(current_month, 1).date(),
                    cost=200.0,
                    currency="USD" if provider == "aws" else None,
                ),
            ]
        }

    return _factory


def metrics_by_month(response):
    return {item["month"]: item["cost"] for item in response["data"]}


def lineage_by_month(response):
    return {item["month"]: item for item in response["data"]}


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


def test_ingestion_run_complete_validates_terminal_transition(user):
    run = VendorMetricIngestionRun(
        user_id=user.id,
        vendor="aws",
        identifier="test-config",
        status="running",
    )

    run.complete(
        status="success",
        completed_at=datetime.utcnow(),
        records_received=2,
        records_stored=2,
    )

    assert run.status == "success"
    assert run.completed_at is not None
    with pytest.raises(ValueError, match="Only running ingestion runs"):
        run.complete(status="failed", completed_at=datetime.utcnow())


def test_ingestion_run_rejects_unknown_status(user):
    run = VendorMetricIngestionRun(
        user_id=user.id,
        vendor="aws",
        identifier="test-config",
        status="running",
    )

    with pytest.raises(ValueError, match="Invalid terminal ingestion status"):
        run.complete(status="greenish", completed_at=datetime.utcnow())


class TestVendorMetricsService:
    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_aws_success(
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        mock_costs_response = cost_response_for("aws")

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
        run = db_session.query(VendorMetricIngestionRun).one()
        assert run.user_id == user.id
        assert run.vendor == "aws"
        assert run.identifier == "test-config"
        assert run.status == "success"
        assert run.completed_at is not None
        assert run.requested_period_start is not None
        assert run.requested_period_end is not None
        assert run.records_received == 2
        assert run.records_stored == 2
        assert run.error_category is None
        stored_metric = (
            db_session.query(VendorMetrics)
            .filter(VendorMetrics.month == mock_costs_response["data"][0]["month"])
            .first()
        )
        assert stored_metric.source_provider == "aws"
        assert (
            stored_metric.source_period_start.isoformat()
            == mock_costs_response["data"][0]["period_start"]
        )
        assert (
            stored_metric.source_period_end.isoformat()
            == mock_costs_response["data"][0]["period_end"]
        )
        assert stored_metric.provider_currency == "USD"
        result_metric = lineage_by_month(result)[
            mock_costs_response["data"][0]["month"]
        ]
        assert result_metric["source_provider"] == "aws"
        assert (
            result_metric["source_period_start"]
            == mock_costs_response["data"][0]["period_start"]
        )
        assert (
            result_metric["source_period_end"]
            == mock_costs_response["data"][0]["period_end"]
        )
        assert result_metric["provider_currency"] == "USD"
        assert (
            run.source_period_start.isoformat()
            == mock_costs_response["data"][0]["period_start"]
        )
        assert (
            run.source_period_end.isoformat()
            == mock_costs_response["data"][1]["period_end"]
        )
        assert (
            result["last_success_at"]
            == run.completed_at.replace(microsecond=0).isoformat() + "Z"
        )
        assert result["last_attempt_at"] == result["last_success_at"]
        assert result["last_attempt_status"] == "success"
        mock_aws_instance.get_monthly_costs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_datadog_success(
        self, db_session, user, cost_response_for
    ):
        add_datadog_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        mock_costs_response = cost_response_for("datadog")

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
        self, db_session, user, cost_response_for
    ):
        add_heroku_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        mock_costs_response = cost_response_for("heroku")

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
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        mock_costs_response = cost_response_for("aws")
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
        assert existing_metric.source_provider == "aws"
        assert (
            existing_metric.source_period_start.isoformat()
            == mock_costs_response["data"][0]["period_start"]
        )
        assert (
            existing_metric.source_period_end.isoformat()
            == mock_costs_response["data"][0]["period_end"]
        )
        assert existing_metric.provider_currency == "USD"
        assert metrics_by_month(result) == metrics_by_month(mock_costs_response)
        assert db_session.query(VendorMetrics).count() == 2

    @pytest.mark.asyncio
    async def test_historical_metrics_with_unknown_lineage_are_explicit(
        self, db_session, user
    ):
        add_aws_config(db_session, user)
        previous_month = shift_month(datetime.now().replace(day=1), -1).strftime(
            "%m-%Y"
        )
        db_session.add(
            VendorMetrics(
                user_id=user.id,
                vendor="aws",
                identifier="test-config",
                month=previous_month,
                cost=42.0,
            )
        )
        db_session.commit()

        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = {"data": []}
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        historical_metric = lineage_by_month(result)[previous_month]
        assert historical_metric["source_provider"] == "unknown"
        assert historical_metric["source_period_start"] is None
        assert historical_metric["source_period_end"] is None
        assert historical_metric["provider_currency"] is None

    def test_uniqueness_by_user_vendor_identifier_and_month_remains_enforced(
        self, db_session, user
    ):
        first_metric = VendorMetrics(
            user_id=user.id,
            vendor="aws",
            identifier="test-config",
            month="01-2026",
            cost=10.0,
            source_provider="aws",
        )
        duplicate_metric = VendorMetrics(
            user_id=user.id,
            vendor="aws",
            identifier="test-config",
            month="01-2026",
            cost=20.0,
            source_provider="aws",
        )
        db_session.add(first_metric)
        db_session.commit()

        db_session.add(duplicate_metric)
        with pytest.raises(IntegrityError):
            db_session.commit()

    @pytest.mark.asyncio
    async def test_response_includes_freshness_fields_on_success(
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)
        mock_costs_response = cost_response_for("aws")
        current_month = datetime.now().replace(day=1).strftime("%m-%Y")

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = mock_costs_response
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        assert result["last_attempt_status"] == "success"
        assert result["last_success_at"] is not None
        assert result["last_attempt_at"] is not None
        assert result["record_count"] == 2
        assert result["data_through"] == current_month
        assert result["stale_after_hours"] == 48

    @pytest.mark.asyncio
    async def test_failed_refresh_serves_cached_data(self, db_session, user):
        add_aws_config(db_session, user)
        previous_month = shift_month(datetime.now().replace(day=1), -1).strftime(
            "%m-%Y"
        )
        prior_success = add_successful_ingestion_run(
            db_session,
            user,
            completed_at=datetime.utcnow() - timedelta(hours=2),
        )
        db_session.add(
            VendorMetrics(
                user_id=user.id,
                vendor="aws",
                identifier="test-config",
                month=previous_month,
                cost=42.0,
            )
        )
        db_session.commit()

        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.side_effect = Exception(
                "vendor down sentinel-secret-token"
            )
            mock_aws_service.return_value = mock_aws_instance

            # Must not raise: cached data is served with a failed-attempt label.
            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        assert result["last_attempt_status"] == "failed"
        assert result["record_count"] == 1
        assert metrics_by_month(result) == {previous_month: 42.0}
        assert (
            result["last_success_at"]
            == prior_success.completed_at.replace(microsecond=0).isoformat() + "Z"
        )
        runs = (
            db_session.query(VendorMetricIngestionRun)
            .order_by(VendorMetricIngestionRun.started_at)
            .all()
        )
        assert [run.status for run in runs] == ["success", "failed"]
        assert runs[-1].error_category == "provider_error"
        assert "sentinel-secret-token" not in (runs[-1].error_category or "")

    @pytest.mark.asyncio
    async def test_failed_refresh_without_cache_raises(self, db_session, user):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.side_effect = Exception(
                "vendor down sentinel-secret-token"
            )
            mock_aws_service.return_value = mock_aws_instance

            # No cached data to fall back to: the failure must surface.
            with pytest.raises(Exception, match="Failed to get and store aws metrics"):
                await service.get_and_store_vendor_metrics("aws", "test-config")

        run = db_session.query(VendorMetricIngestionRun).one()
        assert run.status == "failed"
        assert run.completed_at is not None
        assert run.records_received == 0
        assert run.records_stored == 0
        assert run.error_category == "provider_error"
        assert "sentinel-secret-token" not in (run.error_category or "")

    @pytest.mark.asyncio
    async def test_storage_failure_completes_failed_run_and_preserves_cache(
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user)
        previous_month = shift_month(datetime.now().replace(day=1), -1).strftime(
            "%m-%Y"
        )
        prior_success = add_successful_ingestion_run(
            db_session,
            user,
            completed_at=datetime.utcnow() - timedelta(hours=2),
        )
        db_session.add(
            VendorMetrics(
                user_id=user.id,
                vendor="aws",
                identifier="test-config",
                month=previous_month,
                cost=42.0,
            )
        )
        db_session.commit()

        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service, patch.object(
            service,
            "_store_metrics",
            side_effect=Exception("database wrote sentinel-secret-token"),
        ):
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = cost_response_for("aws")
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        assert result["last_attempt_status"] == "failed"
        assert (
            result["last_success_at"]
            == prior_success.completed_at.replace(microsecond=0).isoformat() + "Z"
        )
        assert metrics_by_month(result) == {previous_month: 42.0}
        failed_run = (
            db_session.query(VendorMetricIngestionRun)
            .filter(VendorMetricIngestionRun.status == "failed")
            .one()
        )
        assert failed_run.records_received == 2
        assert failed_run.records_stored == 0
        assert failed_run.error_category == "storage_error"
        assert "sentinel-secret-token" not in (failed_run.error_category or "")

    @pytest.mark.asyncio
    async def test_partial_refresh_when_current_month_missing(self, db_session, user):
        add_aws_config(db_session, user)
        previous_month_date = shift_month(datetime.now().replace(day=1), -1)
        previous_month = previous_month_date.strftime("%m-%Y")
        db_session.add(
            VendorMetrics(
                user_id=user.id,
                vendor="aws",
                identifier="test-config",
                month=previous_month,
                cost=10.0,
            )
        )
        db_session.commit()

        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            # Vendor returns data but omits the current month.
            mock_aws_instance.get_monthly_costs.return_value = {
                "data": [
                    build_monthly_cost_record(
                        provider="aws",
                        period_start=previous_month_date.date(),
                        period_end=shift_month(previous_month_date, 1).date(),
                        cost=100.0,
                        currency="USD",
                    )
                ]
            }
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        assert result["last_attempt_status"] == "partial"
        run = db_session.query(VendorMetricIngestionRun).one()
        assert run.status == "partial"
        assert run.records_received == 1
        assert run.records_stored == 1
        assert run.error_category == "incomplete_source"

    @pytest.mark.asyncio
    async def test_partial_refresh_records_row_validation_failure(
        self, db_session, user
    ):
        add_aws_config(db_session, user)
        previous_month_date = shift_month(datetime.now().replace(day=1), -1)
        current_month_date = datetime.now().replace(day=1)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = {
                "data": [
                    build_monthly_cost_record(
                        provider="aws",
                        period_start=previous_month_date.date(),
                        period_end=shift_month(previous_month_date, 1).date(),
                        cost=100.0,
                        currency="USD",
                    ),
                    {
                        "month": current_month_date.strftime("%m-%Y"),
                        "cost": "not numeric",
                        "provider": "aws",
                        "period_start": current_month_date.date().isoformat(),
                        "period_end": shift_month(current_month_date, 1)
                        .date()
                        .isoformat(),
                        "currency": "USD",
                    },
                ]
            }
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        run = db_session.query(VendorMetricIngestionRun).one()
        assert result["last_attempt_status"] == "partial"
        assert metrics_by_month(result) == {
            previous_month_date.strftime("%m-%Y"): 100.0
        }
        assert run.status == "partial"
        assert run.records_received == 2
        assert run.records_stored == 1
        assert run.error_category == "row_validation"
        assert run.source_period_start == previous_month_date.date()
        assert run.source_period_end == shift_month(previous_month_date, 1).date()

    @pytest.mark.asyncio
    async def test_empty_source_reports_no_records(self, db_session, user):
        add_aws_config(db_session, user)
        service = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            mock_aws_instance = Mock()
            mock_aws_instance.get_monthly_costs.return_value = {"data": []}
            mock_aws_service.return_value = mock_aws_instance

            result = await service.get_and_store_vendor_metrics("aws", "test-config")

        # No successful ingestion produced data; never rendered as zero spend.
        assert result["record_count"] == 0
        assert result["data"] == []
        assert result["data_through"] is None
        assert result["last_success_at"] is None
        assert result["last_attempt_status"] == "partial"
        run = db_session.query(VendorMetricIngestionRun).one()
        assert run.status == "partial"
        assert run.records_received == 0
        assert run.records_stored == 0
        assert run.error_category == "incomplete_source"

    @pytest.mark.asyncio
    async def test_cached_read_recovers_persisted_runs_without_resetting_health(
        self, db_session, user
    ):
        add_aws_config(db_session, user)
        seed_required_metrics(db_session, user)
        now = datetime.utcnow()
        target_success = add_successful_ingestion_run(
            db_session,
            user,
            completed_at=now - timedelta(hours=3),
        )
        target_failed = VendorMetricIngestionRun(
            user_id=user.id,
            vendor="aws",
            identifier="test-config",
            started_at=now - timedelta(hours=1),
            completed_at=now - timedelta(minutes=59),
            requested_period_start=now.date().replace(day=1),
            requested_period_end=shift_month(now, 1).date(),
            status="failed",
            records_received=0,
            records_stored=0,
            error_category="provider_error",
        )
        db_session.add(target_failed)

        other_user = User(sub="other-user")
        db_session.add(other_user)
        db_session.flush()
        add_successful_ingestion_run(
            db_session,
            other_user,
            completed_at=now,
        )
        add_successful_ingestion_run(
            db_session,
            user,
            identifier="other-config",
            completed_at=now,
        )
        db_session.commit()

        new_service_instance = VendorMetricsService(user.id, db_session)

        with patch(
            "app.services.vendor_metrics_service.AWSService",
            autospec=True,
        ) as mock_aws_service:
            result = await new_service_instance.get_and_store_vendor_metrics(
                "aws", "test-config"
            )

        mock_aws_service.assert_not_called()
        assert result["last_attempt_status"] == "failed"
        assert (
            result["last_attempt_at"]
            == target_failed.completed_at.replace(microsecond=0).isoformat() + "Z"
        )
        assert (
            result["last_success_at"]
            == target_success.completed_at.replace(microsecond=0).isoformat() + "Z"
        )
        assert (
            db_session.query(VendorMetricIngestionRun)
            .filter(VendorMetricIngestionRun.user_id == user.id)
            .filter(VendorMetricIngestionRun.vendor == "aws")
            .filter(VendorMetricIngestionRun.identifier == "test-config")
            .count()
            == 2
        )

    @pytest.mark.asyncio
    async def test_get_and_store_vendor_metrics_invalid_vendor(self, db_session, user):
        service = VendorMetricsService(user.id, db_session)

        with pytest.raises(ValueError, match="Unsupported vendor: invalid"):
            await service.get_and_store_vendor_metrics("invalid", "test-config")

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_success(
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user, "test-aws")
        add_datadog_config(db_session, user, "test-datadog")
        add_heroku_config(db_session, user, "test-heroku")
        aws_response = cost_response_for("aws")
        datadog_response = cost_response_for("datadog")
        heroku_response = cost_response_for("heroku")

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
            mock_aws_instance.get_monthly_costs.return_value = aws_response
            mock_aws_service.return_value = mock_aws_instance

            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.return_value = datadog_response
            mock_dd_service.return_value = mock_dd_instance

            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = heroku_response
            mock_heroku_service.return_value = mock_heroku_instance

            results = await VendorMetricsService.batch_update_all_vendor_metrics(
                db_session
            )

        assert len(results["success"]) == 3
        assert len(results["failed"]) == 0
        assert any("AWS metrics updated" in msg for msg in results["success"])
        assert any("Datadog metrics updated" in msg for msg in results["success"])
        assert any("Heroku metrics updated" in msg for msg in results["success"])
        runs = db_session.query(VendorMetricIngestionRun).all()
        assert len(runs) == 3
        assert {(run.vendor, run.identifier, run.status) for run in runs} == {
            ("aws", "test-aws", "success"),
            ("datadog", "test-datadog", "success"),
            ("heroku", "test-heroku", "success"),
        }

    @pytest.mark.asyncio
    async def test_batch_update_all_vendor_metrics_partial_failure(
        self, db_session, user, cost_response_for
    ):
        add_aws_config(db_session, user, "test-aws")
        add_datadog_config(db_session, user, "test-datadog")
        add_heroku_config(db_session, user, "test-heroku")
        aws_response = cost_response_for("aws")
        heroku_response = cost_response_for("heroku")

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
            mock_aws_instance.get_monthly_costs.return_value = aws_response
            mock_aws_service.return_value = mock_aws_instance

            mock_dd_instance = Mock()
            mock_dd_instance.get_monthly_costs.side_effect = Exception(
                "Datadog API error"
            )
            mock_dd_service.return_value = mock_dd_instance

            mock_heroku_instance = Mock()
            mock_heroku_instance.get_monthly_costs.return_value = heroku_response
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
        runs = db_session.query(VendorMetricIngestionRun).all()
        assert len(runs) == 3
        assert {(run.vendor, run.identifier, run.status) for run in runs} == {
            ("aws", "test-aws", "success"),
            ("datadog", "test-datadog", "failed"),
            ("heroku", "test-heroku", "success"),
        }
        failed_run = next(run for run in runs if run.vendor == "datadog")
        assert failed_run.error_category == "provider_error"
