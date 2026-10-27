"""Autenticación por token para la API y el WebSocket.

Sin API_TOKEN (uso local en 127.0.0.1) no se exige nada. En un servidor público
el token es obligatorio (REQUIRE_API_TOKEN=1) y viaja como `Authorization: Bearer`
en REST y como `?token=` en el WebSocket (los navegadores no permiten cabeceras ahí).
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, WebSocket

from backend.core.config import get_settings

WS_UNAUTHORIZED = 4401  # código de cierre que el frontend interpreta como "pide el token"


def token_valid(token: str | None) -> bool:
    expected = get_settings().api_token
    if not expected:
        return True
    return token is not None and hmac.compare_digest(token.encode(), expected.encode())


async def require_token(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not token_valid(token):
        raise HTTPException(401, "Token de acceso inválido o ausente", headers={"WWW-Authenticate": "Bearer"})


def websocket_authorized(ws: WebSocket) -> bool:
    return token_valid(ws.query_params.get("token"))
