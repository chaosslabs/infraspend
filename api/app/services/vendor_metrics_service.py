from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import (
    VendorMetrics,
    User,
    DatadogAPIConfiguration,
    AWSAPIConfiguration,
    HerokuAPIConfiguration,
)
from app.services.aws_service import AWSService
from app.services.datadog_service import DatadogService
from app.services.heroku_service import HerokuService
from app.services.monthly_costs import parse_iso_date, validate_monthly_cost_record
from typing import List, Dict
from datetime import datetime, timedelta
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

            # Get stored metrics
            stored_metrics = (
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

            # Track the outcome of the refresh attempt so cached, partial, or
            # failed source data can never look silently current downstream.
            attempt_status = "success"

            if missing_months:
                try:
                    # Get costs for missing months
                    earliest_missing = min(
                        missing_months, key=lambda x: datetime.strptime(x, "%m-%Y")
                    )
                    latest_missing = max(
                        missing_months, key=lambda x: datetime.strptime(x, "%m-%Y")
                    )

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

                    costs = self._get_vendor_costs(
                        vendor,
                        identifier,
                        start_date=earliest_missing,
                        end_date=latest_missing,
                    )
                    if inspect.isawaitable(costs):
                        costs = await costs

                    # Store new metrics
                    self._store_metrics(vendor, identifier, costs["data"])

                    # If we asked to refresh the latest month but the vendor did
                    # not return it, the refresh only partially succeeded.
                    returned_months = {c["month"] for c in costs.get("data", [])}
                    if (
                        current_month in missing_months
                        and current_month not in returned_months
                    ):
                        attempt_status = "partial"
                except Exception as refresh_error:
                    if not had_cache:
                        # No cached data to fall back to; surface the failure.
                        raise
                    # Serve cached metrics, but mark the latest attempt as failed
                    # so the dashboard can label the data as stale/cached.
                    logger.warning(
                        "Refresh for %s/%s failed; serving cached metrics: %s",
                        vendor,
                        identifier,
                        refresh_error,
                    )
                    attempt_status = "failed"

            # Return all metrics (stored + new)
            all_metrics = (
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

            data = [
                _serialize_metric(metric)
                for metric in all_metrics
                if datetime.strptime(metric.month, "%m-%Y").year
                > datetime.now().year - 2
            ]

            # Freshness derived from stored write timestamps. Missing data stays
            # absent (never zero-filled) so a gap cannot read as $0 spend.
            last_success_at = max((m.updated_at for m in all_metrics), default=None)
            data_through = (
                max(data, key=lambda d: datetime.strptime(d["month"], "%m-%Y"))["month"]
                if data
                else None
            )

            return {
                "data": data,
                "last_success_at": _iso_utc(last_success_at),
                "last_attempt_at": _iso_utc(datetime.utcnow()),
                "last_attempt_status": attempt_status,
                "data_through": data_through,
                "record_count": len(data),
                "stale_after_hours": FRESHNESS_STALE_HOURS,
            }

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

    def _store_metrics(self, vendor: str, identifier: str, cost_data: list):
        """Store metrics in the database"""
        for cost_item in cost_data:
            cost_record = validate_monthly_cost_record(
                cost_item, expected_provider=vendor.lower()
            )
            source_period_start = parse_iso_date(
                cost_record["period_start"], "period_start"
            )
            source_period_end = parse_iso_date(cost_record["period_end"], "period_end")
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

        self.db.commit()
