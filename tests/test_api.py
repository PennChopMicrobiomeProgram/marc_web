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

    # second page should also load
    response = client.get("/isolates?page=2")
    assert response.status_code == 200


def test_aliquots_page(client):
    response = client.get("/aliquots")
    assert response.status_code == 200

    response = client.get("/aliquots?page=2")
    assert response.status_code == 200
