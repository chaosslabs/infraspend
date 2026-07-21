"""DataDog service module for handling DataDog API interactions."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from app.helpers.secrets_service import SecretsService
from sqlalchemy.orm import Session
import requests
from app.models import DatadogAPIConfiguration
from app.services.monthly_costs import add_month, build_monthly_cost_record

logger = logging.getLogger(__name__)


class DatadogService:
    def __init__(
        self, user_id: int, db: Session, identifier: str = "Default Configuration"
    ):
        config = (
            db.query(DatadogAPIConfiguration)
            .filter(DatadogAPIConfiguration.user_id == user_id)
            .filter(DatadogAPIConfiguration.identifier == identifier)
            .first()
        )
        secrets = SecretsService()
        self.app_key = secrets.get_customer_secret(config.app_key)
        self.api_key = secrets.get_customer_secret(config.api_key)
        self.base_url = "https://api.datadoghq.com/api/v1"

    @staticmethod
    def _parse_usage_month_entry(entry: dict[str, Any]):
        attributes = entry.get("attributes")
        if not isinstance(attributes, dict):
            raise ValueError("missing attributes")

        date_value = attributes.get("date")
        if not isinstance(date_value, str):
            raise ValueError("missing attributes.date")

        try:
            period_start = datetime.fromisoformat(
                date_value.replace("Z", "+00:00")
            ).date()
        except ValueError as exc:
            raise ValueError("attributes.date must be ISO-like") from exc

        # Datadog reports one date anchor per monthly row. Preserve that start
        # and derive the exclusive next-month boundary for downstream lineage.
        period_start = period_start.replace(day=1)
        period_end = add_month(period_start)

        return build_monthly_cost_record(
            provider="datadog",
            period_start=period_start,
            period_end=period_end,
            cost=attributes.get("total_cost"),
            currency=None,
        )

    def get_monthly_costs(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> Dict[str, Any]:
        """
        Get monthly costs from Datadog API
        start_date and end_date format: MM-YYYY
        """
        try:
            # Handle end_date
            if end_date:
                # Convert MM-YYYY to YYYY-MM
                month, year = end_date.split("-")
                end_date = f"{year}-{month}"
            else:
                end_date = datetime.utcnow().strftime("%Y-%m")

            # Handle start_date
            if start_date:
                # Convert MM-YYYY to YYYY-MM
                month, year = start_date.split("-")
                start_date = f"{year}-{month}"
            else:
                # Default to 1 year ago
                start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m")

            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
            }

            response = requests.get(
                "https://api.datadoghq.com/api/v2/usage/historical_cost",
                headers=headers,
                params={"start_month": start_date, "end_month": end_date},
            )

            logger.info(f"Datadog API Response - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                monthly_costs = []
                if "data" in data and isinstance(data["data"], list):
                    for entry in data["data"]:
                        try:
                            monthly_costs.append(self._parse_usage_month_entry(entry))
                        except ValueError as exc:
                            logger.warning(
                                "Skipping malformed Datadog cost row: %s", exc
                            )
                return {"data": monthly_costs}
            else:
                error_msg = (
                    response.json()
                    if response.content
                    else "No error details available"
                )
                logger.error(f"Datadog API error: {error_msg}")
                raise Exception(f"Failed to retrieve Datadog costs: {error_msg}")

        except Exception as e:
            logger.error(f"Error fetching Datadog costs: {str(e)}")
            raise Exception(f"Failed to retrieve Datadog costs: {str(e)}")
