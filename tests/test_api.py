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
    r2 = client.get("/page?room=2q32r&wall=1&shelf=1&book=1&page=1").json()
    assert r1["content"] != r2["content"]

def test_get_different_page():
    r1 = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=1").json()
    r2 = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=2").json()
    assert r1["content"] != r2["content"]

def test_get_page_deterministic():
    r1 = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=1").json()
    r2 = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=1").json()
    assert r1["content"] == r2["content"]

def test_invalid_wall():
    response = client.get("/page?room=2q&wall=5&shelf=1&book=1&page=1")
    assert response.status_code == 422

def test_invalid_shelf():
    response = client.get("/page?room=2q&wall=1&shelf=6&book=1&page=1")
    assert response.status_code == 422

def test_invalid_book():
    response = client.get("/page?room=2q&wall=1&shelf=1&book=33&page=1")
    assert response.status_code == 422

def test_invalid_page():
    response = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=411")
    assert response.status_code == 422

def test_missing_params():

    response = client.get("/page?room=2q&wall=1&shelf=1")
    assert response.status_code == 422


def test_invalid_room_chars():
    response = client.get("/page?room=2qxwyz&wall=1&shelf=1&book=1&page=4")
    assert response.status_code == 400
    assert "invalid address" in response.json()["detail"]


def test_response_schema():
    response = client.get("/page?room=2q&wall=1&shelf=1&book=1&page=41")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"address", "room", "wall", "shelf", "book", "page", "content"}
    assert all(isinstance(data[k], (str, int)) for k in data)






