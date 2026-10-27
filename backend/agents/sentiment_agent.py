"""Agente 02 — Sentimiento y Contexto.

Capa determinista (0 tokens): funding rate, cambio de Open Interest, ratio
long/short y velocidad del precio (datos públicos reales de Binance).
Capa LLM (solo cuando hay setup accionable): un modelo ligero puntúa los
titulares RSS reales de las últimas 24 h. Ambas capas se cachean 30 min.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from backend.core.config import get_settings
from backend.models.schemas import SentimentState
from backend.services.binance_rest import (fetch_long_short_ratio,
                                           fetch_open_interest_hist,
                                           fetch_premium_index)
from backend.services.llm_client import LLMError, build_client
from backend.services.news_feed import recent_headlines

log = logging.getLogger("sentiment")

FUNDING_EXTREME = 0.0005   # 0.05 % cada 8 h
OI_SPIKE_PCT = 5.0         # % en 2.5 h
PRICE_SHOCK_PCT = 3.0      # % en 2.5 h
NEWS_WEIGHT = 0.4          # peso de los titulares en el score combinado

NEWS_PROMPT = (
    "Eres analista de sentimiento cripto. Recibes un activo y titulares reales de las últimas 24 h. "
    "Evalúa su impacto probable en el precio de ese activo en las próximas horas. news_score: -1 muy "
    "bajista, 0 neutral o irrelevante, 1 muy alcista. headline_risk: EXTREME ante hackeos grandes, "
    "quiebras, prohibiciones o shocks macro; ELEVATED ante riesgo relevante; si no, NONE. "
    "summary: una frase en español de máximo 120 caracteres con lo más relevante."
)
NEWS_SCHEMA = {
    "type": "object",
    "properties": {"news_score": {"type": "number"},
                   "headline_risk": {"type": "string", "enum": ["NONE", "ELEVATED", "EXTREME"]},
                   "summary": {"type": "string"}},
    "required": ["news_score", "headline_risk", "summary"],
    "additionalProperties": False,
}


def evaluate(symbol: str, funding: float, oi_change_pct: float, price_change_pct: float,
             ls_ratio: float | None) -> SentimentState:
    """Regla pura: convierte métricas de contexto en un estado de sentimiento."""
    score = 0.0
    # Momentum de precio confirmado por OI = convicción direccional.
    score += max(-0.4, min(0.4, price_change_pct / 5))
    if oi_change_pct > 0:
        score += 0.2 if price_change_pct > 0 else -0.2
    # Funding extremo = posicionamiento saturado (lectura contraria).
    score -= max(-0.3, min(0.3, funding / FUNDING_EXTREME * 0.15))
    if ls_ratio is not None:
        score -= max(-0.1, min(0.1, (ls_ratio - 1.0) * 0.1))
    score = max(-1.0, min(1.0, score))

    regime = "NORMAL"
    if (price_change_pct <= -PRICE_SHOCK_PCT and abs(oi_change_pct) >= OI_SPIKE_PCT) or funding <= -FUNDING_EXTREME:
        regime = "PANIC_EVENT"
    elif funding >= FUNDING_EXTREME and oi_change_pct >= OI_SPIKE_PCT:
        regime = "EUPHORIA"

    summary = (f"Funding {funding * 100:+.4f}% · OI {oi_change_pct:+.2f}% · "
               f"Precio {price_change_pct:+.2f}% · L/S {ls_ratio or 0:.2f}")
    return SentimentState(symbol=symbol, sentiment_score=round(score, 3), regime_alert=regime,
                          summary=summary[:140], funding_rate=funding,
                          open_interest_change_pct=round(oi_change_pct, 3),
                          long_short_ratio=ls_ratio, computed_at=datetime.now(timezone.utc))


def blend_news(state: SentimentState, news_score: float, risk: str, summary: str) -> SentimentState:
    """Combina la capa determinista con la lectura de titulares."""
    news_score = max(-1.0, min(1.0, news_score))
    score = (1 - NEWS_WEIGHT) * state.sentiment_score + NEWS_WEIGHT * news_score
    regime = state.regime_alert
    if risk == "EXTREME" and news_score < 0:
        regime = "PANIC_EVENT"
    return state.model_copy(update={"sentiment_score": round(max(-1.0, min(1.0, score)), 3),
                                    "regime_alert": regime, "news_score": news_score,
                                    "headline_risk": risk, "news_summary": summary[:140]})


class SentimentAgent:
    agent_id = "02"
    name = "Analista de Sentimiento"

    def __init__(self, cache_minutes: int = 30) -> None:
        cfg = get_settings()
        self.ttl = timedelta(minutes=cache_minutes)
        self._cache: dict[str, SentimentState] = {}
        self._news: dict[str, tuple[datetime, float, str, str]] = {}
        self.client = build_client(cfg, cfg.sentiment_model, cfg.sentiment_fallback_models)
        self.tokens_used = 0

    @property
    def model_label(self) -> str:
        return self.client.models[0] if self.client else "determinista"

    def cached(self, symbol: str) -> SentimentState | None:
        return self._cache.get(symbol)

    async def analyze(self, symbol: str, with_news: bool = False) -> tuple[SentimentState, int]:
        """Devuelve (estado, tokens gastados). with_news activa la capa LLM (solo en setups)."""
        state = await self._metrics(symbol)
        if not with_news or self.client is None:
            return state, 0
        tokens = 0
        hit = self._news.get(symbol)
        if hit is None or datetime.now(timezone.utc) - hit[0] >= self.ttl:
            try:
                tokens = await self._score_news(symbol)
            except LLMError as exc:
                log.warning("Titulares %s sin LLM (%s)", symbol, exc)
        news = self._news.get(symbol)
        return (blend_news(state, *news[1:]) if news else state), tokens

    async def _score_news(self, symbol: str) -> int:
        headlines = await recent_headlines()
        if not headlines:
            return 0
        asset = symbol.removesuffix("USDT")
        user = f"Activo: {asset}\nTitulares:\n" + "\n".join(f"- {h}" for h in headlines)
        result = await self.client.generate_json(NEWS_PROMPT, user, NEWS_SCHEMA, max_tokens=1024)
        d = result.data
        risk = str(d.get("headline_risk", "NONE"))
        self._news[symbol] = (datetime.now(timezone.utc), float(d.get("news_score", 0.0)),
                              risk if risk in ("NONE", "ELEVATED", "EXTREME") else "NONE",
                              str(d.get("summary", "")))
        self.tokens_used += result.tokens
        return result.tokens

    async def _metrics(self, symbol: str) -> SentimentState:
        hit = self._cache.get(symbol)
        if hit and datetime.now(timezone.utc) - hit.computed_at < self.ttl:
            return hit
        try:
            premium = await fetch_premium_index(symbol)
            oi = await fetch_open_interest_hist(symbol, "5m", 30)
            ls = await fetch_long_short_ratio(symbol)
            funding = float(premium["lastFundingRate"])
            oi_vals = [float(x["sumOpenInterest"]) for x in oi]
            oi_val_usd = [float(x["sumOpenInterestValue"]) for x in oi]
            oi_change = (oi_vals[-1] / oi_vals[0] - 1) * 100 if len(oi_vals) > 1 else 0.0
            # precio implícito = valor OI / OI (evita otra llamada)
            px = [v / q for v, q in zip(oi_val_usd, oi_vals) if q]
            price_change = (px[-1] / px[0] - 1) * 100 if len(px) > 1 else 0.0
            state = evaluate(symbol, funding, oi_change, price_change, ls)
        except Exception as exc:  # noqa: BLE001
            log.warning("Sentimiento %s sin datos (%s)", symbol, exc)
            if hit:
                return hit
            state = SentimentState(symbol=symbol, sentiment_score=0.0, regime_alert="NORMAL",
                                   summary="Datos de contexto no disponibles",
                                   computed_at=datetime.now(timezone.utc))
        self._cache[symbol] = state
        return state
