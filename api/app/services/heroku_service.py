"""Heroku service module for handling Heroku Platform API interactions."""

import logging
from datetime import datetime
from typing import Any, Dict
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

from app.helpers.secrets_service import SecretsService
from app.models import HerokuAPIConfiguration

logger = logging.getLogger(__name__)


class HerokuService:
    base_url = "https://api.heroku.com"

    def __init__(
        self, user_id: int, db: Session, identifier: str = "Default Configuration"
    ):
        config = (
            db.query(HerokuAPIConfiguration)
            .filter(HerokuAPIConfiguration.user_id == user_id)
            .filter(HerokuAPIConfiguration.identifier == identifier)
            .first()
        )

        if not config:
            raise Exception(
                "No Heroku configuration found for this user "
                f"with identifier {identifier}"
            )

        secrets = SecretsService()
        self.api_key = secrets.get_customer_secret(config.api_key)
        self.team_name_or_id = (config.team_name_or_id or "").strip() or None

        if not self.api_key:
            raise Exception("Heroku API key not found")

    @staticmethod
    def _add_months(date: datetime, months: int) -> datetime:
        month_index = date.month - 1 + months
        year = date.year + month_index // 12
        month = month_index % 12 + 1
        return datetime(year, month, 1)

    @staticmethod
    def _month_start(month_year: str) -> datetime:
        month, year = month_year.split("-")
        return datetime(int(year), int(month), 1)

    @staticmethod
    def _parse_invoice_month(invoice: dict[str, Any]) -> datetime | None:
        period_start = invoice.get("period_start")
        if period_start:
            return datetime.strptime(period_start, "%m/%d/%Y").replace(day=1)

        created_at = invoice.get("created_at")
        if created_at:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(
                day=1, tzinfo=None
            )

        return None

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _invoices_url(self) -> str:
        if self.team_name_or_id:
            team = quote(self.team_name_or_id, safe="")
            return f"{self.base_url}/teams/{team}/invoices"
        return f"{self.base_url}/account/invoices"

    def _invoice_total(self, invoice: dict[str, Any]) -> float:
        total = invoice.get("total", invoice.get("charges_total", 0))
        total_cost = float(total or 0)

        # Team invoice totals are returned as integer cents by the Platform API.
        if self.team_name_or_id:
            total_cost = total_cost / 100

        return round(total_cost, 2)

    def get_monthly_costs(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> Dict[str, Any]:
        """
        Get monthly costs from Heroku invoices.
        start_date and end_date format: MM-YYYY.
        """
        try:
            end_month = (
                self._month_start(end_date)
                if end_date
                else datetime.utcnow().replace(day=1)
            )
            start_month = (
                self._month_start(start_date)
                if start_date
                else self._add_months(end_month, -12)
            )

            response = requests.get(
                self._invoices_url(),
                headers=self._headers(),
                timeout=30,
            )

            logger.info("Heroku API Response - Status: %s", response.status_code)

            if response.status_code != 200:
                error_msg = (
                    response.json()
                    if response.content
                    else "No error details available"
                )
                logger.error("Heroku API error: %s", error_msg)
                raise Exception(f"Failed to retrieve Heroku costs: {error_msg}")

            monthly_costs = []
            for invoice in response.json():
                invoice_month = self._parse_invoice_month(invoice)
                if not invoice_month:
                    continue

                if start_month <= invoice_month <= end_month:
                    monthly_costs.append(
                        {
                            "month": invoice_month.strftime("%m-%Y"),
                            "cost": self._invoice_total(invoice),
                        }
                    )

            monthly_costs.sort(
                key=lambda item: datetime.strptime(item["month"], "%m-%Y")
            )

            return {"data": monthly_costs}
        except Exception as e:
            logger.error("Error fetching Heroku costs: %s", str(e))
            raise Exception(f"Failed to retrieve Heroku costs: {str(e)}")
