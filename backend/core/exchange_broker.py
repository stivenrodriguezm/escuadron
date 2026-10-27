"""Broker real (Binance Testnet / Demo o Real) vía ccxt con la misma interfaz.

Hereda del VirtualBroker: el ledger, la vigilancia de SL/TP cada 500 ms y la
contabilidad compuesta son idénticos; solo cambia el llenado, que pasa a ser
una orden de mercado real. Requiere `pip install ccxt` y claves de API.
ADVERTENCIA: SL/TP se vigilan desde este proceso (no hay órdenes stop en el
exchange); si el servidor se detiene, las posiciones quedan sin protección.
"""
from __future__ import annotations

from backend.core.config import ExecutionMode, Settings
from backend.core.fills import MarketDataProvider
from backend.core.paper_broker import EventCallback, VirtualBroker
from backend.models.schemas import Fill, Side


def ccxt_symbol(symbol: str) -> str:
    return f"{symbol[:-4]}/USDT:USDT" if symbol.endswith("USDT") else symbol


class ExchangeBroker(VirtualBroker):
    def __init__(self, md: MarketDataProvider, cfg: Settings, on_event: EventCallback | None = None) -> None:
        super().__init__(md, cfg, on_event)
        if not cfg.binance_api_key or not cfg.binance_api_secret:
            raise RuntimeError("BINANCE_API_KEY y BINANCE_API_SECRET son obligatorias en modo TESTNET/LIVE")
        import ccxt.async_support as ccxt  # import diferido: dependencia opcional

        self.exchange = ccxt.binanceusdm({"apiKey": cfg.binance_api_key,
                                          "secret": cfg.binance_api_secret,
                                          "enableRateLimit": True})
        if cfg.execution_mode == ExecutionMode.TESTNET:
            if hasattr(self.exchange, "enable_demo_trading"):
                self.exchange.enable_demo_trading(True)
            else:
                self.exchange.set_sandbox_mode(True)

    async def _market_fill(self, symbol: str, side: Side, quantity: float, is_entry: bool) -> Fill:
        book = self.md.book(symbol)
        mid = book.mid if book else self.md.marks[symbol].mark_price
        buying = (side == "LONG") == is_entry
        params = {} if is_entry else {"reduceOnly": True}
        order = await self.exchange.create_order(ccxt_symbol(symbol), "market",
                                                 "buy" if buying else "sell", quantity, None, params)
        avg = float(order.get("average") or order.get("price") or mid)
        filled = float(order.get("filled") or quantity)
        fee_info = order.get("fee") or {}
        fee = float(fee_info.get("cost") or filled * avg * self.cfg.taker_fee)
        return Fill(symbol=symbol, side=side, quantity=filled, weighted_price=avg, effective_price=avg,
                    mid_price=mid, fee=fee, fee_rate=self.cfg.taker_fee,
                    slippage_cost=abs(avg - mid) * filled, s_latency=0.0)

    async def close(self) -> None:
        await self.exchange.close()
