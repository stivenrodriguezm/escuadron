"""Agente 05 — Ejecutor de Órdenes y gestor de posiciones abiertas."""
from __future__ import annotations

from typing import Protocol

from backend.core.config import Settings
from backend.models.ledger import Position
from backend.models.schemas import OrderResult, RiskDecision


class Broker(Protocol):
    async def place_order(self, symbol: str, side: str, quantity: float, stop_loss: float,
                          take_profit: float, order_type: str = "MARKET",
                          limit_price: float | None = None) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> bool: ...
    def get_positions(self) -> list[Position]: ...
    async def update_stop(self, position_id: int, new_stop: float) -> None: ...
    async def close_all(self, reason: str = "KILL_SWITCH") -> int: ...


def breakeven_price(side: str, entry_price: float, fee_rate: float) -> float:
    """Precio que cubre comisiones de entrada y salida (cero pérdida neta)."""
    if side == "LONG":
        return entry_price * (1 + fee_rate) / (1 - fee_rate)
    return entry_price * (1 - fee_rate) / (1 + fee_rate)


def reached_breakeven_trigger(side: str, entry: float, initial_stop: float, price: float,
                              breakeven_r: float) -> bool:
    """¿El precio avanzó breakeven_r × R a favor? breakeven_r ≤ 0 desactiva la regla."""
    initial_risk = abs(entry - initial_stop)
    if breakeven_r <= 0 or initial_risk <= 0:
        return False
    d = 1 if side == "LONG" else -1
    return d * (price - entry) / initial_risk >= breakeven_r


def should_move_to_breakeven(pos: Position, breakeven_r: float) -> bool:
    return not pos.breakeven_moved and reached_breakeven_trigger(
        pos.side, pos.entry_price, pos.initial_stop_loss, pos.current_price, breakeven_r)


class ExecutorAgent:
    agent_id = "05"
    name = "Ejecutor de Órdenes"

    def __init__(self, broker: Broker, cfg: Settings) -> None:
        self.broker = broker
        self.cfg = cfg

    async def execute(self, decision: RiskDecision) -> OrderResult:
        if decision.verdict != "APPROVED" or decision.side is None:
            return OrderResult(ok=False, message="Orden no aprobada por el Guardián")
        return await self.broker.place_order(
            decision.symbol, decision.side, decision.quantity, float(decision.stop_loss or 0),
            float(decision.take_profit or 0), order_type=decision.entry_type)

    async def manage_positions(self) -> list[str]:
        """Mueve el Stop-Loss a break-even cuando la ganancia supera breakeven_r × R."""
        actions: list[str] = []
        for pos in self.broker.get_positions():
            if should_move_to_breakeven(pos, self.cfg.breakeven_r):
                new_sl = breakeven_price(pos.side, pos.entry_price, self.cfg.taker_fee)
                await self.broker.update_stop(pos.id, new_sl)
                actions.append(f"SL de {pos.symbol} movido a break-even {new_sl:,.4f}")
        return actions
