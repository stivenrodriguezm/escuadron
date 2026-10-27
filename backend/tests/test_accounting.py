"""Verificación matemática del motor de dinero y del Guardián de Riesgo."""
from __future__ import annotations

import random

import pytest

from backend.agents.executor_agent import breakeven_price, reached_breakeven_trigger
from backend.agents.risk_guardian import PortfolioView, RiskGuardian
from backend.core import params
from backend.core import accounting as acc
from backend.core.fills import simulate_market_fill
from backend.core.paper_broker import VirtualBroker
from backend.models.schemas import TradeProposal
from backend.services import capital_manager as cm
from backend.tests.conftest import FakeMarket


# ---------------- fórmulas puras ----------------
def test_position_size_formula():
    q = acc.position_size(10_000, 0.015, 100.0, 98.0)
    assert q == pytest.approx(150 / 2.0)


def test_weighted_fill_walks_levels():
    asks = [(100.0, 1.0), (101.0, 1.0), (102.0, 1.0)]
    assert acc.weighted_fill_price(asks, 2.0) == pytest.approx(100.5)
    assert acc.weighted_fill_price(asks, 0.5) == pytest.approx(100.0)
    assert acc.weighted_fill_price(asks, 4.0) > 101.0  # remanente con penalización


def test_net_pnl_and_compound_exact():
    q, e, x = 2.0, 100.0, 110.0
    fees = acc.total_fees(q, e, x, 0.0005, 0.0005, funding=0.3)
    assert fees == pytest.approx(2 * 100 * 0.0005 + 2 * 110 * 0.0005 + 0.3)
    pnl = acc.net_pnl("LONG", q, e, x, fees)
    assert pnl == pytest.approx(20 - fees)
    assert acc.compound(1_000, pnl) == pytest.approx(1_000 + 20 - fees)
    assert acc.net_pnl("SHORT", q, e, x, fees) == pytest.approx(-20 - fees)


def test_compound_interest_reinvests_and_shrinks_after_losses():
    equity, r = 10_000.0, 0.015
    q0 = acc.position_size(equity, r, 100, 98)
    for _ in range(3):  # racha ganadora: +2R netos por operación
        equity = acc.compound(equity, 2 * acc.risk_usd(equity, r))
    q_win = acc.position_size(equity, r, 100, 98)
    assert q_win > q0
    assert equity == pytest.approx(10_000 * 1.03 ** 3)
    for _ in range(5):  # racha perdedora: −1R por operación
        equity = acc.compound(equity, -acc.risk_usd(equity, r))
    assert acc.position_size(equity, r, 100, 98) < q_win
    assert equity == pytest.approx(10_000 * 1.03 ** 3 * 0.985 ** 5)


# ---------------- fricción nunca nula ----------------
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("is_entry", [True, False])
def test_fees_and_slippage_never_zero_or_negative(cfg, side, is_entry):
    md = FakeMarket(sigma=0.0)  # incluso con volatilidad cero
    for qty in (0.001, 0.3, 5.0, 50.0):
        fill = simulate_market_fill(md, cfg, "BTCUSDT", side, qty, is_entry)
        assert fill.fee > 0
        assert fill.slippage_cost > 0
        assert fill.s_latency > 0
        buying = (side == "LONG") == is_entry
        assert (fill.effective_price > fill.mid_price) if buying else (fill.effective_price < fill.mid_price)


# ---------------- Guardián de Riesgo ----------------
def _view(**kw) -> PortfolioView:
    base = dict(equity=10_000, daily_pnl=0.0, day_base_equity=10_000)
    base.update(kw)
    return PortfolioView(**base)


def test_guardian_blocks_all_orders_without_stop_loss(cfg):
    g = RiskGuardian(cfg)
    rnd = random.Random(7)
    for _ in range(500):
        action = rnd.choice(["BUY", "SELL"])
        px = rnd.uniform(10, 100_000)
        d = 1 if action == "BUY" else -1
        bad_sl = rnd.choice([None, 0.0, px + d * rnd.uniform(0.001, 0.05) * px])  # ausente o lado incorrecto
        p = TradeProposal(action=action, symbol="BTCUSDT", suggested_stop_loss=bad_sl,
                          suggested_take_profit=px * (1 + d * 0.05), confidence=99,
                          reasoning_1_line="test")
        assert g.evaluate(p, px, px * 0.01, _view()).verdict == "VETOED"


def test_guardian_blocks_when_daily_loss_limit_exceeded(cfg):
    g = RiskGuardian(cfg)
    p = TradeProposal(action="BUY", symbol="BTCUSDT", suggested_stop_loss=98.0,
                      suggested_take_profit=106.0, confidence=90, reasoning_1_line="ok")
    assert g.evaluate(p, 100.0, 1.5, _view()).verdict == "APPROVED"
    for loss in (300.0, 450.0, 2_000.0):  # ≥ 3 % del capital del día
        d = g.evaluate(p, 100.0, 1.5, _view(daily_pnl=-loss))
        assert d.verdict == "VETOED" and not d.checks["daily_loss"]


def test_guardian_rejects_poor_reward_risk_and_sizes_exactly(cfg):
    g = RiskGuardian(cfg)
    poor = TradeProposal(action="SELL", symbol="ETHUSDT", suggested_stop_loss=102.0,
                         suggested_take_profit=97.0, confidence=80, reasoning_1_line="x")
    assert g.evaluate(poor, 100.0, 1.5, _view()).verdict == "VETOED"
    good = TradeProposal(action="SELL", symbol="ETHUSDT", suggested_stop_loss=102.0,
                         suggested_take_profit=94.0, confidence=80, reasoning_1_line="x")
    d = g.evaluate(good, 100.0, 1.5, _view())
    assert d.verdict == "APPROVED"
    risk = 10_000 * cfg.max_risk_per_trade
    assert d.quantity == pytest.approx(risk / 2.0)  # R_usd / |entrada − SL|
    assert d.risk_usd == pytest.approx(risk)


# ---------------- ciclo completo paper con ledger ----------------
async def test_paper_round_trip_updates_compound_equity(cfg, db):
    md = FakeMarket(mid=100.0, sigma=0.0)
    md.set_mid(100.0, spread=0.02, depth=1_000)
    broker = VirtualBroker(md, cfg)
    res = await broker.place_order("BTCUSDT", "LONG", 50.0, stop_loss=97.0, take_profit=106.0)
    assert res.ok and res.fill is not None
    entry = res.fill
    md.set_mid(106.5, spread=0.02, depth=1_000)
    await broker.watch_tick()  # dispara el Take-Profit
    assert broker.get_positions() == []
    with cm.atomic() as s:
        state = cm.get_portfolio(s)
    exit_px = acc.effective_price(106.5 - 0.01, "LONG", False, cfg.min_latency_slippage)
    expected = acc.net_pnl("LONG", 50.0, entry.effective_price, exit_px,
                           entry.fee + acc.fee(50.0, exit_px, cfg.taker_fee))
    assert state.current_compound_equity == pytest.approx(10_000 + expected)
    assert state.total_fees_paid > 0 and state.total_slippage_cost > 0
    assert state.allocated_margin == pytest.approx(0.0)



# ---------------- break-even y estrategia ----------------
def test_breakeven_rule_disabled_with_zero_and_triggers_at_r():
    assert not reached_breakeven_trigger("LONG", 100.0, 98.0, 110.0, 0.0)
    assert reached_breakeven_trigger("LONG", 100.0, 98.0, 103.0, 1.5)
    assert not reached_breakeven_trigger("LONG", 100.0, 98.0, 102.9, 1.5)
    assert reached_breakeven_trigger("SHORT", 100.0, 102.0, 97.0, 1.5)
    assert breakeven_price("LONG", 100.0, 0.0005) > 100.0 > breakeven_price("SHORT", 100.0, 0.0005)


def test_default_strategy_is_calibrated_per_symbol(tmp_path, monkeypatch):
    monkeypatch.setattr(params, "PARAMS_FILE", tmp_path / "params.json")
    strategy = params.load_strategy()
    assert {s: st.interval for s, st in strategy.items()} == {"DOGEUSDT": "4h", "XRPUSDT": "4h", "SOLUSDT": "1h"}
    params.save_strategy({"BTCUSDT": params.SymbolStrategy(interval="1h", setup_score_threshold=70,
                                                           sl_atr_mult=2.0, tp_atr_mult=6.0)})
    assert list(params.load_strategy()) == ["BTCUSDT"]
