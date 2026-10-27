"""La API pública exige token; sin API_TOKEN (uso local) no se exige nada."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.api import main
from backend.api.auth import WS_UNAUTHORIZED
from backend.core.config import get_settings


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secreto-de-prueba")
    get_settings.cache_clear()
    yield TestClient(main.app)  # sin lifespan: el motor no arranca, basta para probar la auth
    get_settings.cache_clear()


def test_rest_requires_valid_token(client):
    assert client.get("/api/portfolio").status_code == 401
    assert client.get("/api/portfolio", headers={"Authorization": "Bearer otro"}).status_code == 401
    ok = client.get("/api/portfolio", headers={"Authorization": "Bearer secreto-de-prueba"})
    assert ok.status_code == 503  # pasó la auth; el motor no está iniciado en el test


def test_health_is_public(client):
    assert client.get("/api/health").status_code == 200


def test_websocket_rejects_missing_token(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == WS_UNAUTHORIZED


def test_no_token_configured_means_no_auth(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "")
    get_settings.cache_clear()
    try:
        assert TestClient(main.app).get("/api/portfolio").status_code == 503
    finally:
        get_settings.cache_clear()
