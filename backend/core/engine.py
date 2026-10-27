"""Orquestador del escuadrón: Quant → Sentimiento → Estratega → Guardián → Ejecutor."""
from __future__ import annotations

import asyncio
import logging

from sqlmodel import select

from backend.agents.executor_agent import ExecutorAgent
from backend.agents.quant_agent import QuantAgent
from backend.agents.risk_guardian import PortfolioView, RiskGuardian
from backend.agents.sentiment_agent import SentimentAgent
from backend.agents.strategist_agent import StrategistAgent
from backend.core.config import ExecutionMode, get_settings
from backend.core.database import atomic
from backend.core.paper_broker import VirtualBroker, run_watch_loop
from backend.core.params import SymbolStrategy, load_strategy, save_strategy
from backend.core.telemetry import Telemetry
from backend.models.ledger import Position
from backend.models.schemas import Candle, StrategyUpdate
from backend.services import capital_manager as cm
from backend.services.metrics import compute_metrics, position_risk_usd
from backend.services.market_stream import MarketStream

log = logging.getLogger("engine")


class TradingEngine:
    def __init__(self) -> None:
        self.cfg = cfg = get_settings()
        self.strategy = load_strategy()
        self.stream = MarketStream(self._stream_symbols(), self._intervals())
        self.telemetry = Telemetry()
        self.broker = self._make_broker()
        self.quants = {sym: self._make_quant(st) for sym, st in self.strategy.items()}
        self.sentiment = SentimentAgent(cfg.sentiment_cache_minutes)
        self.strategist = StrategistAgent()
        self.guardian = RiskGuardian(cfg)
        self.executor = ExecutorAgent(self.broker, cfg)
        self.running = False
        self._locks = {s: asyncio.Lock() for s in self.symbols}
        self._tasks: list[asyncio.Task] = []

    def _make_broker(self) -> VirtualBroker:
        if self.cfg.execution_mode == ExecutionMode.PAPER_LIVE:
            return VirtualBroker(self.stream, self.cfg, self._broker_event)
        from backend.core.exchange_broker import ExchangeBroker
        return ExchangeBroker(self.stream, self.cfg, self._broker_event)

    async def _broker_event(self, status: str, message: str) -> None:
        self.telemetry.set_status("05", "Activo", message)
        self.telemetry.log("05", status, message)

    # ---------------- ciclo de vida ----------------
    async def start(self) -> None:
        with atomic() as s:
            self.running = cm.get_portfolio(s).is_running
        self.telemetry.restore_token_totals()
        for agent in (self.sentiment, self.strategist):
            status = self.telemetry.agents[agent.agent_id]
            status.model, status.deterministic = agent.model_label, agent.client is None
        if not self.strategist.uses_llm:
            self.telemetry.set_status("03", "Determinista", "Sin clave LLM: reglas de respaldo")
        await self.stream.bootstrap()
        self.stream.on_candle_close(self.on_candle_close)
        self.stream.start()
        self._tasks = [asyncio.create_task(run_watch_loop(self.broker, self.cfg.watch_interval_ms)),
                       asyncio.create_task(self._snapshot_loop()),
                       asyncio.create_task(self._manage_loop()),
                       asyncio.create_task(self._sentiment_loop())]
        for symbol, st in self.strategy.items():  # primera lectura para la UI
            self._run_quant(symbol, self.stream.closed_candles(symbol, st.interval))
        self.telemetry.log("01", "SISTEMA", f"Motor iniciado en modo {self.cfg.execution_mode.value} "
                           f"({'operando' if self.running else 'pausado'})")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await self.stream.stop()

    async def toggle(self, action: str) -> str:
        if action == "START":
            self.running = True
            msg = "Algoritmo reanudado"
        elif action == "PAUSE":
            self.running = False
            msg = "Algoritmo pausado (las posiciones abiertas siguen vigiladas)"
        else:
            self.running = False
            closed = await self.broker.close_all("KILL_SWITCH")
            msg = f"KILL-SWITCH: {closed} posiciones cerradas a mercado"
        cm.set_running(self.running)
        self.telemetry.log("04", action, msg)
        return msg

    @property
    def symbols(self) -> list[str]:
        return list(self.strategy)

    def _stream_symbols(self) -> list[str]:
        """Pares de la estrategia + pares con posiciones abiertas (sus SL/TP deben seguir vigilados)."""
        with atomic() as s:
            open_syms = {p.symbol for p in s.exec(select(Position).where(Position.status == "OPEN")).all()}
        return self.symbols + sorted(open_syms - set(self.symbols))

    def _intervals(self) -> list[str]:
        return sorted({st.interval for st in self.strategy.values()})

    @staticmethod
    def _make_quant(st: SymbolStrategy) -> QuantAgent:
        return QuantAgent(st.sl_atr_mult, st.tp_atr_mult, st.setup_score_threshold)

    async def apply_strategy(self, update: StrategyUpdate) -> None:
        """Aplica parámetros calibrados a un par; si es un par/intervalo nuevo, reabre el stream."""
        st = SymbolStrategy(**update.model_dump(exclude={"symbol"}))
        self.strategy[update.symbol] = st
        self.quants[update.symbol] = self._make_quant(st)
        self._locks.setdefault(update.symbol, asyncio.Lock())
        save_strategy(self.strategy)
        if update.symbol not in self.stream.symbols or st.interval not in self.stream.intervals:
            await self.stream.reconfigure(self._stream_symbols(), self._intervals())
        self.telemetry.log("01", "CALIBRADO", f"{update.symbol} {st.interval} · umbral {st.setup_score_threshold:.0f} · "
                           f"SL {st.sl_atr_mult}×ATR · TP {st.tp_atr_mult}×ATR")

    # ---------------- pipeline por evento ----------------
    def _run_quant(self, symbol: str, candles: list[Candle]):
        book = self.stream.book(symbol)
        signal = self.quants[symbol].analyze(symbol, candles, book.imbalance() if book else None)
        if signal:
            self.telemetry.set_status("01", "Analizando", f"{symbol} score {signal.setup_score:.0f}/100 "
                                      f"· {signal.direction} · RSI {signal.rsi14:.0f}")
        return signal

    async def on_candle_close(self, symbol: str, interval: str, candles: list[Candle]) -> None:
        st = self.strategy.get(symbol)
        if st is None or interval != st.interval:
            return
        quant = self.quants[symbol]
        async with self._locks[symbol]:
            signal = self._run_quant(symbol, candles)
            if not quant.is_actionable(signal):
                score = f"{signal.setup_score:.0f}" if signal else "—"
                self.telemetry.log("01", "SIN SETUP", f"{symbol} · score {score} · Analizando estructura - "
                                   "Sin anomalías accionables")
                return
            self.telemetry.log("01", "SETUP", f"{symbol} {signal.direction} score {signal.setup_score:.0f} "
                               f"· {signal.structure} · vz {signal.volume_z:.1f}")
            if not self.running:
                self.telemetry.log("04", "PAUSADO", f"{symbol}: setup ignorado, algoritmo en pausa")
                return
            sentiment, s_tokens = await self.sentiment.analyze(symbol, with_news=True)
            self.telemetry.set_status("02", "Activo", f"{symbol} {sentiment.sentiment_score:+.2f} · {sentiment.regime_alert}", s_tokens)
            news = f" · Noticias {sentiment.news_score:+.2f}: {sentiment.news_summary}" if sentiment.news_summary else ""
            self.telemetry.log("02", sentiment.regime_alert, f"{symbol} · {sentiment.summary}{news}", s_tokens)

            view = self.portfolio_view()
            book = self.stream.book(symbol)
            long = signal.direction == "LONG"
            ref = (book.asks[0][0] if long else book.bids[0][0]) if book else signal.price
            self.telemetry.set_status("03", "Razonando", f"{symbol} ventana abierta")
            proposal, tokens = await self.strategist.propose(signal, sentiment, {
                "eq": view.equity, "pos": len(view.open_symbols),
                "rk": view.risk_committed_usd / view.equity * 100,
                "dd": min(view.daily_pnl, 0) / view.day_base_equity * 100}, entry_ref=ref)
            self.telemetry.set_status("03", "Activo", f"{proposal.action} {symbol} conf {proposal.confidence}", tokens)
            via = f" [{self.strategist.last_model}]" if tokens else ""
            self.telemetry.log("03", proposal.action, f"{symbol} · {proposal.reasoning_1_line}{via}", tokens)

            book = self.stream.book(symbol)  # libro fresco tras la latencia del LLM
            if book and proposal.action != "HOLD":
                ref = book.asks[0][0] if proposal.action == "BUY" else book.bids[0][0]
            decision = self.guardian.evaluate(proposal, ref, signal.atr14, view)
            if proposal.action != "HOLD":
                self.telemetry.set_status("04", "Vigilando", f"{decision.verdict}: {decision.reason}")
                self.telemetry.log("04", decision.verdict, f"{symbol} · {decision.reason}")
            if decision.verdict == "APPROVED":
                result = await self.executor.execute(decision)
                self.telemetry.set_status("05", "Activo", result.message)
                self.telemetry.log("05", "EJECUTADA" if result.ok else "ERROR", result.message)

    def portfolio_view(self) -> PortfolioView:
        with atomic() as s:
            state = cm.get_portfolio(s)
            m = compute_metrics(s, state)
            positions = s.exec(select(Position).where(Position.status == "OPEN")).all()
            return PortfolioView(
                equity=state.current_compound_equity, daily_pnl=m.daily_pnl,
                day_base_equity=max(state.current_compound_equity - (m.daily_pnl - m.unrealized_pnl), 1e-9),
                risk_committed_usd=sum(position_risk_usd(p) for p in positions),
                notional_open=sum(p.quantity * p.current_price for p in positions),
                open_symbols=[p.symbol for p in positions] + [o.symbol for o in self.broker.pending.values()])

    # ---------------- bucles de fondo ----------------
    async def _snapshot_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                cm.record_snapshot(sum(p.unrealized_pnl for p in self.broker.get_positions()))
            except Exception:  # noqa: BLE001
                log.exception("Snapshot de equity falló")

    async def _manage_loop(self) -> None:
        while True:
            await asyncio.sleep(2)
            try:
                positions = self.broker.get_positions()
                self.telemetry.set_status("05", "Vigilando" if positions else "En espera",
                                          f"{len(positions)} posiciones abiertas · {len(self.broker.pending)} LIMIT")
                for msg in await self.executor.manage_positions():
                    self.telemetry.log("05", "BREAK-EVEN", msg)
                view = self.portfolio_view()
                self.telemetry.set_status("04", "Vigilando", f"Riesgo {view.risk_committed_usd / view.equity * 100:.2f}% "
                                          f"/ Máx {self.cfg.max_portfolio_risk * 100:.1f}%")
            except Exception:  # noqa: BLE001
                log.exception("Gestión de posiciones falló")

    async def _sentiment_loop(self) -> None:
        while True:
            for symbol in self.symbols:
                st, _ = await self.sentiment.analyze(symbol)
                self.telemetry.set_status("02", "Vigilando", f"{symbol} {st.sentiment_score:+.2f} · {st.regime_alert}")
            await asyncio.sleep(self.cfg.sentiment_cache_minutes * 60)
