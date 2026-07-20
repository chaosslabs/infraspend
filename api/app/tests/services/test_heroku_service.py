from unittest.mock import Mock, patch

import pytest

from app.models import HerokuAPIConfiguration
from app.services.heroku_service import HerokuService


@pytest.fixture
def mock_db():
    return Mock()


def configure_query(mock_db, config):
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        config
    )


def test_get_monthly_costs_uses_account_invoices(mock_db):
    config = Mock(spec=HerokuAPIConfiguration)
    config.api_key = "heroku-secret-id"
    config.team_name_or_id = None
    configure_query(mock_db, config)

    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {"period_start": "12/01/2023", "total": 99.99},
        {"period_start": "01/01/2024", "total": 120.50},
        {"period_start": "02/01/2024", "charges_total": 130.25},
        {"period_start": "04/01/2024", "total": 150.00},
    ]

    with patch("app.services.heroku_service.SecretsService") as secrets, patch(
        "app.services.heroku_service.requests.get", return_value=response
    ) as requests_get:
        secrets.return_value.get_customer_secret.return_value = "heroku-token"

        service = HerokuService(1, mock_db, "Default Configuration")
        result = service.get_monthly_costs("01-2024", "03-2024")

    assert result == {
        "data": [
            {"month": "01-2024", "cost": 120.5},
            {"month": "02-2024", "cost": 130.25},
        ]
    }
    requests_get.assert_called_once_with(
        "https://api.heroku.com/account/invoices",
        headers={
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": "Bearer heroku-token",
        },
        timeout=30,
    )


def test_get_monthly_costs_uses_team_invoices_and_normalizes_cents(mock_db):
    config = Mock(spec=HerokuAPIConfiguration)
    config.api_key = "heroku-secret-id"
    config.team_name_or_id = "platform team"
    configure_query(mock_db, config)

    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {"period_start": "01/01/2024", "total": 100000},
        {"period_start": "02/01/2024", "charges_total": 75050},
    ]

    with patch("app.services.heroku_service.SecretsService") as secrets, patch(
        "app.services.heroku_service.requests.get", return_value=response
    ) as requests_get:
        secrets.return_value.get_customer_secret.return_value = "heroku-token"

        service = HerokuService(1, mock_db, "Team Configuration")
        result = service.get_monthly_costs("01-2024", "02-2024")

    assert result == {
        "data": [
            {"month": "01-2024", "cost": 1000.0},
            {"month": "02-2024", "cost": 750.5},
        ]
    }
    requests_get.assert_called_once_with(
        "https://api.heroku.com/teams/platform%20team/invoices",
        headers={
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": "Bearer heroku-token",
        },
        timeout=30,
    )


def test_missing_heroku_configuration_raises_error(mock_db):
    configure_query(mock_db, None)

    with pytest.raises(Exception, match="No Heroku configuration found"):
        HerokuService(1, mock_db, "Missing Configuration")
