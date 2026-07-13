"""Public pages, API docs, and response-header policies."""


def test_system_status(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_home_renders_login_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-react-page="login"' in response.text
    assert "msi-react-bootstrap" in response.text


def test_admin_page_redirects_when_logged_out(client):
    response = client.get("/admin")
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_openapi_schema_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert len(response.json()["paths"]) > 50


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["x-request-id"]


def test_api_responses_are_not_cached(client):
    response = client.get("/api/v1/system/status")
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_page_responses_are_not_cached(client):
    response = client.get("/")
    assert response.headers["cache-control"] == "no-store, max-age=0"
