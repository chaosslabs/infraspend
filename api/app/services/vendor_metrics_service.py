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
from typing import List, Dict
from datetime import datetime, timedelta
import inspect
import logging

logger = logging.getLogger(__name__)

SUPPORTED_VENDORS = {"aws", "datadog", "heroku"}


class VendorConfigurationNotFound(Exception):
    pass


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
        try:
            vendor = vendor.lower()
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
                earliest_missing = min(
                    missing_months, key=lambda x: datetime.strptime(x, "%m-%Y")
                )
                latest_missing = max(
                    missing_months, key=lambda x: datetime.strptime(x, "%m-%Y")
                )

                # If current month needs refresh, also get previous month to ensure complete data
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

            return {
                "data": [
                    {"month": metric.month, "cost": float(metric.cost)}
                    for metric in all_metrics
                    if datetime.strptime(metric.month, "%m-%Y").year
                    > datetime.now().year - 2
                ]
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
            # Check if metric already exists
            existing_metric = (
                self.db.query(VendorMetrics)
                .filter(
                    and_(
                        VendorMetrics.user_id == self.user_id,
                        VendorMetrics.vendor == vendor.lower(),
                        VendorMetrics.identifier == identifier,
                        VendorMetrics.month == cost_item["month"],
                    )
                )
                .first()
            )

            if existing_metric:
                # Update existing metric
                existing_metric.cost = cost_item["cost"]
            else:
                # Create new metric
                metric = VendorMetrics(
                    user_id=self.user_id,
                    vendor=vendor.lower(),
                    identifier=identifier,
                    month=cost_item["month"],
                    cost=cost_item["cost"],
                )
                self.db.add(metric)

        self.db.commit()
