"""Descarga velas y funding históricos reales de Binance con caché .parquet local."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import polars as pl

from backend.core.config import DATA_DIR
from backend.services.binance_rest import fetch_funding_history, fetch_klines

HISTORY_DIR = DATA_DIR / "history"
INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
               "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
KLINE_SCHEMA = {"open_time": pl.Int64, "open": pl.Float64, "high": pl.Float64,
                "low": pl.Float64, "close": pl.Float64, "volume": pl.Float64}


def to_ms(date: str) -> int:
    return int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _path(symbol: str, kind: str) -> str:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return str(HISTORY_DIR / f"{symbol}_{kind}.parquet")


async def _download_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> pl.DataFrame:
    step = INTERVAL_MS[interval]
    rows: list[dict] = []
    cursor = start_ms
    while cursor < end_ms:
        batch = await fetch_klines(symbol, interval, limit=1500, start_ms=cursor, end_ms=end_ms)
        if not batch:
            break
        rows += [c.model_dump(exclude={"closed"}) for c in batch]
        cursor = batch[-1].open_time + step
        await asyncio.sleep(0.15)  # respeta los límites de peso de la API pública
    return pl.DataFrame(rows, schema=KLINE_SCHEMA) if rows else pl.DataFrame(schema=KLINE_SCHEMA)


async def load_klines(symbol: str, interval: str, start: str, end: str) -> pl.DataFrame:
    """Devuelve velas cerradas en [start, end); descarga solo los tramos faltantes."""
    start_ms, end_ms = to_ms(start), min(to_ms(end), int(datetime.now(timezone.utc).timestamp() * 1000))
    step = INTERVAL_MS[interval]
    path = _path(symbol, interval)
    try:
        cached = pl.read_parquet(path)
    except (FileNotFoundError, OSError):
        cached = pl.DataFrame(schema=KLINE_SCHEMA)
    frames = [cached]
    if cached.is_empty():
        frames.append(await _download_klines(symbol, interval, start_ms, end_ms))
    else:
        lo, hi = cached["open_time"].min(), cached["open_time"].max()
        if start_ms < lo:
            frames.append(await _download_klines(symbol, interval, start_ms, lo))
        if end_ms > hi + step:
            frames.append(await _download_klines(symbol, interval, hi + step, end_ms))
    merged = pl.concat(frames).unique("open_time").sort("open_time")
    merged.write_parquet(path)
    # descarta la vela aún en formación
    return merged.filter((pl.col("open_time") >= start_ms) & (pl.col("open_time") + step <= end_ms))


async def load_funding(symbol: str, start: str, end: str) -> list[tuple[int, float]]:
    start_ms, end_ms = to_ms(start), to_ms(end)
    path = _path(symbol, "funding")
    try:
        cached = pl.read_parquet(path)
    except (FileNotFoundError, OSError):
        cached = pl.DataFrame(schema={"time": pl.Int64, "rate": pl.Float64})
    covered = (not cached.is_empty() and cached["time"].min() <= start_ms + 8 * 3_600_000
               and cached["time"].max() >= min(end_ms, int(datetime.now(timezone.utc).timestamp() * 1000)) - 8 * 3_600_000)
    if not covered:
        raw = await fetch_funding_history(symbol, start_ms, end_ms)
        fresh = pl.DataFrame({"time": [int(r["fundingTime"]) for r in raw],
                              "rate": [float(r["fundingRate"]) for r in raw]},
                             schema={"time": pl.Int64, "rate": pl.Float64})
        cached = pl.concat([cached, fresh]).unique("time").sort("time")
        cached.write_parquet(path)
    sel = cached.filter((pl.col("time") >= start_ms) & (pl.col("time") < end_ms))
    return list(zip(sel["time"].to_list(), sel["rate"].to_list()))
