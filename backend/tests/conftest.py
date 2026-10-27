from __future__ import annotations

import time

import pytest

from backend.core.config import Settings
from backend.core.database import get_engine, set_engine
from backend.services.market_stream import BookSnapshot, MarkState


class FakeMarket:
    """Proveedor de libro L2 controlado para tests (solo en tests, nunca en vivo)."""

    def __init__(self, symbol: str = "BTCUSDT", mid: float = 50_000.0, sigma: float = 0.0) -> None:
        self.marks = {symbol: MarkState(mark_price=mid)}
        self.sigma = sigma
        self.symbol = symbol
        self.set_mid(mid)

    def set_mid(self, mid: float, spread: float = 1.0, depth: float = 0.5) -> None:
        self.marks[self.symbol].mark_price = mid
        self._book = BookSnapshot(
            bids=[(mid - spread / 2 - i, depth) for i in range(20)],
            asks=[(mid + spread / 2 + i, depth) for i in range(20)], ts=time.time())

    def book(self, symbol: str) -> BookSnapshot:
        self._book.ts = time.time()
        return self._book

    def sigma_per_second(self, symbol: str) -> float:
        return self.sigma


@pytest.fixture()
def cfg() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture()
def db(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    set_engine(engine)
    yield engine
    engine.dispose()
