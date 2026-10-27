"""VirtualBroker: ejecución Paper hiperrealista con dinero falso sobre datos reales."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

from sqlmodel import select

from backend.core import accounting as acc
from backend.core.config import Settings
from backend.core.database import atomic
from backend.core.fills import (MarketDataProvider, StaleBookError, exit_trigger_price,
                                simulate_maker_fill, simulate_market_fill)
from backend.models.ledger import Position, TradeHistory, utcnow
from backend.models.schemas import Fill, OrderResult, Side
from backend.services.capital_manager import apply_realized_pnl, get_portfolio

log = logging.getLogger("paper_broker")
EventCallback = Callable[[str, str], Awaitable[None]]  # (status, mensaje)
LIMIT_TTL_S = 60


@dataclass
class PendingOrder:
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    stop_loss: float
    take_profit: float
    expires_at: float


class VirtualBroker:
    """Misma interfaz que el conector real: place_order, cancel_order, get_positions."""

    def __init__(self, md: MarketDataProvider, cfg: Settings, on_event: EventCallback | None = None) -> None:
        self.md, self.cfg, self.on_event = md, cfg, on_event
        self.pending: dict[str, PendingOrder] = {}
        self._funding_watch: dict[str, tuple[int, float]] = {}

    async def _emit(self, status: str, msg: str) -> None:
        if self.on_event:
            await self.on_event(status, msg)

    # ---------------- interfaz de broker ----------------
    async def place_order(self, symbol: str, side: Side, quantity: float, stop_loss: float,
                          take_profit: float, order_type: Literal["MARKET", "LIMIT"] = "MARKET",
                          limit_price: float | None = None) -> OrderResult:
        if quantity <= 0:
            return OrderResult(ok=False, message="Cantidad inválida")
        if order_type == "LIMIT":
            book = self.md.book(symbol)
            if book is None:
                return OrderResult(ok=False, message="Libro no disponible")
            price = limit_price or (book.bids[0][0] if side == "LONG" else book.asks[0][0])
            oid = uuid.uuid4().hex[:12]
            self.pending[oid] = PendingOrder(oid, symbol, side, quantity, price, stop_loss,
                                             take_profit, time.time() + LIMIT_TTL_S)
            return OrderResult(ok=True, message=f"LIMIT {side} {quantity} @ {price} en espera", order_id=oid)
        try:
            fill = await self._market_fill(symbol, side, quantity, is_entry=True)
        except StaleBookError as exc:
            return OrderResult(ok=False, message=str(exc))
        pos_id = self._open_position(fill, stop_loss, take_profit)
        return OrderResult(ok=True, message=f"{side} {quantity} {symbol} @ {fill.effective_price:,.4f}",
                           order_id=f"paper-{pos_id}", position_id=pos_id, fill=fill)

    async def _market_fill(self, symbol: str, side: Side, quantity: float, is_entry: bool) -> Fill:
        """Punto de extensión: el broker real sustituye la simulación por una orden real."""
        return simulate_market_fill(self.md, self.cfg, symbol, side, quantity, is_entry)

    async def cancel_order(self, order_id: str) -> bool:
        return self.pending.pop(order_id, None) is not None

    def get_positions(self) -> list[Position]:
        with atomic() as s:
            return list(s.exec(select(Position).where(Position.status == "OPEN")).all())

    async def update_stop(self, position_id: int, new_stop: float) -> None:
        with atomic() as s:
            pos = s.get(Position, position_id)
            if pos and pos.status == "OPEN":
                pos.stop_loss = new_stop
                pos.breakeven_moved = True
                s.add(pos)

    async def close_position(self, position_id: int, reason: str) -> OrderResult:
        with atomic() as s:
            pos = s.get(Position, position_id)
        if pos is None or pos.status != "OPEN":
            return OrderResult(ok=False, message="Posición inexistente o cerrada")
        try:
            fill = await self._market_fill(pos.symbol, pos.side, pos.quantity, is_entry=False)
        except StaleBookError as exc:
            return OrderResult(ok=False, message=str(exc))
        trade = self._settle(pos.id, fill, reason)
        await self._emit("CERRADA", f"{reason} {pos.side} {pos.symbol} · PnL neto ${trade.net_pnl:+,.2f}")
        return OrderResult(ok=True, message=f"Cerrada {pos.symbol}", position_id=pos.id, fill=fill)

    async def close_all(self, reason: str = "KILL_SWITCH") -> int:
        self.pending.clear()
        closed = 0
        for pos in self.get_positions():
            if (await self.close_position(pos.id, reason)).ok:
                closed += 1
        return closed

    # ---------------- contabilidad atómica ----------------
    def _open_position(self, fill: Fill, stop_loss: float, take_profit: float) -> int:
        notional = fill.quantity * fill.effective_price
        margin = notional / self.cfg.max_leverage
        with atomic() as s:
            pos = Position(symbol=fill.symbol, side=fill.side, entry_price=fill.effective_price,
                           current_price=fill.mid_price, quantity=fill.quantity, stop_loss=stop_loss,
                           take_profit=take_profit, initial_stop_loss=stop_loss, entry_fee=fill.fee,
                           entry_slippage=fill.slippage_cost, margin=margin,
                           unrealized_pnl=-fill.fee - fill.slippage_cost)
            s.add(pos)
            state = get_portfolio(s)
            state.allocated_margin += margin
            state.available_balance = state.current_compound_equity - state.allocated_margin
            state.updated_at = utcnow()
            s.add(state)
            s.flush()
            return int(pos.id)

    def _settle(self, position_id: int, fill: Fill, reason: str) -> TradeHistory:
        with atomic() as s:
            pos = s.get(Position, position_id)
            gross = acc.gross_pnl(pos.side, pos.quantity, pos.entry_price, fill.effective_price)
            fees = pos.entry_fee + fill.fee + pos.accumulated_funding
            net = acc.net_pnl(pos.side, pos.quantity, pos.entry_price, fill.effective_price, fees)
            slip = pos.entry_slippage + fill.slippage_cost
            state = get_portfolio(s)
            state.allocated_margin = max(state.allocated_margin - pos.margin, 0.0)
            state = apply_realized_pnl(s, net, pos.entry_fee + fill.fee, slip, pos.accumulated_funding)
            pos.status, pos.current_price, pos.unrealized_pnl = "CLOSED", fill.effective_price, 0.0
            s.add(pos)
            trade = TradeHistory(
                position_id=pos.id, symbol=pos.symbol, side=pos.side, quantity=pos.quantity,
                entry_price=pos.entry_price, exit_price=fill.effective_price, gross_pnl=gross,
                entry_fee=pos.entry_fee, exit_fee=fill.fee, funding_paid=pos.accumulated_funding,
                slippage_cost=slip, net_pnl=net, equity_after=state.current_compound_equity,
                exit_reason=reason, opened_at=pos.opened_at)
            s.add(trade)
            return trade

    # ---------------- vigilancia de ticks (cada 500 ms) ----------------
    async def watch_tick(self) -> None:
        await self._process_pending()
        now_ms = int(time.time() * 1000)
        with atomic() as s:
            positions = list(s.exec(select(Position).where(Position.status == "OPEN")).all())
            to_close: list[tuple[int, str]] = []
            for pos in positions:
                book = self.md.book(pos.symbol)
                if book is None:
                    continue
                self._apply_funding(pos, now_ms)
                px = exit_trigger_price(book, pos.side)
                d = 1 if pos.side == "LONG" else -1
                pos.current_price = book.mid
                est_exit_fee = acc.fee(pos.quantity, px, self.cfg.taker_fee)
                pos.unrealized_pnl = (acc.gross_pnl(pos.side, pos.quantity, pos.entry_price, px)
                                      - pos.entry_fee - est_exit_fee - pos.accumulated_funding)
                s.add(pos)
                if d * (px - pos.stop_loss) <= 0:
                    to_close.append((pos.id, "BREAK_EVEN" if pos.breakeven_moved else "STOP_LOSS"))
                elif d * (px - pos.take_profit) >= 0:
                    to_close.append((pos.id, "TAKE_PROFIT"))
        self._refresh_funding_watch(now_ms)
        for pid, reason in to_close:
            await self.close_position(pid, reason)

    def _apply_funding(self, pos: Position, now_ms: int) -> None:
        watch = self._funding_watch.get(pos.symbol)
        if watch and now_ms >= watch[0] and pos.opened_at.timestamp() * 1000 < watch[0]:
            mark = self.md.marks[pos.symbol].mark_price or pos.current_price
            pos.accumulated_funding += acc.funding_payment(pos.side, pos.quantity, mark, watch[1])

    def _refresh_funding_watch(self, now_ms: int) -> None:
        for symbol, mark in self.md.marks.items():
            watch = self._funding_watch.get(symbol)
            if watch and now_ms >= watch[0]:
                del self._funding_watch[symbol]  # ya aplicado en este tick
            if mark.next_funding_time and now_ms < mark.next_funding_time:
                self._funding_watch[symbol] = (mark.next_funding_time, mark.funding_rate)

    async def _process_pending(self) -> None:
        for oid, o in list(self.pending.items()):
            book = self.md.book(o.symbol)
            if time.time() > o.expires_at:
                self.pending.pop(oid, None)
                await self._emit("CANCELADA", f"LIMIT {o.side} {o.symbol} expiró sin llenarse")
                continue
            if book is None:
                continue
            crossed = book.asks[0][0] <= o.price if o.side == "LONG" else book.bids[0][0] >= o.price
            if crossed:
                self.pending.pop(oid, None)
                fill = simulate_maker_fill(self.md, self.cfg, o.symbol, o.side, o.quantity, o.price)
                self._open_position(fill, o.stop_loss, o.take_profit)
                await self._emit("EJECUTADA", f"LIMIT {o.side} {o.quantity} {o.symbol} @ {o.price:,.4f}")


async def run_watch_loop(broker: VirtualBroker, interval_ms: int) -> None:
    while True:
        try:
            await broker.watch_tick()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("Error en el bucle de vigilancia")
        await asyncio.sleep(interval_ms / 1000)
