"""Construcción de payloads JSON para REST y WebSocket."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from backend.core.database import atomic
from backend.core.engine import TradingEngine
from backend.models.ledger import AgentConsensusLog, Position
from backend.services import capital_manager as cm
from backend.services.metrics import compute_metrics


def iso(dt: datetime) -> str:
    """ISO-8601 en UTC (SQLite puede devolver datetimes sin zona)."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def log_row(row: AgentConsensusLog) -> dict[str, Any]:
    return {"id": row.id, "timestamp": iso(row.timestamp), "agent_id": row.agent_id,
            "status": row.status, "message": row.summary_message, "token_cost": row.token_cost}


def position_row(p: Position) -> dict[str, Any]:
    data = p.model_dump()
    data["opened_at"] = iso(p.opened_at)
    data["notional"] = p.quantity * p.current_price
    return data


def portfolio_payload(engine: TradingEngine) -> dict[str, Any]:
    with atomic() as s:
        state = cm.get_portfolio(s)
        metrics = compute_metrics(s, state)
        positions = s.exec(select(Position).where(Position.status == "OPEN")).all()
        state_data = state.model_dump()
    state_data["updated_at"] = iso(state.updated_at)
    state_data["started_at"] = iso(state.started_at)
    return {
        "state": state_data,
        "metrics": metrics.model_dump(),
        "positions": [position_row(p) for p in positions],
        "pending_orders": [vars(o) for o in engine.broker.pending.values()],
        "running": engine.running,
        "mode": engine.cfg.execution_mode.value,
        "strategy": {sym: st.model_dump() for sym, st in engine.strategy.items()},
        "limits": {"max_risk_per_trade": engine.cfg.max_risk_per_trade,
                   "max_portfolio_risk": engine.cfg.max_portfolio_risk,
                   "max_daily_drawdown": engine.cfg.max_daily_drawdown},
    }


def stream_payload(engine: TradingEngine) -> dict[str, Any]:
    st = engine.stream
    markets = {}
    for symbol in st.symbols:
        book = st.books.get(symbol)
        mark = st.marks[symbol]
        markets[symbol] = {"price": st.last_price(symbol), "funding_rate": mark.funding_rate,
                           "spread_pct": book.spread_pct if book else None,
                           "imbalance": book.imbalance() if book else None}
    return {"connected": st.healthy, "markets": markets}


def telemetry_payload(engine: TradingEngine, logs: list[AgentConsensusLog]) -> dict[str, Any]:
    return {
        "type": "telemetry",
        **portfolio_payload(engine),
        "agents": [a.model_dump(mode="json") for a in engine.telemetry.agents.values()],
        "logs": [log_row(r) for r in logs],
        "stream": stream_payload(engine),
        "llm_enabled": engine.strategist.uses_llm,
    }
