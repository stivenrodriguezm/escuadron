"""Orquesta trabajos de calibración en segundo plano sobre el backtester headless."""
from __future__ import annotations

import asyncio
import itertools
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from backend.agents.indicators import IndicatorSeries
from backend.core.config import get_settings
from backend.core.headless_backtester import precompute_signals, run_backtest
from backend.models.schemas import BacktestRequest, BacktestResult
from backend.services.historical_loader import INTERVAL_MS, load_funding, load_klines

MAX_COMBINATIONS = 48


class BacktestJob(BaseModel):
    job_id: str
    status: Literal["RUNNING", "DONE", "ERROR"] = "RUNNING"
    request: BacktestRequest
    message: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    candles: int = 0
    results: list[BacktestResult] = Field(default_factory=list)


JOBS: dict[str, BacktestJob] = {}


def _grid(req: BacktestRequest, series: IndicatorSeries, funding: list[tuple[int, float]]) -> list[BacktestResult]:
    cfg = get_settings()
    combos = list(itertools.product(req.score_thresholds, req.sl_atr_mults, req.tp_atr_mults))
    signals = precompute_signals(series, req.symbol)
    results = []
    for threshold, sl, tp in combos[:MAX_COMBINATIONS]:
        r = run_backtest(series, funding, req.symbol, INTERVAL_MS[req.interval], cfg,
                         threshold, sl, tp, req.initial_capital, signals)
        r.interval = req.interval
        results.append(r)
    return sorted(results, key=lambda r: (r.sharpe_ratio, r.compound_return_pct), reverse=True)


async def _run(job: BacktestJob) -> None:
    req = job.request
    try:
        if req.interval not in INTERVAL_MS:
            raise ValueError(f"Intervalo no soportado: {req.interval}")
        df = await load_klines(req.symbol, req.interval, req.start, req.end)
        if df.height < 260:
            raise ValueError(f"Datos insuficientes ({df.height} velas); amplía el rango")
        funding = await load_funding(req.symbol, req.start, req.end)
        series = IndicatorSeries.build(df["open_time"].to_list(), df["open"].to_list(),
                                       df["high"].to_list(), df["low"].to_list(),
                                       df["close"].to_list(), df["volume"].to_list())
        job.candles = df.height
        job.results = await asyncio.to_thread(_grid, req, series, funding)
        job.status, job.message = "DONE", f"{len(job.results)} combinaciones evaluadas"
    except Exception as exc:  # noqa: BLE001
        job.status, job.message = "ERROR", str(exc)
    job.finished_at = datetime.now(timezone.utc)


def launch(req: BacktestRequest) -> BacktestJob:
    job = BacktestJob(job_id=uuid.uuid4().hex[:10], request=req)
    JOBS[job.job_id] = job
    asyncio.create_task(_run(job))
    return job
