from app.services.vendor_metrics_service import VendorMetricsService


async def raise_invalid_vendor(*args, **kwargs):
    raise ValueError("Unsupported vendor: invalid_vendor")


async def raise_vendor_error(*args, **kwargs):
    raise Exception("No Datadog configuration found")


def test_get_vendor_metrics_invalid_vendor(test_client, monkeypatch):
    monkeypatch.setattr(
        VendorMetricsService, "get_and_store_vendor_metrics", raise_invalid_vendor
    )

    response = test_client.get("/v1/vendors-metrics/invalid_vendor")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_VENDOR"


def test_get_vendor_metrics_no_config(test_client, monkeypatch):
    monkeypatch.setattr(
        VendorMetricsService, "get_and_store_vendor_metrics", raise_vendor_error
    )

    response = test_client.get("/v1/vendors-metrics/datadog")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "VENDOR_ERROR"
