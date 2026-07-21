from unittest.mock import Mock, patch

import pytest

from app.models import AWSAPIConfiguration
from app.services.aws_service import AWSService


@pytest.fixture
def mock_db():
    return Mock()


def configure_query(mock_db, config):
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        config
    )


def configured_service(mock_db, client):
    config = Mock(spec=AWSAPIConfiguration)
    config.aws_access_key_id = "aws-access-key-secret"
    config.aws_secret_access_key = "aws-secret-key-secret"
    configure_query(mock_db, config)

    with patch("app.services.aws_service.SecretsService") as secrets, patch(
        "app.services.aws_service.boto3.client", return_value=client
    ):
        secrets.return_value.get_customer_secret.side_effect = [
            "aws-access-key",
            "aws-secret-key",
        ]
        return AWSService(1, mock_db, "Default Configuration")


def test_get_monthly_costs_maps_cost_explorer_lineage(mock_db):
    client = Mock()
    client.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                "Total": {
                    "UnblendedCost": {
                        "Amount": "12.345",
                        "Unit": "USD",
                    }
                },
            }
        ]
    }

    service = configured_service(mock_db, client)
    result = service.get_monthly_costs("01-2024", "02-2024")

    assert result == {
        "data": [
            {
                "month": "01-2024",
                "cost": 12.35,
                "provider": "aws",
                "period_start": "2024-01-01",
                "period_end": "2024-02-01",
                "currency": "USD",
            }
        ]
    }


def test_get_monthly_costs_fails_on_malformed_cost_explorer_row(mock_db):
    client = Mock()
    client.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-02-01"},
                "Total": {"UnblendedCost": {"Unit": "USD"}},
            }
        ]
    }

    service = configured_service(mock_db, client)

    with pytest.raises(Exception, match="Malformed AWS Cost Explorer monthly cost row"):
        service.get_monthly_costs("01-2024", "02-2024")
