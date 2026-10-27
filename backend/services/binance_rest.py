"""Cliente REST público de Binance USDⓈ-M Futures (sin claves)."""
from __future__ import annotations

from typing import Any

import httpx

from backend.core.config import get_settings
from backend.models.schemas import Candle


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=get_settings().rest_base_url, timeout=15.0)


def parse_kline_row(row: list[Any], closed: bool = True) -> Candle:
    return Candle(open_time=int(row[0]), open=float(row[1]), high=float(row[2]),
                  low=float(row[3]), close=float(row[4]), volume=float(row[5]), closed=closed)


async def fetch_klines(symbol: str, interval: str, limit: int = 500,
                       start_ms: int | None = None, end_ms: int | None = None) -> list[Candle]:
    params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    if end_ms is not None:
        params["endTime"] = end_ms
    async with _client() as c:
        r = await c.get("/fapi/v1/klines", params=params)
        r.raise_for_status()
        return [parse_kline_row(row) for row in r.json()]


async def fetch_open_interest_hist(symbol: str, period: str = "5m", limit: int = 30) -> list[dict[str, Any]]:
    async with _client() as c:
        r = await c.get("/futures/data/openInterestHist",
                        params={"symbol": symbol, "period": period, "limit": limit})
        r.raise_for_status()
        return r.json()


async def fetch_long_short_ratio(symbol: str, period: str = "5m") -> float | None:
    async with _client() as c:
        r = await c.get("/futures/data/globalLongShortAccountRatio",
                        params={"symbol": symbol, "period": period, "limit": 1})
        r.raise_for_status()
        data = r.json()
        return float(data[-1]["longShortRatio"]) if data else None


async def fetch_premium_index(symbol: str) -> dict[str, Any]:
    async with _client() as c:
        r = await c.get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        r.raise_for_status()
        return r.json()


async def fetch_depth(symbol: str, limit: int = 20) -> dict[str, Any]:
    async with _client() as c:
        r = await c.get("/fapi/v1/depth", params={"symbol": symbol, "limit": limit})
        r.raise_for_status()
        return r.json()


async def fetch_funding_history(symbol: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor = start_ms
    async with _client() as c:
        while cursor < end_ms:
            r = await c.get("/fapi/v1/fundingRate", params={
                "symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000})
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            out.extend(batch)
            cursor = int(batch[-1]["fundingTime"]) + 1
            if len(batch) < 1000:
                break
    return out
