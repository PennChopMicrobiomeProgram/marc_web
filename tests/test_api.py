import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MARC_DB_URL", "sqlite:///:memory:")
    from app.app import app

    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200


def test_isolates_page(client):
    response = client.get("/isolates")
    assert response.status_code == 200
    assert b"Sample ID" in response.data

    api_resp = client.get("/api/isolates?draw=1&start=0&length=5")
    assert api_resp.status_code == 200
    data = api_resp.get_json()
    assert "data" in data


def test_aliquots_page(client):
    response = client.get("/aliquots")
    assert response.status_code == 200

    api_resp = client.get("/api/aliquots?draw=1&start=0&length=5")
    assert api_resp.status_code == 200
    data = api_resp.get_json()
    assert "data" in data


def test_query_page(client):
    resp = client.get("/query")
    assert resp.status_code == 200
    # Dropdown should exist
    assert b"model-select" in resp.data
    # Known model names should appear in options
    assert b"isolates" in resp.data
    assert b"aliquots" in resp.data
