"""Estrategia calibrada por par (intervalo + parámetros), persistida en data/params.json.

Los valores por defecto salen de la calibración con validación fuera de muestra
(ver Sección 8.3 del plan maestro). Calibrar desde la UI sobrescribe el par aplicado.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from backend.core.config import DATA_DIR

PARAMS_FILE = DATA_DIR / "params.json"


class SymbolStrategy(BaseModel):
    interval: str
    setup_score_threshold: float
    sl_atr_mult: float
    tp_atr_mult: float


DEFAULT_STRATEGY: dict[str, SymbolStrategy] = {
    "DOGEUSDT": SymbolStrategy(interval="4h", setup_score_threshold=85, sl_atr_mult=1.5, tp_atr_mult=8.0),
    "XRPUSDT": SymbolStrategy(interval="4h", setup_score_threshold=60, sl_atr_mult=1.0, tp_atr_mult=5.0),
    "SOLUSDT": SymbolStrategy(interval="1h", setup_score_threshold=75, sl_atr_mult=3.0, tp_atr_mult=8.0),
}


def load_strategy() -> dict[str, SymbolStrategy]:
    if PARAMS_FILE.exists():
        try:
            raw = json.loads(PARAMS_FILE.read_text())
            strategy = {s: SymbolStrategy.model_validate(v) for s, v in raw.get("symbols", {}).items()}
            if strategy:
                return strategy
        except (ValueError, OSError, ValidationError, AttributeError):
            pass
    return dict(DEFAULT_STRATEGY)


def save_strategy(strategy: dict[str, SymbolStrategy]) -> None:
    PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_FILE.write_text(json.dumps({"symbols": {s: v.model_dump() for s, v in strategy.items()}}, indent=2))
