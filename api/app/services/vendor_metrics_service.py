from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import (
    VendorMetrics,
    VendorMetricIngestionRun,
    User,
    DatadogAPIConfiguration,
    AWSAPIConfiguration,
    HerokuAPIConfiguration,
    INGESTION_RUN_RUNNING_STATUS,
)
from app.services.aws_service import AWSService
from app.services.datadog_service import DatadogService
from app.services.heroku_service import HerokuService
from app.services.monthly_costs import parse_iso_date, validate_monthly_cost_record
from dataclasses import dataclass
from typing import Any, List, Dict
from datetime import date, datetime, timedelta
import inspect
import logging
import os

logger = logging.getLogger(__name__)

SUPPORTED_VENDORS = {"aws", "datadog", "heroku"}

# Freshness threshold used by the dashboard to decide when a last-successful
# ingestion is "stale". Documented and configurable rather than hidden in UI
# copy; the backend refreshes the current month once its data is older than a
# day, so 48h leaves one full refresh cycle of tolerance. Returned in the
# metrics payload so the API and dashboard share a single source of truth.
FRESHNESS_STALE_HOURS = int(os.getenv("METRIC_FRESHNESS_STALE_HOURS", "48"))


class VendorConfigurationNotFound(Exception):
    pass


@dataclass
class StoreMetricsResult:
    records_received: int
    records_stored: int
    invalid_records: int
    returned_months: set[str]
    source_period_start: date | None
    source_period_end: date | None


def _iso_utc(dt: datetime | None) -> str | None:
    """Serialise a naive UTC datetime as an explicit-UTC ISO string.

    Stored timestamps are naive UTC (``datetime.utcnow``); appending ``Z``
    ensures clients parse them as UTC rather than local time.
    """
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


def _date_iso(date_value) -> str | None:
    if date_value is None:
        return None
    return date_value.isoformat()


def _serialize_metric(metric: VendorMetrics):
    return {
        "month": metric.month,
        "cost": float(metric.cost),
        "source_provider": metric.source_provider or "unknown",
        "source_period_start": _date_iso(metric.source_period_start),
        "source_period_end": _date_iso(metric.source_period_end),
        "provider_currency": metric.provider_currency,
    }


def _month_start(month: str) -> date:
    return datetime.strptime(month, "%m-%Y").date().replace(day=1)


def _month_after(month: str) -> date:
    start = _month_start(month)
    return (start.replace(day=1) + timedelta(days=32)).replace(day=1)


def _month_sort_key(month: str) -> datetime:
    return datetime.strptime(month, "%m-%Y")


class VendorMetricsService:
    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db

    @classmethod
    async def batch_update_all_vendor_metrics(cls, db: Session) -> Dict[str, List[str]]:
        """Update metrics for all users and their configurations"""
        results: Dict[str, List[str]] = {"success": [], "failed": []}

        try:
            # Get all users with their configurations
            users = db.query(User).all()

            for user in users:
                service = cls(user.id, db)

                vendors = [
                    ("aws", "AWS", AWSAPIConfiguration),
                    ("datadog", "Datadog", DatadogAPIConfiguration),
                    ("heroku", "Heroku", HerokuAPIConfiguration),
                ]

                for vendor, label, config_model in vendors:
                    configs = (
                        db.query(config_model)
                        .filter(config_model.user_id == user.id)
                        .all()
                    )

                    for config in configs:
                        try:
                            await service.get_and_store_vendor_metrics(
                                vendor, config.identifier
                            )
                            msg = (
                                f"{label} metrics updated for user {user.id}, "
                                f"config {config.identifier}"
                            )
                            results["success"].append(msg)
                        except Exception as e:
                            error_msg = (
                                f"Failed to update {label} metrics for user {user.id}, "
                                f"config {config.identifier}: {str(e)}"
                            )
                            logger.error(error_msg)
                            results["failed"].append(error_msg)

        except Exception as e:
            error_msg = f"Batch update failed: {str(e)}"
            logger.error(error_msg)
            results["failed"].append(error_msg)

        return results

    async def get_and_store_vendor_metrics(
        self, vendor: str, identifier: str = "Default Configuration"
    ):
        """Get vendor metrics and store them in the database"""
        vendor = vendor.lower()

        try:
            if vendor not in SUPPORTED_VENDORS:
                raise ValueError(f"Unsupported vendor: {vendor}")

            stored_metrics = self._get_stored_metrics(vendor, identifier)
            had_cache = len(stored_metrics) > 0

            # Calculate date range for last 11 months
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            # Find missing months
            existing_months = {metric.month for metric in stored_metrics}
            required_months = set()
            current_date = start_date
            while current_date <= end_date:
                month_str = current_date.strftime("%m-%Y")
                required_months.add(month_str)
                current_date = (
                    current_date.replace(day=1) + timedelta(days=32)
                ).replace(day=1)

            missing_months = required_months - existing_months

            # Check if current month's data needs refresh
            current_month = end_date.strftime("%m-%Y")
            current_month_metric = next(
                (m for m in stored_metrics if m.month == current_month), None
            )

            if current_month_metric and (
                datetime.utcnow() - current_month_metric.updated_at
            ) > timedelta(days=1):
                # If current month data is older than 1 day, add it to missing months
                missing_months.add(current_month)

            if missing_months:
                # Get costs for missing months
                earliest_missing = min(missing_months, key=_month_sort_key)
                latest_missing = max(missing_months, key=_month_sort_key)

                # If current month needs refresh, also get previous month to
                # ensure complete data
                if current_month in missing_months:
                    earliest_date = datetime.strptime(earliest_missing, "%m-%Y")

                    if (earliest_date - start_date).days > 0:
                        earliest_missing = (
                            earliest_date - timedelta(days=32)
                        ).strftime("%m-%Y")
                    else:
                        earliest_missing = earliest_date.strftime("%m-%Y")

                run = self._start_ingestion_run(
                    vendor,
                    identifier,
                    requested_period_start=_month_start(earliest_missing),
                    requested_period_end=_month_after(latest_missing),
                )

                costs = None
                try:
                    costs = self._get_vendor_costs(
                        vendor,
                        identifier,
                        start_date=earliest_missing,
                        end_date=latest_missing,
                    )
                    if inspect.isawaitable(costs):
                        costs = await costs
                except VendorConfigurationNotFound:
                    self._complete_ingestion_run(
                        run,
                        status="failed",
                        error_category="configuration_error",
                    )
                    raise
                except Exception as provider_error:
                    self._complete_ingestion_run(
                        run,
                        status="failed",
                        error_category="provider_error",
                    )
                    if not had_cache:
                        # No cached data to fall back to; surface the failure.
                        raise
                    # Serve cached metrics, but leave the failed attempt
                    # persisted so future reads keep showing cached/stale data.
                    logger.warning(
                        "Refresh for %s/%s failed; serving cached metrics: %s",
                        vendor,
                        identifier,
                        provider_error,
                    )
                else:
                    cost_data = []
                    try:
                        cost_data = self._extract_cost_data(costs)
                        store_result = self._store_metrics(
                            vendor, identifier, cost_data
                        )
                    except ValueError as row_error:
                        self._complete_ingestion_run(
                            run,
                            status="failed",
                            error_category="row_validation",
                        )
                        if not had_cache:
                            raise Exception(
                                "Vendor cost response failed validation"
                            ) from row_error
                        logger.warning(
                            "Refresh for %s/%s returned malformed rows; "
                            "serving cached metrics: %s",
                            vendor,
                            identifier,
                            row_error,
                        )
                    except Exception as storage_error:
                        self._complete_ingestion_run(
                            run,
                            status="failed",
                            records_received=len(cost_data),
                            error_category="storage_error",
                        )
                        if not had_cache:
                            raise
                        logger.warning(
                            "Refresh for %s/%s could not store metrics; "
                            "serving cached metrics: %s",
                            vendor,
                            identifier,
                            storage_error,
                        )
                    else:
                        attempt_status = "success"
                        error_category = None

                        # If any individual rows were invalid, valid rows still
                        # landed but the source refresh is auditable as partial.
                        if store_result.invalid_records:
                            attempt_status = "partial"
                            error_category = "row_validation"

                        # If we asked to refresh the latest month but the vendor
                        # did not return it, the refresh only partially succeeded.
                        if (
                            current_month in missing_months
                            and current_month not in store_result.returned_months
                        ):
                            attempt_status = "partial"
                            error_category = error_category or "incomplete_source"

                        self._complete_ingestion_run(
                            run,
                            status=attempt_status,
                            records_received=store_result.records_received,
                            records_stored=store_result.records_stored,
                            source_period_start=store_result.source_period_start,
                            source_period_end=store_result.source_period_end,
                            error_category=error_category,
                        )

            return self._build_metrics_response(vendor, identifier)

        except (ValueError, VendorConfigurationNotFound):
            raise
        except Exception as e:
            raise Exception(f"Failed to get and store {vendor} metrics: {str(e)}")

    def _get_vendor_costs(
        self,
        vendor: str,
        identifier: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        """Get costs from the appropriate vendor service"""
        if vendor == "datadog":
            self._ensure_configuration_exists(
                DatadogAPIConfiguration, "Datadog", identifier
            )
            service = DatadogService(self.user_id, self.db, identifier)
            return service.get_monthly_costs(start_date, end_date)
        elif vendor == "aws":
            self._ensure_configuration_exists(AWSAPIConfiguration, "AWS", identifier)
            service = AWSService(self.user_id, self.db, identifier)
            return service.get_monthly_costs(start_date, end_date)
        elif vendor == "heroku":
            self._ensure_configuration_exists(
                HerokuAPIConfiguration, "Heroku", identifier
            )
            service = HerokuService(self.user_id, self.db, identifier)
            return service.get_monthly_costs(start_date, end_date)
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")

    def _ensure_configuration_exists(
        self, config_model, vendor_label: str, identifier: str
    ):
        config = (
            self.db.query(config_model)
            .filter(config_model.user_id == self.user_id)
            .filter(config_model.identifier == identifier)
            .first()
        )

        if not config:
            raise VendorConfigurationNotFound(
                f"{vendor_label} API configuration not found "
                f"for this user with identifier {identifier}"
            )

    def _get_stored_metrics(self, vendor: str, identifier: str):
        return (
            self.db.query(VendorMetrics)
            .filter(
                and_(
                    VendorMetrics.user_id == self.user_id,
                    VendorMetrics.vendor == vendor,
                    VendorMetrics.identifier == identifier,
                )
            )
            .order_by(VendorMetrics.month)
            .all()
        )

    def _start_ingestion_run(
        self,
        vendor: str,
        identifier: str,
        *,
        requested_period_start: date | None = None,
        requested_period_end: date | None = None,
    ) -> VendorMetricIngestionRun:
        run = VendorMetricIngestionRun(
            user_id=self.user_id,
            vendor=vendor,
            identifier=identifier,
            started_at=datetime.utcnow(),
            requested_period_start=requested_period_start,
            requested_period_end=requested_period_end,
            status=INGESTION_RUN_RUNNING_STATUS,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _complete_ingestion_run(
        self,
        run: VendorMetricIngestionRun,
        *,
        status: str,
        records_received: int = 0,
        records_stored: int = 0,
        source_period_start: date | None = None,
        source_period_end: date | None = None,
        error_category: str | None = None,
    ):
        try:
            run.complete(
                status=status,
                completed_at=datetime.utcnow(),
                records_received=records_received,
                records_stored=records_stored,
                source_period_start=source_period_start,
                source_period_end=source_period_end,
                error_category=error_category,
            )
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
        except Exception:
            self.db.rollback()
            raise

    def _extract_cost_data(self, costs: Any) -> list:
        if not isinstance(costs, dict):
            raise ValueError("Vendor cost response must be a mapping")

        cost_data = costs.get("data", [])
        if cost_data is None:
            return []
        if not isinstance(cost_data, list):
            raise ValueError("Vendor cost response data must be a list")
        return cost_data

    def _latest_ingestion_run(
        self, vendor: str, identifier: str, status: str | None = None
    ) -> VendorMetricIngestionRun | None:
        query = self.db.query(VendorMetricIngestionRun).filter(
            and_(
                VendorMetricIngestionRun.user_id == self.user_id,
                VendorMetricIngestionRun.vendor == vendor,
                VendorMetricIngestionRun.identifier == identifier,
            )
        )
        if status:
            query = query.filter(VendorMetricIngestionRun.status == status)
        return query.order_by(
            VendorMetricIngestionRun.started_at.desc(),
            VendorMetricIngestionRun.id.desc(),
        ).first()

    def _build_metrics_response(self, vendor: str, identifier: str):
        all_metrics = self._get_stored_metrics(vendor, identifier)

        data = [
            _serialize_metric(metric)
            for metric in all_metrics
            if datetime.strptime(metric.month, "%m-%Y").year > datetime.now().year - 2
        ]

        latest_attempt = self._latest_ingestion_run(vendor, identifier)
        latest_success = self._latest_ingestion_run(vendor, identifier, "success")
        last_attempt_status = (
            latest_attempt.status
            if latest_attempt and latest_attempt.status != INGESTION_RUN_RUNNING_STATUS
            else None
        )
        last_attempt_at = (
            latest_attempt.completed_at or latest_attempt.started_at
            if latest_attempt
            else None
        )
        last_success_at = latest_success.completed_at if latest_success else None
        data_through = (
            max(data, key=lambda d: datetime.strptime(d["month"], "%m-%Y"))["month"]
            if data
            else None
        )

        return {
            "data": data,
            "last_success_at": _iso_utc(last_success_at),
            "last_attempt_at": _iso_utc(last_attempt_at),
            "last_attempt_status": last_attempt_status,
            "data_through": data_through,
            "record_count": len(data),
            "stale_after_hours": FRESHNESS_STALE_HOURS,
        }

    def _store_metrics(self, vendor: str, identifier: str, cost_data: list):
        """Store metrics in the database"""
        records_stored = 0
        invalid_records = 0
        returned_months: set[str] = set()
        source_period_starts: list[date] = []
        source_period_ends: list[date] = []

        for cost_item in cost_data:
            try:
                cost_record = validate_monthly_cost_record(
                    cost_item, expected_provider=vendor.lower()
                )
                source_period_start = parse_iso_date(
                    cost_record["period_start"], "period_start"
                )
                source_period_end = parse_iso_date(
                    cost_record["period_end"], "period_end"
                )
            except ValueError as exc:
                invalid_records += 1
                logger.warning(
                    "Skipping malformed %s monthly cost row for user %s, "
                    "config %s: %s",
                    vendor,
                    self.user_id,
                    identifier,
                    exc,
                )
                continue

            # Check if metric already exists
            existing_metric = (
                self.db.query(VendorMetrics)
                .filter(
                    and_(
                        VendorMetrics.user_id == self.user_id,
                        VendorMetrics.vendor == vendor.lower(),
                        VendorMetrics.identifier == identifier,
                        VendorMetrics.month == cost_record["month"],
                    )
                )
                .first()
            )

            if existing_metric:
                # Update existing metric
                existing_metric.cost = cost_record["cost"]
                existing_metric.source_provider = cost_record["provider"]
                existing_metric.source_period_start = source_period_start
                existing_metric.source_period_end = source_period_end
                existing_metric.provider_currency = cost_record["currency"]
            else:
                # Create new metric
                metric = VendorMetrics(
                    user_id=self.user_id,
                    vendor=vendor.lower(),
                    identifier=identifier,
                    month=cost_record["month"],
                    cost=cost_record["cost"],
                    source_provider=cost_record["provider"],
                    source_period_start=source_period_start,
                    source_period_end=source_period_end,
                    provider_currency=cost_record["currency"],
                )
                self.db.add(metric)

            records_stored += 1
            returned_months.add(cost_record["month"])
            source_period_starts.append(source_period_start)
            source_period_ends.append(source_period_end)

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return StoreMetricsResult(
            records_received=len(cost_data),
            records_stored=records_stored,
            invalid_records=invalid_records,
            returned_months=returned_months,
            source_period_start=(
                min(source_period_starts) if source_period_starts else None
            ),
            source_period_end=max(source_period_ends) if source_period_ends else None,
        )
