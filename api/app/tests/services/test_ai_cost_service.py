from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from app.services.ai_cost_service import AICostService


def bucket(provider, day="2026-01-01", amount="12.345", currency="USD"):
    start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    end = start.timestamp() + 86400
    if provider == "openai":
        return {
            "start_time": int(start.timestamp()),
            "end_time": int(end),
            "results": [{"amount": {"value": amount, "currency": currency}}],
        }
    return {
        "starting_at": start.isoformat(),
        "ending_at": datetime.fromtimestamp(end, timezone.utc).isoformat(),
        "results": [{"amount": amount, "currency": currency}],
    }


def response(data, has_more=False, next_page=None):
    return Mock(
        status_code=200,
        json=Mock(
            return_value={"data": data, "has_more": has_more, "next_page": next_page}
        ),
    )


@pytest.fixture
def service():
    def make(provider):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = Mock(
            api_key="secret-ref"
        )
        with patch("app.services.ai_cost_service.SecretsService") as secrets:
            secrets.return_value.get_customer_secret.return_value = "test-admin-key"
            return AICostService(1, db, "Account", provider)

    return make


@pytest.mark.parametrize("provider,expected", [("openai", 24.69), ("anthropic", 0.25)])
def test_pagination_decimal_aggregation_and_headers(service, provider, expected):
    with patch(
        "app.services.ai_cost_service.requests.get",
        side_effect=[
            response([bucket(provider)], True, "second"),
            response([bucket(provider, "2026-01-02")]),
        ],
    ) as get:
        result = service(provider).get_monthly_costs("01-2026", "01-2026")
    assert result["data"] == [
        {
            "month": "01-2026",
            "cost": expected,
            "provider": provider,
            "period_start": "2026-01-01",
            "period_end": "2026-01-03",
            "currency": "USD",
        }
    ]
    first, second = get.call_args_list
    assert "page" not in first.kwargs["params"]
    assert second.kwargs["params"]["page"] == "second"
    assert first.kwargs["timeout"] == 30
    assert first.kwargs["allow_redirects"] is False
    if provider == "openai":
        assert first.args[0] == "https://api.openai.com/v1/organization/costs"
        assert first.kwargs["headers"]["Authorization"] == "Bearer test-admin-key"
        assert first.kwargs["params"]["end_time"] == 1769904000
    else:
        assert first.args[0] == "https://api.anthropic.com/v1/organizations/cost_report"
        assert first.kwargs["headers"]["anthropic-version"] == "2023-06-01"
        assert first.kwargs["headers"]["x-api-key"] == "test-admin-key"
        assert first.kwargs["params"]["ending_at"] == "2026-02-01T00:00:00Z"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_empty_report_does_not_invent_zero_months(service, provider):
    with patch("app.services.ai_cost_service.requests.get", return_value=response([])):
        assert service(provider).get_monthly_costs("01-2026", "01-2026") == {"data": []}


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_explicit_empty_bucket_is_zero(service, provider):
    row = bucket(provider)
    row["results"] = []
    with patch(
        "app.services.ai_cost_service.requests.get", return_value=response([row])
    ):
        assert (
            service(provider).get_monthly_costs("01-2026", "01-2026")["data"][0]["cost"]
            == 0
        )


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize(
    "bad_amount,currency", [("NaN", "USD"), (None, "USD"), ("3", "EUR")]
)
def test_malformed_amounts_fail_entire_report(service, provider, bad_amount, currency):
    with patch(
        "app.services.ai_cost_service.requests.get",
        return_value=response([bucket(provider, amount=bad_amount, currency=currency)]),
    ):
        with pytest.raises(RuntimeError, match="invalid billing report"):
            service(provider).get_monthly_costs("01-2026", "01-2026")


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_later_page_failure_does_not_return_partial_total(service, provider):
    with patch(
        "app.services.ai_cost_service.requests.get",
        side_effect=[response([bucket(provider)], True, "next"), Mock(status_code=429)],
    ):
        with pytest.raises(RuntimeError, match="HTTP 429"):
            service(provider).get_monthly_costs("01-2026", "01-2026")


def test_missing_cursor_and_duplicate_bucket_rejected(service):
    for pages in (
        [response([], True)],
        [response([bucket("openai"), bucket("openai")])],
        [response([], True, "next"), response([], True, "next")],
    ):
        with patch("app.services.ai_cost_service.requests.get", side_effect=pages):
            with pytest.raises(RuntimeError, match="invalid billing report"):
                service("openai").get_monthly_costs("01-2026", "01-2026")


def test_network_error_does_not_expose_key(service):
    with patch(
        "app.services.ai_cost_service.requests.get",
        side_effect=requests.RequestException("test-admin-key"),
    ):
        with pytest.raises(RuntimeError) as error:
            service("openai").get_monthly_costs("01-2026", "01-2026")
    assert "test-admin-key" not in str(error.value)


def test_missing_config_and_missing_key():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ValueError, match="configuration not found"):
        AICostService(1, db, "Missing", "openai")
    db.query.return_value.filter.return_value.first.return_value = Mock(api_key="ref")
    with patch("app.services.ai_cost_service.SecretsService") as secrets:
        secrets.return_value.get_customer_secret.return_value = None
        with pytest.raises(ValueError, match="key not found"):
            AICostService(1, db, "Missing key", "anthropic")


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_current_month_requests_only_completed_utc_days(service, provider):
    with patch("app.services.ai_cost_service.datetime", wraps=datetime) as clock, patch(
        "app.services.ai_cost_service.requests.get", return_value=response([])
    ) as get:
        clock.now.return_value = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
        service(provider).get_monthly_costs("01-2026", "01-2026")
    params = get.call_args.kwargs["params"]
    if provider == "openai":
        assert params["end_time"] == int(
            datetime(2026, 1, 15, tzinfo=timezone.utc).timestamp()
        )
    else:
        assert params["ending_at"] == "2026-01-15T00:00:00Z"
