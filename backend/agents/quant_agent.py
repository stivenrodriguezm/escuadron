"""Agente 01 — Analista Cuantitativo. 100% determinista (0 tokens)."""
from __future__ import annotations

from typing import Optional

from backend.agents.indicators import IndicatorSeries
from backend.models.schemas import Candle, QuantSignal

WEIGHTS = {"trend": 25, "structure": 20, "breakout": 20, "volume": 15, "volatility": 10, "momentum": 10}
ATR_PCT_RANGE = (0.15, 2.5)  # volatilidad operable en % del precio


def score_at(series: IndicatorSeries, i: int, symbol: str, sl_atr_mult: float,
             tp_atr_mult: float, book_imbalance: Optional[float] = None) -> Optional[QuantSignal]:
    """Puntúa el setup en el índice i usando solo información ≤ i."""
    if not series.ready(i):
        return None
    close, atr_v = series.closes[i], series.atr14[i]
    e20, e50, e200 = series.ema20[i], series.ema50[i], series.ema200[i]
    d = 1 if e20 > e50 else -1
    comp: dict[str, float] = {}

    aligned = (e20 > e50 > e200) if d > 0 else (e20 < e50 < e200)
    price_side = (close > e200) if d > 0 else (close < e200)
    comp["trend"] = WEIGHTS["trend"] * (1.0 if aligned else 0.6 if price_side else 0.3)

    structure = series.structure(i)
    wanted = "BULLISH" if d > 0 else "BEARISH"
    comp["structure"] = WEIGHTS["structure"] * (1.0 if structure == wanted else 0.3 if structure == "RANGE" else 0.0)

    broke, dist = series.breakout(i, d)
    comp["breakout"] = WEIGHTS["breakout"] * (1.0 if broke else 0.4 if -dist < 0.25 * atr_v else 0.0)

    vz = series.vol_z[i]
    comp["volume"] = WEIGHTS["volume"] * min(max(vz, 0.0) / 2.0, 1.0)

    atr_pct = atr_v / close * 100
    comp["volatility"] = WEIGHTS["volatility"] * (1.0 if ATR_PCT_RANGE[0] <= atr_pct <= ATR_PCT_RANGE[1] else 0.0)

    r = series.rsi14[i]
    core, soft = ((50, 70), (45, 78)) if d > 0 else ((30, 50), (22, 55))
    comp["momentum"] = WEIGHTS["momentum"] * (1.0 if core[0] <= r <= core[1] else 0.5 if soft[0] <= r <= soft[1] else 0.0)

    if book_imbalance is not None:  # confirmación de microestructura (solo en vivo)
        comp["order_book"] = max(-5.0, min(5.0, d * book_imbalance * 10))

    score = max(0.0, min(100.0, sum(comp.values())))
    return QuantSignal(
        symbol=symbol, timestamp=series.open_times[i], price=close,
        direction="LONG" if d > 0 else "SHORT", setup_score=round(score, 2),
        ema20=e20, ema50=e50, ema200=e200, rsi14=r, atr14=atr_v, atr_pct=round(atr_pct, 4),
        volume_z=round(vz, 3), structure=structure, breakout=broke,
        order_book_imbalance=book_imbalance,
        suggested_stop_loss=close - d * sl_atr_mult * atr_v,
        suggested_take_profit=close + d * tp_atr_mult * atr_v,
        components={k: round(v, 2) for k, v in comp.items()},
    )


def series_from_candles(candles: list[Candle]) -> IndicatorSeries:
    return IndicatorSeries.build(
        [c.open_time for c in candles], [c.open for c in candles], [c.high for c in candles],
        [c.low for c in candles], [c.close for c in candles], [c.volume for c in candles])


class QuantAgent:
    agent_id = "01"
    name = "Analista Cuantitativo"

    def __init__(self, sl_atr_mult: float, tp_atr_mult: float, threshold: float) -> None:
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.threshold = threshold

    def analyze(self, symbol: str, candles: list[Candle],
                book_imbalance: Optional[float] = None) -> Optional[QuantSignal]:
        if len(candles) < 210:
            return None
        series = series_from_candles(candles)
        return score_at(series, len(candles) - 1, symbol, self.sl_atr_mult,
                        self.tp_atr_mult, book_imbalance)

    def is_actionable(self, signal: Optional[QuantSignal]) -> bool:
        return signal is not None and signal.setup_score >= self.threshold
