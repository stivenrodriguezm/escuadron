"""Agente 04 — Guardián de Riesgo. 100% código duro determinista.

Ninguna propuesta del LLM llega al broker sin pasar estas reglas de fuego.
"""
from __future__ import annotations

import math

from pydantic import BaseModel, Field

from backend.core import accounting as acc
from backend.core.config import Settings
from backend.models.schemas import RiskDecision, TradeProposal

ATR_STOP_RANGE = (0.5, 4.0)  # distancia al SL en múltiplos de ATR


class PortfolioView(BaseModel):
    """Foto mínima de la cartera que necesita el Guardián."""
    equity: float = Field(gt=0)
    daily_pnl: float = 0.0
    day_base_equity: float = Field(gt=0)
    risk_committed_usd: float = 0.0
    notional_open: float = 0.0
    open_symbols: list[str] = Field(default_factory=list)


def _floor(x: float, decimals: int = 6) -> float:
    f = 10 ** decimals
    return math.floor(x * f) / f


class RiskGuardian:
    agent_id = "04"
    name = "Guardián de Riesgo"

    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg

    def evaluate(self, p: TradeProposal, reference_entry: float, atr: float,
                 view: PortfolioView) -> RiskDecision:
        cfg = self.cfg
        base = {"symbol": p.symbol, "entry_type": p.entry_type}
        if p.action == "HOLD":
            return RiskDecision(verdict="VETOED", reason="Sin operación propuesta (HOLD)", **base)
        side = "LONG" if p.action == "BUY" else "SHORT"
        d = 1 if side == "LONG" else -1
        sl, tp = p.suggested_stop_loss, p.suggested_take_profit
        checks: dict[str, bool] = {}

        def veto(reason: str) -> RiskDecision:
            return RiskDecision(verdict="VETOED", reason=reason, side=side, reference_entry=reference_entry,
                                stop_loss=sl, take_profit=tp, checks=checks, **base)

        # Reglas previas: datos completos y coherentes.
        checks["stop_loss_present"] = bool(sl and sl > 0 and d * (reference_entry - sl) > 0)
        if not checks["stop_loss_present"]:
            return veto("Stop-Loss ausente o del lado incorrecto")
        checks["take_profit_present"] = bool(tp and tp > 0 and d * (tp - reference_entry) > 0)
        if not checks["take_profit_present"]:
            return veto("Take-Profit ausente o del lado incorrecto")
        checks["no_duplicate"] = p.symbol not in view.open_symbols
        if not checks["no_duplicate"]:
            return veto(f"Ya existe una posición abierta en {p.symbol}")

        # Regla 1: R/B neta tras comisiones de entrada y salida.
        fee_rate = cfg.maker_fee if p.entry_type == "LIMIT" else cfg.taker_fee
        rr = acc.net_reward_risk(side, reference_entry, sl, tp, fee_rate)
        checks["reward_risk"] = rr >= cfg.min_reward_risk
        if not checks["reward_risk"]:
            return veto(f"R/B neta 1:{rr:.2f} < 1:{cfg.min_reward_risk:.1f}")

        # Regla 2: pérdida diaria acumulada.
        daily_loss_pct = -view.daily_pnl / view.day_base_equity
        checks["daily_loss"] = daily_loss_pct < cfg.max_daily_drawdown
        if not checks["daily_loss"]:
            return veto(f"Pérdida diaria {daily_loss_pct * 100:.2f}% ≥ límite {cfg.max_daily_drawdown * 100:.1f}%")

        # Regla 4: coherencia del Stop con el ATR.
        dist_atr = abs(reference_entry - sl) / atr if atr > 0 else 0.0
        checks["atr_coherence"] = ATR_STOP_RANGE[0] <= dist_atr <= ATR_STOP_RANGE[1]
        if not checks["atr_coherence"]:
            return veto(f"Stop a {dist_atr:.2f} ATR fuera de [{ATR_STOP_RANGE[0]}, {ATR_STOP_RANGE[1]}]")

        # Regla 5: tamaño exacto Q con interés compuesto sobre E_t.
        qty = acc.position_size(view.equity, cfg.max_risk_per_trade, reference_entry, sl)
        max_notional = view.equity * cfg.max_leverage - view.notional_open
        if qty * reference_entry > max_notional:
            qty = max(max_notional, 0.0) / reference_entry
        qty = _floor(qty)
        risk = round(qty * abs(reference_entry - sl), 2)

        # Regla 3: exposición total de la cartera.
        total_risk_pct = (view.risk_committed_usd + risk) / view.equity
        checks["exposure"] = total_risk_pct <= cfg.max_portfolio_risk + 1e-9
        if not checks["exposure"]:
            return veto(f"Exposición {total_risk_pct * 100:.2f}% > máx {cfg.max_portfolio_risk * 100:.1f}%")
        checks["min_notional"] = qty * reference_entry >= cfg.min_notional_usdt
        if not checks["min_notional"]:
            return veto(f"Nocional {qty * reference_entry:.2f} USDT bajo el mínimo")

        return RiskDecision(
            verdict="APPROVED", side=side, reference_entry=reference_entry, stop_loss=sl, take_profit=tp,
            quantity=qty, risk_usd=risk, reward_risk=round(rr, 3), checks=checks,
            reason=f"Q={qty} · riesgo ${risk:,.2f} ({risk / view.equity * 100:.2f}%) · R/B 1:{rr:.2f}",
            **base)
