"""Indicadores técnicos causales (el valor en t solo usa datos ≤ t).

Al ser causales, el backtester puede calcular las series completas una vez
sin introducir sesgo de futuro, y el agente en vivo usa exactamente las mismas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

NAN = float("nan")
Structure = Literal["BULLISH", "BEARISH", "RANGE"]
PIVOT_K = 3


def ema(values: Sequence[float], n: int) -> list[float]:
    out = [NAN] * len(values)
    if len(values) < n:
        return out
    k = 2 / (n + 1)
    prev = sum(values[:n]) / n
    out[n - 1] = prev
    for i in range(n, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes: Sequence[float], n: int = 14) -> list[float]:
    out = [NAN] * len(closes)
    if len(closes) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / n, losses / n
    out[n] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (n - 1) + max(d, 0)) / n
        avg_l = (avg_l * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], n: int = 14) -> list[float]:
    out = [NAN] * len(closes)
    if len(closes) <= n:
        return out
    trs = [highs[0] - lows[0]] + [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, len(closes))]
    prev = sum(trs[1:n + 1]) / n
    out[n] = prev
    for i in range(n + 1, len(closes)):
        prev = (prev * (n - 1) + trs[i]) / n
        out[i] = prev
    return out


def volume_zscore(volumes: Sequence[float], n: int = 20) -> list[float]:
    """Z-score del volumen actual frente a las n velas previas (excluye la actual)."""
    out = [NAN] * len(volumes)
    for i in range(n, len(volumes)):
        window = volumes[i - n:i]
        mean = sum(window) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in window) / (n - 1))
        out[i] = 0.0 if std == 0 else (volumes[i] - mean) / std
    return out


def pivots(highs: Sequence[float], lows: Sequence[float], k: int = 3) -> tuple[list[bool], list[bool]]:
    """Marca pivotes de máximo/mínimo. Un pivote en j solo se conoce en j + k."""
    n = len(highs)
    ph, pl = [False] * n, [False] * n
    for j in range(k, n - k):
        ph[j] = highs[j] == max(highs[j - k:j + k + 1])
        pl[j] = lows[j] == min(lows[j - k:j + k + 1])
    return ph, pl


@dataclass
class IndicatorSeries:
    """Series completas precalculadas (causales) para una lista de velas."""
    open_times: list[int]
    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]
    volumes: list[float]
    ema20: list[float]
    ema50: list[float]
    ema200: list[float]
    rsi14: list[float]
    atr14: list[float]
    vol_z: list[float]
    pivot_high: list[bool]
    pivot_low: list[bool]

    @classmethod
    def build(cls, open_times: list[int], opens: list[float], highs: list[float],
              lows: list[float], closes: list[float], volumes: list[float]) -> "IndicatorSeries":
        ph, pl = pivots(highs, lows, PIVOT_K)
        return cls(open_times, opens, highs, lows, closes, volumes,
                   ema(closes, 20), ema(closes, 50), ema(closes, 200), rsi(closes, 14),
                   atr(highs, lows, closes, 14), volume_zscore(volumes, 20), ph, pl)

    def ready(self, i: int) -> bool:
        return i >= 200 and not any(math.isnan(x) for x in (
            self.ema200[i], self.rsi14[i], self.atr14[i], self.vol_z[i]))

    def structure(self, i: int, lookback: int = 80) -> Structure:
        """HH/HL o LH/LL con pivotes confirmados hasta el índice i (sin futuro)."""
        hs: list[float] = []
        ls: list[float] = []
        for j in range(i - PIVOT_K, max(PIVOT_K, i - lookback) - 1, -1):
            if self.pivot_high[j] and len(hs) < 2:
                hs.append(self.highs[j])
            if self.pivot_low[j] and len(ls) < 2:
                ls.append(self.lows[j])
            if len(hs) == 2 and len(ls) == 2:
                break
        if len(hs) < 2 or len(ls) < 2:
            return "RANGE"
        if hs[0] > hs[1] and ls[0] > ls[1]:
            return "BULLISH"
        if hs[0] < hs[1] and ls[0] < ls[1]:
            return "BEARISH"
        return "RANGE"

    def breakout(self, i: int, direction: int, n: int = 20) -> tuple[bool, float]:
        """¿El cierre rompe el extremo de las n velas previas? Devuelve (ruptura, distancia)."""
        if direction > 0:
            level = max(self.highs[i - n:i])
            return self.closes[i] > level, self.closes[i] - level
        level = min(self.lows[i - n:i])
        return self.closes[i] < level, level - self.closes[i]
