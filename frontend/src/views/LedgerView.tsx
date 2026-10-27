import { useEffect, useState } from "react";
import { PageHeader } from "../components/Layout";
import { fmtDateTime, fmtPrice, fmtUsd, tone } from "../components/format";
import { api } from "../hooks/api";
import type { TelemetryState } from "../hooks/useTelemetry";
import type { Trade } from "../types";
import { Loading } from "./DashboardView";

export function LedgerView({ telemetry }: { telemetry: TelemetryState }) {
  const { data } = telemetry;
  const [trades, setTrades] = useState<Trade[]>([]);
  const tradesCount = data?.metrics.trades_count ?? 0;

  useEffect(() => {
    api.get<Trade[]>("/api/trades?limit=500").then(setTrades).catch(() => undefined);
  }, [tradesCount]);

  if (!data) return <Loading />;
  const s = data.state;
  const totals = trades.reduce(
    (acc, t) => ({ gross: acc.gross + t.gross_pnl, fees: acc.fees + t.entry_fee + t.exit_fee, net: acc.net + t.net_pnl }),
    { gross: 0, fees: 0, net: 0 },
  );

  return (
    <>
      <PageHeader title="Posiciones y Ledger" subtitle="Registro contable inmutable con desglose exacto de fricción" />
      <div className="space-y-5 px-8 py-6">
        <div className="grid grid-cols-5 gap-3">
          {[
            ["Comisiones pagadas", fmtUsd(s.total_fees_paid)],
            ["Slippage + spread", fmtUsd(s.total_slippage_cost)],
            ["Funding neto", fmtUsd(s.total_funding_paid)],
            ["PnL bruto cerrado", fmtUsd(totals.gross, true)],
            ["PnL neto cerrado", fmtUsd(totals.net, true)],
          ].map(([label, value]) => (
            <div key={label} className="panel p-4">
              <div className="label">{label}</div>
              <div className="num mt-1.5 text-[16px]">{value}</div>
            </div>
          ))}
        </div>

        <section className="panel">
          <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">Posiciones abiertas ({data.positions.length})</div>
          <div className="overflow-x-auto">
            <table className="data">
              <thead>
                <tr><th>Par</th><th>Lado</th><th>Cantidad</th><th>Entrada</th><th>Actual</th><th>Stop</th><th>Take-Profit</th><th>Comisión ent.</th><th>Funding</th><th>PnL no realizado</th><th>Apertura</th></tr>
              </thead>
              <tbody>
                {data.positions.length === 0 && <tr><td colSpan={11} className="py-6 text-center text-ink-faint">Sin posiciones abiertas.</td></tr>}
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
        </section>

        <section className="panel">
          <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">Operaciones cerradas ({trades.length})</div>
          <div className="max-h-[520px] overflow-auto">
            <table className="data">
              <thead>
                <tr><th>Cierre</th><th>Par</th><th>Lado</th><th>Cant.</th><th>Entrada</th><th>Salida</th><th>PnL bruto</th><th>Com. ent.</th><th>Com. sal.</th><th>Slippage</th><th>Funding</th><th>PnL neto</th><th>Balance</th><th>Motivo</th></tr>
              </thead>
              <tbody>
                {trades.length === 0 && <tr><td colSpan={14} className="py-6 text-center text-ink-faint">Aún no hay operaciones cerradas.</td></tr>}
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
        </section>
      </div>
    </>
  );
}
