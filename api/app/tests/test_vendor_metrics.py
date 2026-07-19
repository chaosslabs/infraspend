def test_get_vendor_metrics_invalid_vendor(test_client):
    response = test_client.get("/v1/vendors-metrics/invalid_vendor")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_VENDOR"


def test_get_vendor_metrics_no_config(test_client):
    response = test_client.get("/v1/vendors-metrics/datadog")

    assert response.status_code == 404
    assert response.json()["code"] == "CONFIG_NOT_FOUND"
