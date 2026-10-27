"""Contratos Pydantic v2 que viajan entre agentes, broker y API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Side = Literal["LONG", "SHORT"]


class Candle(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True


class QuantSignal(BaseModel):
    symbol: str
    timestamp: int
    price: float
    direction: Side
    setup_score: float = Field(ge=0, le=100)
    ema20: float
    ema50: float
    ema200: float
    rsi14: float
    atr14: float
    atr_pct: float
    volume_z: float
    structure: Literal["BULLISH", "BEARISH", "RANGE"]
    breakout: bool
    order_book_imbalance: Optional[float] = None
    suggested_stop_loss: float
    suggested_take_profit: float
    components: dict[str, float] = Field(default_factory=dict)


class SentimentState(BaseModel):
    symbol: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    regime_alert: Literal["NORMAL", "EUPHORIA", "PANIC_EVENT"]
    summary: str
    funding_rate: float = 0.0
    open_interest_change_pct: float = 0.0
    long_short_ratio: Optional[float] = None
    news_score: Optional[float] = None
    headline_risk: Optional[Literal["NONE", "ELEVATED", "EXTREME"]] = None
    news_summary: Optional[str] = None
    computed_at: datetime


class TradeProposal(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    entry_type: Literal["MARKET", "LIMIT"] = "MARKET"
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    confidence: int = Field(ge=0, le=100)
    reasoning_1_line: str = Field(max_length=140)


class RiskDecision(BaseModel):
    verdict: Literal["APPROVED", "VETOED"]
    reason: str
    symbol: str
    side: Optional[Side] = None
    entry_type: Literal["MARKET", "LIMIT"] = "MARKET"
    reference_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: float = 0.0
    risk_usd: float = 0.0
    reward_risk: float = 0.0
    checks: dict[str, bool] = Field(default_factory=dict)


class Fill(BaseModel):
    symbol: str
    side: Side
    quantity: float
    weighted_price: float
    effective_price: float
    mid_price: float
    fee: float
    fee_rate: float
    slippage_cost: float
    s_latency: float


class OrderResult(BaseModel):
    ok: bool
    message: str
    order_id: Optional[str] = None
    position_id: Optional[int] = None
    fill: Optional[Fill] = None


class AgentStatus(BaseModel):
    id: str
    name: str
    status: str
    metric: str
    tokens_used: int = 0
    last_update: Optional[datetime] = None
    deterministic: bool = True
    model: Optional[str] = None


class CapitalUpdate(BaseModel):
    amount: float = Field(gt=0)
    mode: Literal["RESCALE", "RESET"] = "RESCALE"


class EngineToggle(BaseModel):
    action: Literal["START", "PAUSE", "KILL_SWITCH"]


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    start: str = Field(description="YYYY-MM-DD")
    end: str = Field(description="YYYY-MM-DD")
    initial_capital: float = Field(default=10_000.0, gt=0)
    score_thresholds: list[float] = Field(default_factory=lambda: [75.0])
    sl_atr_mults: list[float] = Field(default_factory=lambda: [1.5])
    tp_atr_mults: list[float] = Field(default_factory=lambda: [3.5])


class BacktestResult(BaseModel):
    symbol: str
    interval: str
    score_threshold: float
    sl_atr_mult: float
    tp_atr_mult: float
    initial_capital: float
    final_equity: float
    compound_return_pct: float
    trades: int
    win_rate_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    total_fees: float
    total_slippage: float
    total_funding: float
    equity_curve: list[tuple[int, float]] = Field(default_factory=list)


class StrategyUpdate(BaseModel):
    """Aplica parámetros calibrados a un par (desde la vista de Calibración)."""
    symbol: str
    interval: str
    setup_score_threshold: float = Field(ge=0, le=100)
    sl_atr_mult: float = Field(gt=0)
    tp_atr_mult: float = Field(gt=0)
