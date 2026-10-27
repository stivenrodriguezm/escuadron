"""Métricas en vivo de la cartera: rendimiento, Sharpe, win rate, exposición."""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from typing import Sequence

from pydantic import BaseModel
from sqlmodel import Session, func, select

from backend.models.ledger import (EquitySnapshot, Position, PortfolioState,
                                   TradeHistory, utcnow)


class PortfolioMetrics(BaseModel):
    equity: float
    equity_with_unrealized: float
    unrealized_pnl: float
    total_return_pct: float
    daily_pnl: float
    daily_return_pct: float
    daily_friction: float
    sharpe_ratio: float
    win_rate_pct: float
    trades_count: int
    exposure_pct: float
    risk_committed_pct: float
    max_drawdown_pct: float


def position_risk_usd(p: Position) -> float:
    """Pérdida si se toca el SL actual (0 si el SL ya está en break-even o ganancia)."""
    direction = 1.0 if p.side == "LONG" else -1.0
    return max(direction * (p.entry_price - p.stop_loss) * p.quantity, 0.0)


def annualized_sharpe(values: Sequence[float], periods_per_year: float) -> float:
    if len(values) < 3:
        return 0.0
    rets = [values[i] / values[i - 1] - 1 for i in range(1, len(values)) if values[i - 1] > 0]
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    std = math.sqrt(var)
    return 0.0 if std == 0 else mean / std * math.sqrt(periods_per_year)


def hourly_equity(snapshots: Sequence[EquitySnapshot]) -> list[float]:
    """Último valor de equity por hora (remuestreo de snapshots de 1 minuto)."""
    buckets: dict[datetime, float] = {}
    for snap in snapshots:
        buckets[snap.timestamp.replace(minute=0, second=0, microsecond=0)] = snap.equity
    return [buckets[k] for k in sorted(buckets)]


_SHARPE_CACHE: dict[str, float] = {"at": 0.0, "value": 0.0}
SHARPE_TTL_S = 60


def _cached_sharpe(session: Session) -> float:
    """Sharpe anualizado sobre equity horaria (90 días); se recalcula como máximo cada 60 s."""
    if time.time() - _SHARPE_CACHE["at"] < SHARPE_TTL_S:
        return _SHARPE_CACHE["value"]
    since = utcnow() - timedelta(days=90)
    snaps = session.exec(select(EquitySnapshot).where(EquitySnapshot.timestamp >= since)
                         .order_by(EquitySnapshot.timestamp)).all()
    _SHARPE_CACHE.update(at=time.time(), value=annualized_sharpe(hourly_equity(snaps), 24 * 365))
    return _SHARPE_CACHE["value"]


def compute_metrics(session: Session, state: PortfolioState) -> PortfolioMetrics:
    positions = session.exec(select(Position).where(Position.status == "OPEN")).all()
    unrealized = sum(p.unrealized_pnl for p in positions)
    equity = state.current_compound_equity
    marked = equity + unrealized

    day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = session.exec(select(TradeHistory).where(TradeHistory.closed_at >= day_start)).all()
    realized_today = sum(t.net_pnl for t in today)
    friction_today = sum(t.entry_fee + t.exit_fee + t.slippage_cost + t.funding_paid for t in today)
    friction_today += sum(p.entry_fee + p.entry_slippage for p in positions if p.opened_at >= day_start)
    daily_pnl = realized_today + unrealized
    day_base = equity - realized_today

    trades_count = session.exec(select(func.count()).select_from(TradeHistory)).one()
    wins = session.exec(select(func.count()).select_from(TradeHistory).where(TradeHistory.net_pnl > 0)).one()
    sharpe = _cached_sharpe(session)

    notional = sum(p.quantity * p.current_price for p in positions)
    risk = sum(position_risk_usd(p) for p in positions)
    return PortfolioMetrics(
        equity=equity,
        equity_with_unrealized=marked,
        unrealized_pnl=unrealized,
        total_return_pct=(marked / state.initial_capital - 1) * 100 if state.initial_capital else 0.0,
        daily_pnl=daily_pnl,
        daily_return_pct=daily_pnl / day_base * 100 if day_base > 0 else 0.0,
        daily_friction=friction_today,
        sharpe_ratio=round(sharpe, 3),
        win_rate_pct=wins / trades_count * 100 if trades_count else 0.0,
        trades_count=trades_count,
        exposure_pct=notional / equity * 100 if equity > 0 else 0.0,
        risk_committed_pct=risk / equity * 100 if equity > 0 else 0.0,
        max_drawdown_pct=state.max_drawdown_pct,
    )
