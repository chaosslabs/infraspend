from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Literal, Mapping, TypedDict, cast


ProviderName = Literal["aws", "datadog", "heroku"]
ALLOWED_PROVIDERS: set[str] = {"aws", "datadog", "heroku"}


class MonthlyCostRecord(TypedDict):
    month: str
    cost: float
    provider: ProviderName
    period_start: str
    period_end: str
    currency: str | None


def add_month(date_value: date) -> date:
    month_index = date_value.month
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def parse_iso_date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO date") from exc
    raise ValueError(f"{field_name} must be an ISO date")


def decimal_cost(value: Any, field_name: str = "cost") -> Decimal:
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc

    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite")

    return amount


def build_monthly_cost_record(
    *,
    provider: ProviderName,
    period_start: date,
    period_end: date,
    cost: Any,
    currency: Any = None,
) -> MonthlyCostRecord:
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")

    if period_end <= period_start:
        raise ValueError("period_end must be after period_start")

    normalized_cost = decimal_cost(cost).quantize(Decimal("0.01"), ROUND_HALF_UP)
    currency_value = str(currency).strip() if currency not in (None, "") else None

    return {
        "month": period_start.strftime("%m-%Y"),
        "cost": float(normalized_cost),
        "provider": provider,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "currency": currency_value,
    }


def validate_monthly_cost_record(
    record: Mapping[str, Any], expected_provider: str | None = None
) -> MonthlyCostRecord:
    provider = str(record.get("provider", "")).lower()
    if expected_provider and provider != expected_provider.lower():
        raise ValueError(
            f"Monthly cost provider {provider or '<missing>'} does not match "
            f"expected provider {expected_provider.lower()}"
        )
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError("Monthly cost provider is required")

    period_start = parse_iso_date(record.get("period_start"), "period_start")
    period_end = parse_iso_date(record.get("period_end"), "period_end")
    expected_month = period_start.strftime("%m-%Y")
    if record.get("month") != expected_month:
        raise ValueError("Monthly cost month must match period_start")

    return build_monthly_cost_record(
        provider=cast(ProviderName, provider),
        period_start=period_start,
        period_end=period_end,
        cost=record.get("cost"),
        currency=record.get("currency"),
    )
