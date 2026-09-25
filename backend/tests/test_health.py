def test_health_returns_ok(anon_client):
    response = anon_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
