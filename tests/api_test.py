import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """verify api is alive or not"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"

def test_get_page_valid():
    response = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=1")
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "2q.1.1.1.1"
    assert data["room"] == "2q"
    assert data["wall"] == 1
    assert data["shelf"] == 1
    assert data["book"] == 1
    assert data["page"] == 1
    assert len(data["content"]) == 3200
    assert isinstance(data["content"], str)

    def test_get_page_different_room():
        r1 = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=1").json()
        r2 = client.get("/page?room=2qw32wr&wall=1&shelf=1&book=1&page=1").json()
        assert r1["content"] != r2["content"]

        

