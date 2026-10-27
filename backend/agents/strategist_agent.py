"""Agente 03 — Estratega / Orquestador (único agente con inferencia LLM).

Solo se invoca cuando el Quant (score ≥ umbral) y el Sentimiento habilitan
una ventana. Recibe un payload JSON ultracompacto y responde un TradeProposal
validado por Pydantic mediante Structured Outputs.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from backend.core.config import get_settings
from backend.models.schemas import QuantSignal, SentimentState, TradeProposal
from backend.services.llm_client import LLMError, build_client

log = logging.getLogger("strategist")

SYSTEM_PROMPT = (
    "Eres el estratega de un escuadrón de trading de futuros cripto. Recibes métricas ya "
    "calculadas: q=señal cuantitativa (dir, score 0-100, px, atr, rsi, vz=z-score volumen, "
    "st=estructura, bo=ruptura, obi=desequilibrio del libro, sl/tp sugeridos), "
    "s=sentimiento (sc -1..1, rg=régimen, fr=funding, oi=%cambio OI, news=titulares), p=cartera "
    "(eq, pos=posiciones abiertas, rk=% riesgo comprometido, dd=% pérdida hoy). "
    "Decide BUY (largo), SELL (corto) o HOLD. Opera solo a favor de q.dir; usa HOLD si el "
    "sentimiento o el régimen contradicen el setup. Usa el sl y el tp sugeridos (están calibrados con "
    "datos históricos); solo puedes acercar el tp si ves un obstáculo claro, nunca alejarlo ni mover el "
    "sl. Ante la duda, HOLD: no operar es una decisión válida. Para HOLD "
    "usa 0 en sl y tp. Un Guardián de Riesgo determinista validará tu propuesta. "
    "reasoning_1_line: una frase en español de máximo 140 caracteres."
)

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
        "symbol": {"type": "string"},
        "entry_type": {"type": "string", "enum": ["MARKET", "LIMIT"]},
        "suggested_stop_loss": {"type": "number"},
        "suggested_take_profit": {"type": "number"},
        "confidence": {"type": "integer"},
        "reasoning_1_line": {"type": "string"},
    },
    "required": ["action", "symbol", "entry_type", "suggested_stop_loss",
                 "suggested_take_profit", "confidence", "reasoning_1_line"],
    "additionalProperties": False,
}


def compact_payload(q: QuantSignal, s: SentimentState, portfolio: dict[str, float],
                    entry_ref: float | None = None) -> str:
    """JSON de ~150 tokens: nunca se envían velas crudas al LLM.

    entry_ref es el precio ejecutable ahora (ask para LONG, bid para SHORT): el mismo
    que usará el Guardián para verificar la propuesta.
    """
    sig = lambda x: float(f"{x:.6g}")  # noqa: E731
    px = entry_ref or q.price
    payload = {
        "q": {"sym": q.symbol, "dir": q.direction, "score": round(q.setup_score), "px": sig(px),
              "atr": sig(q.atr14), "rsi": round(q.rsi14, 1), "vz": round(q.volume_z, 2),
              "st": q.structure, "bo": q.breakout,
              "obi": None if q.order_book_imbalance is None else round(q.order_book_imbalance, 2),
              "sl": sig(q.suggested_stop_loss), "tp": sig(q.suggested_take_profit)},
        "s": {"sc": s.sentiment_score, "rg": s.regime_alert, "fr": round(s.funding_rate * 100, 4),
              "oi": s.open_interest_change_pct, "news": s.news_summary or None},
        "p": {k: round(v, 2) for k, v in portfolio.items()},
    }
    return json.dumps(payload, separators=(",", ":"))


def deterministic_proposal(q: QuantSignal, s: SentimentState) -> TradeProposal:
    """Respaldo sin LLM (sin LLM_API_KEY): sigue al Quant salvo contradicción de contexto."""
    d = 1 if q.direction == "LONG" else -1
    against_regime = (s.regime_alert == "EUPHORIA" and d > 0) or (s.regime_alert == "PANIC_EVENT" and d < 0)
    if d * s.sentiment_score < -0.3 or against_regime:
        return TradeProposal(action="HOLD", symbol=q.symbol, confidence=int(q.setup_score) // 2,
                             reasoning_1_line=f"Setup {q.direction} contradicho por contexto ({s.regime_alert}, {s.sentiment_score:+.2f})")
    return TradeProposal(
        action="BUY" if d > 0 else "SELL", symbol=q.symbol, entry_type="MARKET",
        suggested_stop_loss=q.suggested_stop_loss, suggested_take_profit=q.suggested_take_profit,
        confidence=int(q.setup_score),
        reasoning_1_line=f"[Determinista] {q.direction} score {q.setup_score:.0f}, {q.structure}, vz {q.volume_z:.1f}")


class StrategistAgent:
    agent_id = "03"
    name = "Estratega"

    def __init__(self) -> None:
        cfg = get_settings()
        self.client = build_client(cfg, cfg.strategist_model, cfg.strategist_fallback_models)
        self.tokens_used = 0
        self.last_model: str | None = None

    @property
    def uses_llm(self) -> bool:
        return self.client is not None

    @property
    def model_label(self) -> str:
        return self.client.models[0] if self.client else "determinista"

    async def propose(self, q: QuantSignal, s: SentimentState, portfolio: dict[str, float],
                      entry_ref: float | None = None) -> tuple[TradeProposal, int]:
        """Devuelve (propuesta, tokens consumidos en esta llamada)."""
        if self.client is None:
            return deterministic_proposal(q, s), 0
        try:
            result = await self.client.generate_json(SYSTEM_PROMPT, compact_payload(q, s, portfolio, entry_ref), PROPOSAL_SCHEMA)
        except LLMError as exc:
            log.warning("Estratega LLM no disponible (%s): se usa el respaldo determinista", exc)
            fallback = deterministic_proposal(q, s)
            fallback.reasoning_1_line = f"[LLM caído] {fallback.reasoning_1_line}"[:140]
            return fallback, 0
        self.tokens_used += result.tokens
        self.last_model = result.model
        data = result.data
        try:
            data["reasoning_1_line"] = str(data.get("reasoning_1_line", ""))[:140]
            data["symbol"] = q.symbol
            data["confidence"] = max(0, min(100, int(data.get("confidence", 0))))
            for key in ("suggested_stop_loss", "suggested_take_profit"):
                if not data.get(key):
                    data[key] = None
            return TradeProposal.model_validate(data), result.tokens
        except (ValidationError, TypeError, ValueError) as exc:
            log.error("Respuesta LLM inválida: %s", exc)
            return self._hold(q, f"Respuesta inválida de {result.model}: se fuerza HOLD"), result.tokens

    @staticmethod
    def _hold(q: QuantSignal, reason: str) -> TradeProposal:
        return TradeProposal(action="HOLD", symbol=q.symbol, confidence=0, reasoning_1_line=reason[:140])
