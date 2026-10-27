"""Gestión del capital virtual (dinero falso) con interés compuesto."""
from __future__ import annotations

from typing import Literal

from sqlmodel import Session, delete, select

from backend.core.config import get_settings
from backend.core.database import atomic
from backend.models.ledger import (EquitySnapshot, Position, PortfolioState,
                                   TradeHistory, utcnow)

PORTFOLIO_ID = 1


def get_portfolio(session: Session) -> PortfolioState:
    """Devuelve el estado único de cartera, creándolo si no existe."""
    state = session.get(PortfolioState, PORTFOLIO_ID)
    if state is None:
        capital = get_settings().default_virtual_capital
        state = PortfolioState(id=PORTFOLIO_ID, initial_capital=capital,
                               current_compound_equity=capital, available_balance=capital,
                               high_water_mark=capital)
        session.add(state)
        session.add(EquitySnapshot(equity=capital))
        session.flush()
    return state


def init_virtual_capital(amount: float) -> PortfolioState:
    """Inicializa la cartera con cualquier monto elegido por el usuario."""
    if amount <= 0:
        raise ValueError("El capital inicial debe ser positivo")
    with atomic() as s:
        state = s.get(PortfolioState, PORTFOLIO_ID)
        if state is not None:
            return state
        state = PortfolioState(id=PORTFOLIO_ID, initial_capital=amount,
                               current_compound_equity=amount, available_balance=amount,
                               high_water_mark=amount)
        s.add(state)
        s.add(EquitySnapshot(equity=amount))
        return state


def set_virtual_capital(new_amount: float,
                        mode: Literal["RESCALE", "RESET"] = "RESCALE") -> PortfolioState:
    """Modifica el capital en caliente.

    RESCALE: escala proporcionalmente balance, capital base, HWM y la curva
    histórica, preservando el rendimiento porcentual acumulado.
    RESET: reinicia la curva compuesta desde cero (requiere 0 posiciones abiertas).
    """
    if new_amount <= 0:
        raise ValueError("El capital debe ser positivo")
    with atomic() as s:
        state = get_portfolio(s)
        open_count = len(s.exec(select(Position).where(Position.status == "OPEN")).all())
        if mode == "RESET":
            if open_count:
                raise RuntimeError("Cierra las posiciones abiertas antes de reiniciar")
            s.exec(delete(TradeHistory))
            s.exec(delete(EquitySnapshot))
            s.exec(delete(Position))
            state.initial_capital = new_amount
            state.current_compound_equity = new_amount
            state.available_balance = new_amount
            state.allocated_margin = 0.0
            state.total_fees_paid = state.total_slippage_cost = state.total_funding_paid = 0.0
            state.high_water_mark = new_amount
            state.max_drawdown_pct = 0.0
            state.started_at = utcnow()
            s.add(EquitySnapshot(equity=new_amount))
        else:
            factor = new_amount / state.current_compound_equity
            state.initial_capital *= factor
            state.current_compound_equity = new_amount
            state.high_water_mark *= factor
            state.available_balance = new_amount - state.allocated_margin
            for snap in s.exec(select(EquitySnapshot)).all():
                snap.equity *= factor
                s.add(snap)
            s.add(EquitySnapshot(equity=new_amount))
        state.updated_at = utcnow()
        s.add(state)
        return state


def apply_realized_pnl(session: Session, pnl_net: float, fees: float, slippage: float,
                       funding: float) -> PortfolioState:
    """E_{t+1} = E_t + PnL neto; actualiza HWM y drawdown máximo (misma transacción)."""
    from backend.core.accounting import compound

    state = get_portfolio(session)
    state.current_compound_equity = compound(state.current_compound_equity, pnl_net)
    state.total_fees_paid += fees
    state.total_slippage_cost += slippage
    state.total_funding_paid += funding
    update_drawdown(state, state.current_compound_equity)
    state.available_balance = state.current_compound_equity - state.allocated_margin
    state.updated_at = utcnow()
    session.add(state)
    return state


def update_drawdown(state: PortfolioState, equity_mark: float) -> None:
    state.high_water_mark = max(state.high_water_mark, equity_mark)
    if state.high_water_mark > 0:
        dd = (state.high_water_mark - equity_mark) / state.high_water_mark * 100
        state.max_drawdown_pct = max(state.max_drawdown_pct, dd)


def set_running(running: bool) -> None:
    with atomic() as s:
        state = get_portfolio(s)
        state.is_running = running
        state.updated_at = utcnow()
        s.add(state)


def record_snapshot(unrealized: float) -> None:
    with atomic() as s:
        state = get_portfolio(s)
        update_drawdown(state, state.current_compound_equity + unrealized)
        s.add(state)
        s.add(EquitySnapshot(equity=state.current_compound_equity + unrealized,
                             unrealized_pnl=unrealized))
