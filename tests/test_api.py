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


@pytest.mark.parametrize(
    "page,api_endpoint",
    [
        ("/assemblies", "/api/assemblies"),
        ("/assembly_qc", "/api/assembly_qc"),
        ("/taxonomic_assignments", "/api/taxonomic_assignments"),
        ("/antimicrobials", "/api/antimicrobials"),
    ],
)
def test_assembly_tables(client, page, api_endpoint):
    resp = client.get(page)
    assert resp.status_code == 200

    api_resp = client.get(f"{api_endpoint}?draw=1&start=0&length=5")
    assert api_resp.status_code == 200
    data = api_resp.get_json()
    assert "data" in data


def test_query_api(client):
    resp = client.post(
        "/api/query",
        data={"query": "SELECT 1 as one", "draw": 1, "start": 0, "length": 5},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["recordsTotal"] == 1
    assert data["data"][0]["one"] == 1
