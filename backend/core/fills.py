"""Simulación de llenados contra el Order Book L2 real de Binance."""
from __future__ import annotations

from typing import Protocol

from backend.core import accounting as acc
from backend.core.config import Settings
from backend.models.schemas import Fill, Side
from backend.services.market_stream import BookSnapshot, MarkState


class MarketDataProvider(Protocol):
    marks: dict[str, MarkState]

    def book(self, symbol: str) -> BookSnapshot | None: ...
    def sigma_per_second(self, symbol: str) -> float: ...


class StaleBookError(RuntimeError):
    pass


def simulate_market_fill(md: MarketDataProvider, cfg: Settings, symbol: str, side: Side,
                         quantity: float, is_entry: bool) -> Fill:
    """Foto instantánea del libro: VWAP por niveles + latencia + comisión taker."""
    book = md.book(symbol)
    if book is None or not book.bids or not book.asks:
        raise StaleBookError(f"Libro de órdenes de {symbol} no disponible o desactualizado")
    buying = (side == "LONG") == is_entry
    levels = book.asks if buying else book.bids
    weighted = acc.weighted_fill_price(levels, quantity)
    s_lat = acc.latency_slippage(md.sigma_per_second(symbol), cfg.latency_ms, cfg.min_latency_slippage)
    eff = acc.effective_price(weighted, side, is_entry, s_lat)
    return Fill(symbol=symbol, side=side, quantity=quantity, weighted_price=weighted,
                effective_price=eff, mid_price=book.mid, fee=acc.fee(quantity, eff, cfg.taker_fee),
                fee_rate=cfg.taker_fee, slippage_cost=acc.slippage_cost(quantity, eff, book.mid),
                s_latency=s_lat)


def simulate_maker_fill(md: MarketDataProvider, cfg: Settings, symbol: str, side: Side,
                        quantity: float, price: float) -> Fill:
    """Orden LIMIT pasiva llenada a su precio con comisión maker."""
    book = md.book(symbol)
    mid = book.mid if book else price
    buying = side == "LONG"
    adverse = max((price - mid) if buying else (mid - price), 0.0)
    return Fill(symbol=symbol, side=side, quantity=quantity, weighted_price=price,
                effective_price=price, mid_price=mid, fee=acc.fee(quantity, price, cfg.maker_fee),
                fee_rate=cfg.maker_fee, slippage_cost=adverse * quantity, s_latency=0.0)


def exit_trigger_price(book: BookSnapshot, side: Side) -> float:
    """Precio al que se podría cerrar ahora: bid para LONG, ask para SHORT."""
    return book.bids[0][0] if side == "LONG" else book.asks[0][0]
