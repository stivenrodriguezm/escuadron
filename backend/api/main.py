"""Servidor FastAPI: REST + WebSocket de telemetría + frontend compilado."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select

from backend.api.serializers import iso, log_row, portfolio_payload, telemetry_payload
from backend.core.config import ROOT_DIR, get_settings
from backend.core.database import atomic, get_engine
from backend.core.engine import TradingEngine
from backend.models.ledger import EquitySnapshot, TradeHistory, utcnow
from backend.models.schemas import BacktestRequest, CapitalUpdate, EngineToggle, StrategyUpdate
from backend.services import calibration
from backend.services import capital_manager as cm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
engine: TradingEngine | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global engine
    get_engine()
    with atomic() as s:
        cm.get_portfolio(s)
    engine = TradingEngine()
    await engine.start()
    yield
    await engine.stop()


app = FastAPI(title="Escuadrón Multi-Agente de Trading", lifespan=lifespan)
# allow_private_network: Chrome lo exige cuando una web pública (GitHub Pages) llama a localhost
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["*"],
                   allow_headers=["*"], allow_private_network=True)


def eng() -> TradingEngine:
    if engine is None:
        raise HTTPException(503, "Motor no inicializado")
    return engine


@app.get("/api/portfolio")
def get_portfolio():
    return portfolio_payload(eng())


@app.post("/api/capital")
async def update_capital(body: CapitalUpdate):
    e = eng()
    if body.mode == "RESET":
        await e.broker.close_all("RESET")
    try:
        state = cm.set_virtual_capital(body.amount, body.mode)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    e.telemetry.log("04", "CAPITAL", f"Capital {'reiniciado' if body.mode == 'RESET' else 'reescalado'} "
                    f"a ${state.current_compound_equity:,.2f}")
    return portfolio_payload(e)


@app.post("/api/engine/toggle")
async def toggle_engine(body: EngineToggle):
    return {"message": await eng().toggle(body.action), "running": eng().running}


@app.post("/api/backtest/run")
async def run_backtest(body: BacktestRequest):
    return calibration.launch(body).model_dump(mode="json")


@app.get("/api/backtest")
def list_backtests():
    jobs = sorted(calibration.JOBS.values(), key=lambda j: j.started_at, reverse=True)
    return [j.model_dump(mode="json", exclude={"results"}) | {"best": j.results[0].model_dump() if j.results else None}
            for j in jobs]


@app.get("/api/backtest/{job_id}")
def get_backtest(job_id: str):
    job = calibration.JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Trabajo no encontrado")
    return job.model_dump(mode="json")


@app.post("/api/backtest/apply")
async def apply_strategy(body: StrategyUpdate):
    await eng().apply_strategy(body)
    return body


@app.get("/api/trades")
def get_trades(limit: int = 200):
    with atomic() as s:
        rows = s.exec(select(TradeHistory).order_by(TradeHistory.id.desc()).limit(limit)).all()
    return [r.model_dump(mode="json") | {"opened_at": iso(r.opened_at), "closed_at": iso(r.closed_at)} for r in rows]


@app.get("/api/equity")
def get_equity(hours: int = 24 * 30):
    since = utcnow() - timedelta(hours=hours)
    with atomic() as s:
        rows = s.exec(select(EquitySnapshot).where(EquitySnapshot.timestamp >= since)
                      .order_by(EquitySnapshot.timestamp)).all()
        initial = cm.get_portfolio(s).initial_capital
    stride = max(1, len(rows) // 1000)
    return {"initial_capital": initial,
            "points": [{"t": iso(r.timestamp), "equity": round(r.equity, 2)} for r in rows[::stride]]}


@app.get("/api/consensus")
def get_consensus(limit: int = 100):
    return [log_row(r) for r in eng().telemetry.recent(limit)]


@app.get("/api/settings")
def get_settings_view():
    cfg = eng().cfg
    return {"execution_mode": cfg.execution_mode.value, "symbols": eng().symbols,
            "llm_provider": cfg.llm_provider, "llm_enabled": eng().strategist.uses_llm,
            "agent_models": {"01": "determinista", "02": eng().sentiment.model_label,
                             "03": eng().strategist.model_label, "04": "determinista", "05": "determinista"},
            "strategist_fallbacks": eng().strategist.client.models[1:] if eng().strategist.client else [],
            "binance_keys": bool(cfg.binance_api_key and cfg.binance_api_secret),
            "taker_fee": cfg.taker_fee, "maker_fee": cfg.maker_fee, "latency_ms": cfg.latency_ms,
            "max_risk_per_trade": cfg.max_risk_per_trade, "max_daily_drawdown": cfg.max_daily_drawdown,
            "max_portfolio_risk": cfg.max_portfolio_risk, "max_leverage": cfg.max_leverage,
            "min_reward_risk": cfg.min_reward_risk, "breakeven_r": cfg.breakeven_r,
            "strategy": {sym: st.model_dump() for sym, st in eng().strategy.items()}}


@app.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket):
    await ws.accept()
    e = eng()
    recent = e.telemetry.recent(50)
    last_id = recent[-1].id if recent else 0
    try:
        await ws.send_json(telemetry_payload(e, recent))
        while True:
            await asyncio.sleep(1)
            new = e.telemetry.logs_after(last_id)
            if new:
                last_id = new[-1].id
            await ws.send_json(telemetry_payload(e, new))
    except (WebSocketDisconnect, RuntimeError):
        return


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = (FRONTEND_DIST / path).resolve()
        inside = target.is_relative_to(FRONTEND_DIST.resolve())  # bloquea path traversal
        return FileResponse(target if path and inside and target.is_file() else FRONTEND_DIST / "index.html")
