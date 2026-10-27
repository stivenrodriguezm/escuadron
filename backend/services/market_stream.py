"""Streaming en vivo de Binance Futures: velas, libro L2 y funding (datos reales)."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import ssl
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import truststore
import websockets

from backend.core.config import get_settings
from backend.models.schemas import Candle
from backend.services.binance_rest import fetch_klines

log = logging.getLogger("market_stream")
# Almacén de certificados del sistema operativo (igual que httpx): respeta CAs corporativas.
SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

CandleCallback = Callable[[str, str, list[Candle]], Awaitable[None]]


@dataclass
class BookSnapshot:
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    ts: float

    @property
    def mid(self) -> float:
        return (self.bids[0][0] + self.asks[0][0]) / 2

    @property
    def spread_pct(self) -> float:
        return (self.asks[0][0] - self.bids[0][0]) / self.mid * 100

    def imbalance(self, levels: int = 10) -> float:
        """(Vol_bid − Vol_ask)/(Vol_bid + Vol_ask) en los N mejores niveles: [-1, 1]."""
        b = sum(q for _, q in self.bids[:levels])
        a = sum(q for _, q in self.asks[:levels])
        return 0.0 if a + b == 0 else (b - a) / (b + a)


@dataclass
class MarkState:
    mark_price: float = 0.0
    funding_rate: float = 0.0
    next_funding_time: int = 0
    ts: float = 0.0


@dataclass
class MarketStream:
    symbols: list[str]
    intervals: list[str]
    candles: dict[str, dict[str, deque[Candle]]] = field(default_factory=dict)
    books: dict[str, BookSnapshot] = field(default_factory=dict)
    marks: dict[str, MarkState] = field(default_factory=dict)
    prices_1s: dict[str, deque[float]] = field(default_factory=dict)
    last_message_ts: float = 0.0
    _callbacks: list[CandleCallback] = field(default_factory=list)
    _tasks: list[asyncio.Task] = field(default_factory=list)
    _route_up: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._ensure_buffers()

    def _ensure_buffers(self) -> None:
        for s in self.symbols:
            self.candles.setdefault(s, {})
            for i in self.intervals:
                self.candles[s].setdefault(i, deque(maxlen=600))
            self.marks.setdefault(s, MarkState())
            self.prices_1s.setdefault(s, deque(maxlen=180))

    async def reconfigure(self, symbols: list[str], intervals: list[str]) -> None:
        """Añade pares/intervalos en caliente: descarga su historial y reabre los streams."""
        new = [(s, i) for s in symbols for i in intervals
               if s not in self.symbols or i not in self.intervals]
        self.symbols, self.intervals = list(symbols), list(intervals)
        self._ensure_buffers()
        await self.bootstrap(only=new)
        await self.stop()
        self.start()

    def on_candle_close(self, cb: CandleCallback) -> None:
        self._callbacks.append(cb)

    # ---------- consultas ----------
    def closed_candles(self, symbol: str, interval: str) -> list[Candle]:
        return [c for c in self.candles[symbol][interval] if c.closed]

    def book(self, symbol: str) -> BookSnapshot | None:
        snap = self.books.get(symbol)
        if snap is None or time.time() - snap.ts > 5:
            return None  # libro obsoleto: nunca operar con datos viejos
        return snap

    def last_price(self, symbol: str) -> float:
        snap = self.books.get(symbol)
        if snap:
            return snap.mid
        return self.marks[symbol].mark_price

    def sigma_per_second(self, symbol: str) -> float:
        px = list(self.prices_1s[symbol])
        rets = [math.log(px[i] / px[i - 1]) for i in range(1, len(px)) if px[i - 1] > 0]
        if len(rets) < 10:
            return 0.0
        mean = sum(rets) / len(rets)
        return math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))

    @property
    def connected(self) -> bool:
        return len(self._route_up) == 2 and all(self._route_up.values())

    @property
    def healthy(self) -> bool:
        return self.connected and time.time() - self.last_message_ts < 10

    # ---------- ciclo de vida ----------
    async def bootstrap(self, only: list[tuple[str, str]] | None = None) -> None:
        pairs = only if only is not None else [(s, i) for s in self.symbols for i in self.intervals]
        for s, i in pairs:
            try:
                rows = await fetch_klines(s, i, limit=500)
                self.candles[s][i].extend(rows[:-1])  # la última está en formación
            except Exception as exc:  # noqa: BLE001
                log.warning("Bootstrap %s %s falló: %s", s, i, exc)

    def start(self) -> None:
        if not self._tasks:
            # Binance separa los streams: /public (libro L2) y /market (velas, mark price).
            self._tasks = [asyncio.create_task(self._run(route, streams))
                           for route, streams in self._routes().items()]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks = []
        self._route_up.clear()

    def _routes(self) -> dict[str, list[str]]:
        public, market = [], []
        for s in self.symbols:
            low = s.lower()
            public.append(f"{low}@depth20@100ms")
            market += [f"{low}@kline_{i}" for i in self.intervals] + [f"{low}@markPrice@1s"]
        return {"public": public, "market": market}

    async def _run(self, route: str, streams: list[str]) -> None:
        url = f"{get_settings().ws_base_url}/{route}/stream?streams={'/'.join(streams)}"
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(url, ssl=SSL_CONTEXT, ping_interval=20, max_size=2**22) as ws:
                    self._route_up[route], backoff = True, 1.0
                    log.info("Conectado al stream %s de Binance Futures", route)
                    async for raw in ws:
                        self.last_message_ts = time.time()
                        await self._dispatch(json.loads(raw))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("Stream %s desconectado (%s). Reintentando en %.0fs", route, exc, backoff)
            self._route_up[route] = False
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    async def _dispatch(self, msg: dict) -> None:
        data = msg.get("data", msg)
        event = data.get("e")
        symbol = data.get("s")
        if symbol not in self.marks:
            return
        if event == "depthUpdate":
            self.books[symbol] = BookSnapshot(
                bids=[(float(p), float(q)) for p, q in data["b"] if float(q) > 0],
                asks=[(float(p), float(q)) for p, q in data["a"] if float(q) > 0],
                ts=time.time())
        elif event == "markPriceUpdate":
            m = self.marks[symbol]
            m.mark_price, m.funding_rate = float(data["p"]), float(data["r"])
            m.next_funding_time, m.ts = int(data["T"]), time.time()
            self.prices_1s[symbol].append(m.mark_price)
        elif event == "kline":
            await self._on_kline(symbol, data["k"])

    async def _on_kline(self, symbol: str, k: dict) -> None:
        interval = k["i"]
        if interval not in self.candles[symbol]:
            return
        candle = Candle(open_time=int(k["t"]), open=float(k["o"]), high=float(k["h"]),
                        low=float(k["l"]), close=float(k["c"]), volume=float(k["v"]),
                        closed=bool(k["x"]))
        buf = self.candles[symbol][interval]
        if buf and buf[-1].open_time == candle.open_time:
            buf[-1] = candle
        elif not buf or candle.open_time > buf[-1].open_time:
            buf.append(candle)
        if candle.closed:
            closed = self.closed_candles(symbol, interval)
            for cb in self._callbacks:
                asyncio.create_task(cb(symbol, interval, closed))
