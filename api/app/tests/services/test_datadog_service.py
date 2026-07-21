from unittest.mock import Mock, patch

import pytest

from app.models import DatadogAPIConfiguration
from app.services.datadog_service import DatadogService


@pytest.fixture
def mock_db():
    return Mock()


def configure_query(mock_db, config):
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        config
    )


def configured_service(mock_db):
    config = Mock(spec=DatadogAPIConfiguration)
    config.app_key = "datadog-app-key-secret"
    config.api_key = "datadog-api-key-secret"
    configure_query(mock_db, config)

    with patch("app.services.datadog_service.SecretsService") as secrets:
        secrets.return_value.get_customer_secret.side_effect = [
            "datadog-app-key",
            "datadog-api-key",
        ]
        return DatadogService(1, mock_db, "Default Configuration")


def test_get_monthly_costs_maps_month_anchor_and_null_currency(mock_db):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "data": [
            {
                "attributes": {
                    "date": "2024-01-01T00:00:00Z",
                    "total_cost": "98.765",
                }
            }
        ]
    }

    service = configured_service(mock_db)
    with patch(
        "app.services.datadog_service.requests.get", return_value=response
    ) as requests_get:
        result = service.get_monthly_costs("01-2024", "01-2024")

    assert result == {
        "data": [
            {
                "month": "01-2024",
                "cost": 98.77,
                "provider": "datadog",
                "period_start": "2024-01-01",
                "period_end": "2024-02-01",
                "currency": None,
            }
        ]
    }
    requests_get.assert_called_once_with(
        "https://api.datadoghq.com/api/v2/usage/historical_cost",
        headers={
            "DD-API-KEY": "datadog-api-key",
            "DD-APPLICATION-KEY": "datadog-app-key",
        },
        params={"start_month": "2024-01", "end_month": "2024-01"},
    )


def test_get_monthly_costs_skips_malformed_rows_with_warning(mock_db, caplog):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "data": [
            {
                "attributes": {
                    "date": "2024-01-01T00:00:00Z",
                }
            }
        ]
    }

    service = configured_service(mock_db)
    caplog.set_level("WARNING")

    with patch("app.services.datadog_service.requests.get", return_value=response):
        result = service.get_monthly_costs("01-2024", "01-2024")

    assert result == {"data": []}
    assert "Skipping malformed Datadog cost row" in caplog.text
