"""Smoke tests: health, user CRUD, wardrobe upload, recommend guard. No external network."""
import io

import pytest
from fastapi.testclient import TestClient

import app.routers.wardrobe as wardrobe_router
from app.config import settings
from app.main import app
from app.services import storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(storage, "UPLOAD_ROOT", tmp_path / "uploads")
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_user_crud(client):
    r = client.post(
        "/api/user",
        json={"name": "张三", "gender": "男", "height_cm": 175, "weight_kg": 70, "age": 25},
    )
    assert r.status_code == 200
    first = r.json()
    assert first["is_active"] is True

    r = client.post(
        "/api/user",
        json={"name": "李四", "gender": "女", "height_cm": 160, "weight_kg": 50},
    )
    assert r.status_code == 200
    second = r.json()
    assert second["is_active"] is False

    r = client.get("/api/user")
    assert len(r.json()) == 2

    r = client.post(f"/api/user/{second['id']}/activate")
    assert r.status_code == 200
    assert r.json()["active_id"] == second["id"]

    r = client.delete(f"/api/user/{second['id']}")
    assert r.status_code == 200

    users = client.get("/api/user").json()
    assert len(users) == 1
    assert users[0]["id"] == first["id"]
    assert users[0]["is_active"] is True


def test_wardrobe_upload_and_dedupe(client, monkeypatch):
    monkeypatch.setattr(
        wardrobe_router,
        "recognize_clothing",
        lambda b: {
            "name": "白色T恤",
            "type": "上衣",
            "category": "短袖",
            "color": "白色",
            "material": "纯棉",
            "season": ["夏"],
            "formality": 2,
            "style": ["休闲"],
            "features": ["圆领"],
        },
    )
    payload = b"\xff\xd8\xff\xe0" + b"\x00" * 128

    r = client.post(
        "/api/wardrobe/upload",
        files={"file": ("t.jpg", io.BytesIO(payload), "image/jpeg")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["recognized"]["name"] == "白色T恤"

    r2 = client.post(
        "/api/wardrobe/upload",
        files={"file": ("t.jpg", io.BytesIO(payload), "image/jpeg")},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == data["id"]


def test_upload_rejects_oversize(client):
    big = b"\xff\xd8\xff\xe0" + b"\x00" * (10 * 1024 * 1024 + 1)
    r = client.post(
        "/api/wardrobe/upload",
        files={"file": ("big.jpg", io.BytesIO(big), "image/jpeg")},
    )
    assert r.status_code == 400


def test_recommend_empty_wardrobe(client):
    r = client.post(
        "/api/recommend",
        json={"lat": 31.23, "lon": 121.47, "occasion": "日常"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "EMPTY_WARDROBE"
