def test_healthcheck_returns_ok(test_client):
    """GET /healthcheck should return 200 with a body of 'OK'."""
    response = test_client.get("/healthcheck")
    assert response.status_code == 200
    assert response.text == "OK"


def test_root_redirects_to_docs(test_client):
    """GET / should redirect to /docs."""
    response = test_client.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 307, 308)
    assert response.headers["location"] == "/docs"
