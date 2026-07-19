from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import VendorMetrics, User, DatadogAPIConfiguration, AWSAPIConfiguration
from app.services.aws_service import AWSService
from app.services.datadog_service import DatadogService
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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

                # Update AWS metrics for each configuration
                aws_configs = (
                    db.query(AWSAPIConfiguration)
                    .filter(AWSAPIConfiguration.user_id == user.id)
                    .all()
                )

                for config in aws_configs:
                    try:
                        await service.get_and_store_vendor_metrics(
                            "aws", config.identifier
                        )
                        msg = f"AWS metrics updated for user {user.id}, config {config.identifier}"
                        results["success"].append(msg)
                    except Exception as e:
                        error_msg = (
                            f"Failed to update AWS metrics for user {user.id}, "
                            f"config {config.identifier}: {str(e)}"
                        )
                        logger.error(error_msg)
                        results["failed"].append(error_msg)

                # Update Datadog metrics for each configuration
                datadog_configs = (
                    db.query(DatadogAPIConfiguration)
                    .filter(DatadogAPIConfiguration.user_id == user.id)
                    .all()
                )

                for config in datadog_configs:
                    try:
                        await service.get_and_store_vendor_metrics(
                            "datadog", config.identifier
                        )
                        msg = (
                            f"Datadog metrics updated for user {user.id}, "
                            f"config {config.identifier}"
                        )
                        results["success"].append(msg)
                    except Exception as e:
                        error_msg = (
                            f"Failed to update Datadog metrics for user {user.id}, "
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
        if vendor not in {"aws", "datadog"}:
            raise ValueError(f"Unsupported vendor: {vendor}")

        try:
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

        except ValueError:
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
        if vendor.lower() == "datadog":
            service = DatadogService(self.user_id, self.db, identifier)
            return service.get_monthly_costs(start_date, end_date)
        elif vendor.lower() == "aws":
            service = AWSService(self.user_id, self.db, identifier)
            return service.get_monthly_costs(start_date, end_date)
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")

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
