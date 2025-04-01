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
