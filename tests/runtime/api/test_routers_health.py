"""Tests for health HTTP routes."""


def test_health_returns_ok(api_client):
    """The health endpoint should report that the application is healthy."""

    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
