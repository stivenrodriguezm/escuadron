import { useEffect, useState } from "react";
import { PageHeader } from "../components/Layout";
import { PositionCard, TradeCard } from "../components/MobileCards";
import { fmtDateTime, fmtPrice, fmtUsd, tone } from "../components/format";
import { api } from "../hooks/api";
import type { TelemetryState } from "../hooks/useTelemetry";
import type { Trade } from "../types";
import { Loading } from "./DashboardView";

const TRADES_PAGE = 20;

function Empty({ text }: { text: string }) {
  return <div className="px-4 py-6 text-center text-[12.5px] text-ink-faint">{text}</div>;
}

export function LedgerView({ telemetry }: { telemetry: TelemetryState }) {
  const { data } = telemetry;
  const [trades, setTrades] = useState<Trade[]>([]);
  const [visible, setVisible] = useState(TRADES_PAGE);
  const tradesCount = data?.metrics.trades_count ?? 0;

  useEffect(() => {
    api.get<Trade[]>("/api/trades?limit=500").then(setTrades).catch(() => undefined);
  }, [tradesCount]);

  if (!data) return <Loading />;
  const s = data.state;
  const totals = trades.reduce(
    (acc, t) => ({ gross: acc.gross + t.gross_pnl, net: acc.net + t.net_pnl }),
    { gross: 0, net: 0 },
  );
  const summary: [string, string, string][] = [
    ["PnL neto cerrado", fmtUsd(totals.net, true), tone(totals.net)],
    ["PnL bruto cerrado", fmtUsd(totals.gross, true), tone(totals.gross)],
    ["Comisiones", fmtUsd(s.total_fees_paid), ""],
    ["Slippage + spread", fmtUsd(s.total_slippage_cost), ""],
    ["Funding neto", fmtUsd(s.total_funding_paid), ""],
  ];

  return (
    <>
      <PageHeader title="Posiciones y Ledger" subtitle="Registro contable inmutable con desglose exacto de fricción" />
      <div className="space-y-4 px-4 py-4 md:space-y-5 md:px-8 md:py-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {summary.map(([label, value, cls], i) => (
            <div key={label} className={`panel p-3.5 md:p-4 ${i === 0 ? "col-span-2 sm:col-span-1" : ""}`}>
              <div className="label">{label}</div>
              <div className={`num mt-1.5 text-[16px] ${cls}`}>{value}</div>
            </div>
          ))}
        </div>

        <section className="panel">
          <div className="border-b border-line px-4 py-3 text-[13px] font-medium md:px-5 md:py-3.5">
            Posiciones abiertas ({data.positions.length})
          </div>
          {data.positions.length === 0 ? (
            <Empty text="Sin posiciones abiertas." />
          ) : (
            <>
              <div className="divide-y divide-line md:hidden">
                {data.positions.map((p) => <PositionCard key={p.id} p={p} />)}
              </div>
              <div className="hidden overflow-x-auto md:block">
                <table className="data">
                  <thead>
                    <tr><th>Par</th><th>Lado</th><th>Cantidad</th><th>Entrada</th><th>Actual</th><th>Stop</th><th>Take-Profit</th><th>Comisión ent.</th><th>Funding</th><th>PnL no realizado</th><th>Apertura</th></tr>
                  </thead>
                  <tbody>
                    {data.positions.map((p) => (
                      <tr key={p.id}>
                        <td>{p.symbol}</td>
                        <td className={p.side === "LONG" ? "text-gain" : "text-loss"}>{p.side}</td>
                        <td className="num">{p.quantity}</td>
                        <td className="num">{fmtPrice(p.entry_price)}</td>
                        <td className="num">{fmtPrice(p.current_price)}</td>
                        <td className="num">{fmtPrice(p.stop_loss)}{p.breakeven_moved && <span className="ml-1 text-[10px] text-warn">BE</span>}</td>
                        <td className="num">{fmtPrice(p.take_profit)}</td>
                        <td className="num">{fmtUsd(p.entry_fee)}</td>
                        <td className="num">{fmtUsd(p.accumulated_funding)}</td>
                        <td className={`num ${tone(p.unrealized_pnl)}`}>{fmtUsd(p.unrealized_pnl, true)}</td>
                        <td className="num text-ink-faint">{fmtDateTime(p.opened_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        <section className="panel">
          <div className="border-b border-line px-4 py-3 text-[13px] font-medium md:px-5 md:py-3.5">
            Operaciones cerradas ({trades.length})
          </div>
          {trades.length === 0 ? (
            <Empty text="Aún no hay operaciones cerradas." />
          ) : (
            <>
              <div className="divide-y divide-line md:hidden">
                {trades.slice(0, visible).map((t) => <TradeCard key={t.id} t={t} />)}
                {visible < trades.length && (
                  <div className="p-3">
                    <button className="btn w-full justify-center" onClick={() => setVisible((v) => v + TRADES_PAGE)}>
                      Mostrar más ({trades.length - visible})
                    </button>
                  </div>
                )}
              </div>
              <div className="hidden max-h-[520px] overflow-auto md:block">
                <table className="data">
                  <thead>
                    <tr><th>Cierre</th><th>Par</th><th>Lado</th><th>Cant.</th><th>Entrada</th><th>Salida</th><th>PnL bruto</th><th>Com. ent.</th><th>Com. sal.</th><th>Slippage</th><th>Funding</th><th>PnL neto</th><th>Balance</th><th>Motivo</th></tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id}>
                        <td className="num text-ink-faint">{fmtDateTime(t.closed_at)}</td>
                        <td>{t.symbol}</td>
                        <td className={t.side === "LONG" ? "text-gain" : "text-loss"}>{t.side}</td>
                        <td className="num">{t.quantity}</td>
                        <td className="num">{fmtPrice(t.entry_price)}</td>
                        <td className="num">{fmtPrice(t.exit_price)}</td>
                        <td className={`num ${tone(t.gross_pnl)}`}>{fmtUsd(t.gross_pnl, true)}</td>
                        <td className="num">{fmtUsd(t.entry_fee)}</td>
                        <td className="num">{fmtUsd(t.exit_fee)}</td>
                        <td className="num">{fmtUsd(t.slippage_cost)}</td>
                        <td className="num">{fmtUsd(t.funding_paid)}</td>
                        <td className={`num ${tone(t.net_pnl)}`}>{fmtUsd(t.net_pnl, true)}</td>
                        <td className="num">{fmtUsd(t.equity_after)}</td>
                        <td className="text-[11.5px] text-ink-dim">{t.exit_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
