from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from app.models import AWSAPIConfiguration, User, VendorMetrics
from app.tests.conftest import TestingSessionLocal


def shift_month(date_value: datetime, months: int) -> datetime:
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    return date_value.replace(year=year, month=month, day=1)


def test_get_vendor_metrics_invalid_vendor(test_client):
    response = test_client.get("/v1/vendors-metrics/invalid_vendor")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_VENDOR"


def test_get_vendor_metrics_no_config(test_client):
    response = test_client.get("/v1/vendors-metrics/datadog")

    assert response.status_code == 404
    assert response.json()["code"] == "CONFIG_NOT_FOUND"


def test_get_vendor_metrics_returns_lineage_without_cross_scope_leaks(test_client):
    identifier = f"route-scope-{uuid4()}"
    other_identifier = f"{identifier}-other"
    month_start = shift_month(datetime.now().replace(day=1), -1).date()
    month_end = shift_month(datetime.now().replace(day=1), 0).date()
    month = month_start.strftime("%m-%Y")

    db = TestingSessionLocal()
    try:
        current_user = db.query(User).filter(User.sub == "test-user-123").first()
        other_user = User(sub=f"other-user-{uuid4()}")
        db.add(other_user)
        db.flush()
        db.add(
            AWSAPIConfiguration(
                user_id=current_user.id,
                identifier=identifier,
                aws_access_key_id="aws-key",
                aws_secret_access_key="aws-secret",
            )
        )
        db.add(
            VendorMetrics(
                user_id=current_user.id,
                vendor="aws",
                identifier=identifier,
                month=month,
                cost=123.45,
                source_provider="aws",
                source_period_start=month_start,
                source_period_end=month_end,
                provider_currency="USD",
            )
        )
        db.add(
            VendorMetrics(
                user_id=current_user.id,
                vendor="aws",
                identifier=other_identifier,
                month=month,
                cost=888.88,
            )
        )
        db.add(
            VendorMetrics(
                user_id=other_user.id,
                vendor="aws",
                identifier=identifier,
                month=month,
                cost=999.99,
            )
        )
        db.commit()
    finally:
        db.close()

    with patch(
        "app.services.vendor_metrics_service.VendorMetricsService._get_vendor_costs",
        return_value={"data": []},
    ):
        response = test_client.get(f"/v1/vendors-metrics/aws?identifier={identifier}")

    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 1
    assert body["data"] == [
        {
            "month": month,
            "cost": 123.45,
            "source_provider": "aws",
            "source_period_start": month_start.isoformat(),
            "source_period_end": month_end.isoformat(),
            "provider_currency": "USD",
        }
    ]
