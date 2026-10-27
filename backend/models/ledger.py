"""Tablas del Ledger 24/7 (SQLite en modo WAL)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PortfolioState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    initial_capital: float
    current_compound_equity: float
    available_balance: float
    allocated_margin: float = 0.0
    total_fees_paid: float = 0.0
    total_slippage_cost: float = 0.0
    total_funding_paid: float = 0.0
    high_water_mark: float
    max_drawdown_pct: float = 0.0
    is_running: bool = False
    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    side: str  # LONG / SHORT
    entry_price: float
    current_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    initial_stop_loss: float
    unrealized_pnl: float = 0.0
    accumulated_funding: float = 0.0
    entry_fee: float = 0.0
    entry_slippage: float = 0.0
    margin: float = 0.0
    breakeven_moved: bool = False
    opened_at: datetime = Field(default_factory=utcnow)
    status: str = Field(default="OPEN", index=True)  # OPEN / CLOSED


class TradeHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    position_id: int = Field(index=True)
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    entry_fee: float
    exit_fee: float
    funding_paid: float
    slippage_cost: float
    net_pnl: float
    equity_after: float
    exit_reason: str  # STOP_LOSS / TAKE_PROFIT / KILL_SWITCH / MANUAL
    opened_at: datetime
    closed_at: datetime = Field(default_factory=utcnow, index=True)


class AgentConsensusLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow, index=True)
    agent_id: str
    status: str
    summary_message: str
    token_cost: int = 0


class EquitySnapshot(SQLModel, table=True):
    """Punto de la curva de rendimiento compuesto (persistente entre reinicios)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow, index=True)
    equity: float
    unrealized_pnl: float = 0.0
