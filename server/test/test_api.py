import uuid
import pytest
from server import app


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def user(client):
    login = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{login}@example.com"
    password = "Passw0rd!test"
    resp = client.post("/api/create-user", json={
        "login": login, "password": password, "email": email,
    })
    assert resp.status_code in (200, 201)
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"email": email, "password": password, "token": resp.get_json()["token"]}


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert isinstance(resp.get_json()["message"], str)


def test_create_user(client):
    login = f"user_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/create-user", json={
        "login": login,
        "password": "Passw0rd!test",
        "email": f"{login}@example.com",
    })
    assert resp.status_code in (200, 201)
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert body["login"] == login


def test_login(client, user):
    resp = client.post("/api/login", json={
        "email": user["email"], "password": user["password"],
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["expires_in"], int)
    assert isinstance(body["token"], str)


def test_get_watermarking_methods(client):
    resp = client.get("/api/get-watermarking-methods")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == len(body["methods"])
    assert all({"name", "description"} <= m.keys() for m in body["methods"])


def test_list_documents(client, user):
    resp = client.get(
        "/api/list-documents",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.get_json()["documents"], list)