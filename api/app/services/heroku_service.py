"""Heroku service module for handling Heroku Platform API interactions."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

from app.helpers.secrets_service import SecretsService
from app.models import HerokuAPIConfiguration
from app.services.monthly_costs import (
    add_month,
    build_monthly_cost_record,
    decimal_cost,
)

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
    def _add_months(date_value: date, months: int) -> date:
        month_index = date_value.month - 1 + months
        year = date_value.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    @staticmethod
    def _month_start(month_year: str) -> date:
        month, year = month_year.split("-")
        return date(int(year), int(month), 1)

    @staticmethod
    def _parse_heroku_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            return None

        for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                pass

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @classmethod
    def _parse_invoice_period(cls, invoice: dict[str, Any]) -> tuple[date, date] | None:
        period_start = invoice.get("period_start")
        start = cls._parse_heroku_date(period_start)

        if not start:
            created_at = invoice.get("created_at")
            start = cls._parse_heroku_date(created_at)
            if start:
                start = start.replace(day=1)

        if not start:
            return None

        end = cls._parse_heroku_date(invoice.get("period_end"))
        if not end:
            # Some Heroku invoice payloads expose only a monthly anchor. In that
            # case derive the exclusive next-month boundary and keep it explicit.
            end = add_month(start.replace(day=1))

        return start, end

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

    def _invoice_total(self, invoice: dict[str, Any]) -> Decimal:
        if "total" in invoice:
            total = invoice["total"]
        elif "charges_total" in invoice:
            total = invoice["charges_total"]
        else:
            raise ValueError("missing invoice total")

        total_cost = decimal_cost(total, "invoice total")

        # Team invoice totals are returned as integer cents by the Platform API.
        if self.team_name_or_id:
            total_cost = total_cost / Decimal("100")

        return total_cost

    @staticmethod
    def _invoice_currency(invoice: dict[str, Any]) -> str | None:
        for key in ("currency", "currency_code", "total_currency"):
            currency = invoice.get(key)
            if currency:
                return str(currency)
        return None

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
                invoice_period = self._parse_invoice_period(invoice)
                if not invoice_period:
                    logger.warning("Skipping Heroku invoice without usable period")
                    continue

                period_start, period_end = invoice_period
                if not (start_month <= period_start.replace(day=1) <= end_month):
                    continue

                try:
                    monthly_costs.append(
                        build_monthly_cost_record(
                            provider="heroku",
                            period_start=period_start,
                            period_end=period_end,
                            cost=self._invoice_total(invoice),
                            currency=self._invoice_currency(invoice),
                        )
                    )
                except ValueError as exc:
                    logger.warning("Skipping malformed Heroku invoice row: %s", exc)

            monthly_costs.sort(key=lambda item: item["period_start"])

            return {"data": monthly_costs}
        except Exception as e:
            logger.error("Error fetching Heroku costs: %s", str(e))
            raise Exception(f"Failed to retrieve Heroku costs: {str(e)}")
