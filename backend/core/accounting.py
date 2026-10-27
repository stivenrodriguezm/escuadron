"""Fórmulas contables obligatorias del motor (Sección 3 del plan maestro).

Funciones puras, sin I/O: las usa el VirtualBroker en vivo, el Guardián de
Riesgo y el backtester headless, garantizando la misma matemática en todos.
"""
from __future__ import annotations

import math
from typing import Literal, Sequence

Side = Literal["LONG", "SHORT"]
BookLevels = Sequence[tuple[float, float]]  # [(precio, cantidad), ...] mejor nivel primero


def risk_usd(equity: float, r_max: float) -> float:
    """R_usd = E_t × r_max."""
    if equity <= 0 or r_max <= 0:
        return 0.0
    return equity * r_max


def position_size(equity: float, r_max: float, entry: float, stop_loss: float) -> float:
    """Q = R_usd / |P_entrada_efectivo − P_stop_loss|."""
    distance = abs(entry - stop_loss)
    if distance <= 0:
        raise ValueError("La distancia al Stop-Loss debe ser mayor que cero")
    return risk_usd(equity, r_max) / distance


def weighted_fill_price(levels: BookLevels, quantity: float, overflow_penalty: float = 0.001) -> float:
    """P_ponderado(Q): recorre los niveles L2 reales hasta cubrir Q.

    Si el libro visible no alcanza, el remanente se llena al último nivel con
    una penalización adicional (liquidez oculta más profunda y peor).
    """
    if quantity <= 0:
        raise ValueError("La cantidad debe ser positiva")
    if not levels:
        raise ValueError("Libro de órdenes vacío")
    remaining, cost = quantity, 0.0
    last_price = levels[0][0]
    for price, size in levels:
        take = min(remaining, size)
        cost += take * price
        remaining -= take
        last_price = price
        if remaining <= 1e-12:
            return cost / quantity
    direction = 1.0 if levels[-1][0] >= levels[0][0] else -1.0  # asks suben, bids bajan
    cost += remaining * last_price * (1 + direction * overflow_penalty)
    return cost / quantity


def latency_slippage(sigma_per_second: float, latency_ms: float, floor: float) -> float:
    """s_latencia: movimiento esperado del precio durante la latencia de red.

    σ_latencia = σ_1s × √(latencia_s). Nunca cero: se aplica un mínimo.
    """
    s = max(sigma_per_second, 0.0) * math.sqrt(max(latency_ms, 0.0) / 1000.0)
    return max(s, floor)


def effective_price(weighted_price: float, side: Side, is_entry: bool, s_latency: float) -> float:
    """P_efectivo = P_ponderado × (1 ± s_latencia), siempre en contra del trader.

    LONG entra comprando (asks) y sale vendiendo (bids); SHORT al revés.
    """
    buying = (side == "LONG") == is_entry
    return weighted_price * (1 + s_latency) if buying else weighted_price * (1 - s_latency)


def fee(quantity: float, price: float, fee_rate: float) -> float:
    """Comisión de una pierna: Q × P × f_rate."""
    return abs(quantity) * price * fee_rate


def total_fees(quantity: float, entry: float, exit_: float, fee_rate_entry: float,
               fee_rate_exit: float, funding: float = 0.0) -> float:
    """F = (Q·P_entrada·f) + (Q·P_salida·f) + F_funding."""
    return fee(quantity, entry, fee_rate_entry) + fee(quantity, exit_, fee_rate_exit) + funding


def gross_pnl(side: Side, quantity: float, entry: float, exit_: float) -> float:
    """Q × (P_salida − P_entrada), con signo invertido para SHORT."""
    direction = 1.0 if side == "LONG" else -1.0
    return direction * quantity * (exit_ - entry)


def net_pnl(side: Side, quantity: float, entry: float, exit_: float, fees: float) -> float:
    """PnL Neto = Q × (P_salida − P_entrada) − F."""
    return gross_pnl(side, quantity, entry, exit_) - fees


def compound(equity: float, pnl_net: float) -> float:
    """E_{t+1} = E_t + PnL Neto."""
    return equity + pnl_net


def funding_payment(side: Side, quantity: float, mark_price: float, funding_rate: float) -> float:
    """Costo de funding (positivo = pago). Con tasa > 0 los LONG pagan a los SHORT."""
    direction = 1.0 if side == "LONG" else -1.0
    return direction * quantity * mark_price * funding_rate


def net_reward_risk(side: Side, entry: float, stop_loss: float, take_profit: float,
                    fee_rate: float) -> float:
    """Relación beneficio/riesgo neta por unidad, restando comisiones estimadas."""
    direction = 1.0 if side == "LONG" else -1.0
    reward = direction * (take_profit - entry) - (entry + take_profit) * fee_rate
    risk = direction * (entry - stop_loss) + (entry + stop_loss) * fee_rate
    if risk <= 0:
        return 0.0
    return max(reward, 0.0) / risk


def slippage_cost(quantity: float, effective: float, mid: float) -> float:
    """Costo de spread + slippage frente al precio medio (siempre ≥ 0)."""
    return abs(effective - mid) * abs(quantity)
