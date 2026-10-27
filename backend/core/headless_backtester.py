"""Laboratorio de calibración headless, basado en eventos y sin sesgo de futuro.

Reglas punto-en-el-tiempo:
- La señal se calcula con el cierre de la vela i (indicadores causales).
- La entrada se ejecuta en la APERTURA de la vela i+1 (nunca al cierre de i).
- SL/TP se evalúan con máximo/mínimo de cada vela; si ambos se tocan en la
  misma vela se asume el Stop primero (supuesto conservador).
Usa exactamente el Agente Quant, el Guardián de Riesgo, la regla de break-even
del Ejecutor y las fórmulas de fricción del modo en vivo. El Estratega usa su respaldo determinista (0 tokens).
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass

from backend.agents.executor_agent import breakeven_price, reached_breakeven_trigger
from backend.agents.indicators import IndicatorSeries
from backend.agents.quant_agent import score_at
from backend.agents.risk_guardian import PortfolioView, RiskGuardian
from backend.agents.sentiment_agent import evaluate as sentiment_eval
from backend.agents.strategist_agent import deterministic_proposal
from backend.core import accounting as acc
from backend.core.config import Settings
from backend.models.schemas import BacktestResult, QuantSignal
from backend.services.metrics import annualized_sharpe

HALF_SPREAD = 0.00005  # 0.5 pb: medio spread típico en pares líquidos de Binance Futures
DAY_MS = 86_400_000


@dataclass
class _Open:
    side: str
    qty: float
    entry: float
    sl: float
    tp: float
    entry_fee: float
    slippage: float
    funding: float
    opened_ms: int
    init_sl: float = 0.0
    be_moved: bool = False


def _fill(ref: float, side: str, is_entry: bool, s_lat: float) -> float:
    buying = (side == "LONG") == is_entry
    quoted = ref * (1 + HALF_SPREAD) if buying else ref * (1 - HALF_SPREAD)
    return acc.effective_price(quoted, side, is_entry, s_lat)


def precompute_signals(series: IndicatorSeries, symbol: str) -> list[QuantSignal | None]:
    """Señales del Quant por vela (independientes de umbral/SL/TP): se calculan una vez por serie."""
    return [score_at(series, i, symbol, 1.0, 1.0) for i in range(len(series.closes))]


def _signal_for(cache: list[QuantSignal | None], i: int, sl_mult: float, tp_mult: float) -> QuantSignal | None:
    sig = cache[i]
    if sig is None:
        return None
    d = 1 if sig.direction == "LONG" else -1
    return sig.model_copy(update={"suggested_stop_loss": sig.price - d * sl_mult * sig.atr14,
                                  "suggested_take_profit": sig.price + d * tp_mult * sig.atr14})


def run_backtest(series: IndicatorSeries, funding: list[tuple[int, float]], symbol: str,
                 interval_ms: int, cfg: Settings, threshold: float, sl_mult: float,
                 tp_mult: float, capital: float,
                 signal_cache: list[QuantSignal | None] | None = None) -> BacktestResult:
    guardian = RiskGuardian(cfg)
    f_times = [t for t, _ in funding]
    equity, day_start_eq, day = capital, capital, -1
    pos: _Open | None = None
    pending = None
    fees = slip = fund_total = 0.0
    wins = trades = 0
    curve: list[tuple[int, float]] = []
    hwm, max_dd = capital, 0.0
    sec_per_bar = interval_ms / 1000

    def close(exit_ref: float, s_lat: float) -> None:
        nonlocal equity, pos, fees, slip, fund_total, wins, trades
        exit_px = _fill(exit_ref, pos.side, False, s_lat)
        exit_fee = acc.fee(pos.qty, exit_px, cfg.taker_fee)
        total = pos.entry_fee + exit_fee + pos.funding
        pnl = acc.net_pnl(pos.side, pos.qty, pos.entry, exit_px, total)
        equity = acc.compound(equity, pnl)
        fees += pos.entry_fee + exit_fee
        slip += pos.slippage + acc.slippage_cost(pos.qty, exit_px, exit_ref)
        fund_total += pos.funding
        trades += 1
        wins += pnl > 0
        pos = None

    for i in range(len(series.closes)):
        t, o, h, l, c = (series.open_times[i], series.opens[i], series.highs[i],
                         series.lows[i], series.closes[i])
        if t // DAY_MS != day:
            day, day_start_eq = t // DAY_MS, equity
        atr_prev = series.atr14[i - 1] if i else float("nan")
        sigma = (atr_prev / c) / math.sqrt(sec_per_bar) if not math.isnan(atr_prev) else 0.0
        s_lat = acc.latency_slippage(sigma, cfg.latency_ms, cfg.min_latency_slippage)

        # 1) Entrada en la apertura de i con la señal del cierre de i-1.
        if pending is not None and pos is None:
            signal, sentiment = pending
            proposal = deterministic_proposal(signal, sentiment)
            side = "LONG" if proposal.action == "BUY" else "SHORT"
            ref = o * (1 + HALF_SPREAD) if side == "LONG" else o * (1 - HALF_SPREAD)
            view = PortfolioView(equity=equity, daily_pnl=equity - day_start_eq, day_base_equity=day_start_eq)
            decision = guardian.evaluate(proposal, ref, signal.atr14, view)
            if decision.verdict == "APPROVED":
                entry = _fill(o, side, True, s_lat)
                pos = _Open(side, decision.quantity, entry, decision.stop_loss, decision.take_profit,
                            acc.fee(decision.quantity, entry, cfg.taker_fee),
                            acc.slippage_cost(decision.quantity, entry, o), 0.0, t, decision.stop_loss)
        pending = None

        # 2) Gestión de la posición dentro de la vela i.
        if pos is not None:
            # funding con marca de tiempo dentro de esta vela y posterior a la apertura
            lo = bisect.bisect_left(f_times, max(t, pos.opened_ms + 1))
            hi = bisect.bisect_left(f_times, t + interval_ms)
            for k in range(lo, hi):
                pos.funding += acc.funding_payment(pos.side, pos.qty, c, funding[k][1])
            d = 1 if pos.side == "LONG" else -1
            stop_hit = (l <= pos.sl) if d > 0 else (h >= pos.sl)
            tp_hit = (h >= pos.tp) if d > 0 else (l <= pos.tp)
            if stop_hit:
                gapped = (o < pos.sl) if d > 0 else (o > pos.sl)
                close(o if gapped else pos.sl, s_lat)
            elif tp_hit:
                close(pos.tp, s_lat)
            # Agente 05: stop a break-even tras +breakeven_r·R (vigente desde la vela siguiente)
            if pos is not None and not pos.be_moved and reached_breakeven_trigger(
                    pos.side, pos.entry, pos.init_sl, h if d > 0 else l, cfg.breakeven_r):
                pos.sl, pos.be_moved = breakeven_price(pos.side, pos.entry, cfg.taker_fee), True

        # 3) Señal al cierre de i (se ejecutará en i+1).
        if pos is None and i + 1 < len(series.closes):
            if signal_cache is not None:
                cached = signal_cache[i]
                signal = (_signal_for(signal_cache, i, sl_mult, tp_mult)
                          if cached is not None and cached.setup_score >= threshold else None)
            else:
                signal = score_at(series, i, symbol, sl_mult, tp_mult)
            if signal is not None and signal.setup_score >= threshold:
                fr_idx = bisect.bisect_right(f_times, t + interval_ms) - 1
                fr = funding[fr_idx][1] if fr_idx >= 0 else 0.0
                px_chg = (c / series.closes[max(i - 10, 0)] - 1) * 100
                pending = (signal, sentiment_eval(symbol, fr, 0.0, px_chg, None))

        marked = equity
        if pos is not None:
            marked += acc.gross_pnl(pos.side, pos.qty, pos.entry, c) - pos.entry_fee - pos.funding
        hwm = max(hwm, marked)
        max_dd = max(max_dd, (hwm - marked) / hwm * 100 if hwm else 0.0)
        curve.append((t, marked))

    if pos is not None:  # cierre forzado al final del rango
        close(series.closes[-1], acc.latency_slippage(0.0, cfg.latency_ms, cfg.min_latency_slippage))
        curve.append((series.open_times[-1] + interval_ms, equity))

    stride = max(1, len(curve) // 400)
    bars_per_year = 365 * DAY_MS / interval_ms
    return BacktestResult(
        symbol=symbol, interval="", score_threshold=threshold, sl_atr_mult=sl_mult, tp_atr_mult=tp_mult,
        initial_capital=capital, final_equity=round(equity, 2),
        compound_return_pct=round((equity / capital - 1) * 100, 3), trades=trades,
        win_rate_pct=round(wins / trades * 100, 2) if trades else 0.0,
        sharpe_ratio=round(annualized_sharpe([v for _, v in curve], bars_per_year), 3),
        max_drawdown_pct=round(max_dd, 3), total_fees=round(fees, 2), total_slippage=round(slip, 2),
        total_funding=round(fund_total, 2),
        equity_curve=[(ts, round(v, 2)) for ts, v in curve[::stride]])
