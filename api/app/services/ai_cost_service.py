"""Organization API billing; aggregate daily costs without estimating token prices."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal

import requests
from pydantic import BaseModel, StrictBool
from sqlalchemy.orm import Session

from app.helpers.secrets_service import SecretsService
from app.models import AI_CONFIG_MODELS
from app.services.monthly_costs import (
    add_month,
    build_monthly_cost_record,
    decimal_cost,
)

APIProvider = Literal["openai", "anthropic"]


class CostPage(BaseModel):
    data: list[dict]
    has_more: StrictBool
    next_page: str | None = None


class AICostService:
    def __init__(
        self, user_id: int, db: Session, identifier: str, provider: APIProvider
    ):
        self.provider = provider
        model = AI_CONFIG_MODELS[provider]
        config = (
            db.query(model)
            .filter(model.user_id == user_id, model.identifier == identifier)
            .first()
        )
        if not config:
            raise ValueError("AI billing configuration not found")
        key = SecretsService().get_customer_secret(config.api_key)
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Organization admin API key not found")
        self.api_key = key

    def get_monthly_costs(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict:
        now = datetime.now(timezone.utc)
        end = (
            datetime.strptime(end_date, "%m-%Y").date()
            if end_date
            else now.date().replace(day=1)
        )
        start = (
            datetime.strptime(start_date, "%m-%Y").date()
            if start_date
            else end.replace(year=end.year - 1)
        )
        if start > end:
            raise ValueError("Start month must not follow end month")
        stop = min(
            datetime.combine(add_month(end), datetime.min.time(), timezone.utc),
            now.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        if datetime.combine(start, datetime.min.time(), timezone.utc) >= stop:
            return {"data": []}
        params: dict[str, str | int] = {"bucket_width": "1d", "limit": 31}
        headers = {"User-Agent": "InfraSpend/1.0"}
        if self.provider == "openai":
            url = "https://api.openai.com/v1/organization/costs"
            headers["Authorization"] = f"Bearer {self.api_key}"
            params.update(
                start_time=int(
                    datetime.combine(
                        start, datetime.min.time(), timezone.utc
                    ).timestamp()
                ),
                end_time=int(stop.timestamp()),
            )
        else:
            url = "https://api.anthropic.com/v1/organizations/cost_report"
            headers.update(
                {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
            )
            params.update(
                starting_at=f"{start.isoformat()}T00:00:00Z",
                ending_at=stop.isoformat().replace("+00:00", "Z"),
            )
        totals: dict[date, Decimal] = {}
        periods: dict[date, tuple[date, date]] = {}
        seen_pages: set[str] = set()
        seen_buckets: set[date] = set()
        while True:
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=dict(params),
                    timeout=30,
                    allow_redirects=False,
                )
            except requests.RequestException:
                raise RuntimeError(f"{self.provider} billing request failed") from None
            if response.status_code != 200:
                # Never expose provider response bodies or credentials in errors.
                raise RuntimeError(
                    f"{self.provider} billing request failed (HTTP {response.status_code}); "
                    "check admin key permissions"
                )
            try:
                page = CostPage.parse_obj(response.json())
                for bucket in page.data:
                    if self.provider == "openai":
                        bucket_start = datetime.fromtimestamp(
                            bucket["start_time"], timezone.utc
                        ).date()
                        bucket_end = datetime.fromtimestamp(
                            bucket["end_time"], timezone.utc
                        ).date()
                    else:
                        bucket_start = datetime.fromisoformat(
                            bucket["starting_at"].replace("Z", "+00:00")
                        ).date()
                        bucket_end = datetime.fromisoformat(
                            bucket["ending_at"].replace("Z", "+00:00")
                        ).date()
                    if (
                        bucket_start in seen_buckets
                        or bucket_end <= bucket_start
                        or bucket_start < start
                        or bucket_start >= add_month(end)
                        or bucket_start >= stop.date()
                    ):
                        raise ValueError("Invalid or repeated cost bucket")
                    if bucket_end - bucket_start != timedelta(days=1):
                        raise ValueError("Expected a daily cost bucket")
                    seen_buckets.add(bucket_start)
                    month = bucket_start.replace(day=1)
                    results = bucket["results"]
                    if not isinstance(results, list):
                        raise ValueError("Invalid cost results")
                    amount = Decimal(0)
                    for result in results:
                        value = result["amount"]
                        currency = (
                            value["currency"]
                            if self.provider == "openai"
                            else result["currency"]
                        )
                        if not isinstance(currency, str) or currency.upper() != "USD":
                            raise ValueError("Unsupported billing currency")
                        amount += decimal_cost(
                            value["value"] if self.provider == "openai" else value
                        ) / (100 if self.provider == "anthropic" else 1)
                    totals[month] = totals.get(month, Decimal(0)) + amount
                    previous = periods.get(month, (bucket_start, bucket_end))
                    periods[month] = (
                        min(previous[0], bucket_start),
                        max(previous[1], bucket_end),
                    )
                if not page.has_more:
                    break
                if not page.next_page or page.next_page in seen_pages:
                    raise ValueError("Invalid cost pagination")
                seen_pages.add(page.next_page)
                params["page"] = page.next_page
            except (ValueError, KeyError, TypeError, OverflowError, AttributeError):
                raise RuntimeError(
                    f"{self.provider} returned an invalid billing report"
                ) from None
        return {
            "data": [
                build_monthly_cost_record(
                    provider=self.provider,
                    period_start=periods[month][0],
                    period_end=periods[month][1],
                    cost=totals[month],
                    currency="USD",
                )
                for month in sorted(totals)
            ]
        }
