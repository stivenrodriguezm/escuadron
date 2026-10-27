import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { AgentList } from "../components/AgentList";
import { CapitalModal } from "../components/CapitalModal";
import { ConnectScreen } from "../components/ConnectScreen";
import { ConsensusTable } from "../components/ConsensusTable";
import { EquityChart } from "../components/EquityChart";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/Layout";
import { fmtPct, fmtPrice, fmtUsd, tone } from "../components/format";
import { useEquityCurve } from "../hooks/useEquityCurve";
import type { TelemetryState } from "../hooks/useTelemetry";

export function DashboardView({ telemetry }: { telemetry: TelemetryState }) {
  const { data, logs } = telemetry;
  const [showCapital, setShowCapital] = useState(false);
  const { points, initial } = useEquityCurve(data?.metrics.equity_with_unrealized);

  if (!data) return <Loading />;
  const { metrics: m, state, limits } = data;
  const friction = state.total_fees_paid + state.total_slippage_cost + state.total_funding_paid;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Operación en vivo sobre datos reales de Binance Futures"
        right={
          <div className="flex gap-5">
            {Object.entries(data.stream.markets).map(([sym, mk]) => (
              <div key={sym} className="text-right">
                <div className="label">{sym.replace("USDT", "")}</div>
                <div className="num text-[12.5px] text-ink-dim">{mk.price ? fmtPrice(mk.price) : "—"}</div>
              </div>
            ))}
          </div>
        }
      />
      <div className="space-y-5 px-8 py-6">
        <div className="grid grid-cols-4 gap-4">
          <KpiCard
            label="Balance estimado (compuesto)"
            value={`${fmtUsd(m.equity_with_unrealized)}`}
            delta={<span className={`num text-[12.5px] ${tone(m.total_return_pct)}`}>{fmtPct(m.total_return_pct)}</span>}
            footer="USDT · incluye PnL no realizado"
            action={
              <button className="btn px-2 py-1 text-[11.5px]" onClick={() => setShowCapital(true)}>
                <SlidersHorizontal size={12} /> Ajustar Capital
              </button>
            }
          />
          <KpiCard
            label="Capital base / en trabajo"
            value={fmtUsd(state.initial_capital)}
            footer={<>Margen desplegado: <span className="num text-ink-dim">{fmtUsd(state.allocated_margin)}</span> · {data.positions.length} pos.</>}
          />
          <KpiCard
            label="Rendimiento neto y fricción"
            value={<span className={tone(m.daily_pnl)}>{fmtUsd(m.daily_pnl, true)}</span>}
            delta={<span className={`num text-[12.5px] ${tone(m.daily_return_pct)}`}>{fmtPct(m.daily_return_pct)} hoy</span>}
            footer={<>Comisiones y Slippage restados: <span className="num text-ink-dim">−{fmtUsd(m.daily_friction)}</span> hoy · <span className="num">−{fmtUsd(friction)}</span> total</>}
          />
          <KpiCard
            label="Exposición de riesgo"
            value={`${m.risk_committed_pct.toFixed(2)}%`}
            delta={<span className="num text-[12.5px] text-ink-faint">/ Máx {(limits.max_portfolio_risk * 100).toFixed(1)}%</span>}
            footer={<>Drawdown máx: <span className="num text-ink-dim">{m.max_drawdown_pct.toFixed(2)}%</span> · Sharpe <span className="num text-ink-dim">{m.sharpe_ratio.toFixed(2)}</span> · Win <span className="num text-ink-dim">{m.win_rate_pct.toFixed(0)}%</span></>}
          />
        </div>

        <div className="grid gap-5" style={{ gridTemplateColumns: "38fr 62fr" }}>
          <section className="panel self-start">
            <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
              <span className="text-[13px] font-medium">Módulos de Agentes</span>
              <span className="text-[11.5px] text-ink-faint">{data.llm_enabled ? "LLM activo" : "LLM desactivado"}</span>
            </div>
            <AgentList agents={data.agents} />
          </section>

          <div className="flex min-w-0 flex-col gap-5">
            <section className="panel">
              <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
                <span className="text-[13px] font-medium">Evolución de Cartera · Rendimiento Compuesto</span>
                <span className={`num text-[12px] ${tone(m.total_return_pct)}`}>{fmtPct(m.total_return_pct)}</span>
              </div>
              <div className="px-3 py-4">
                <EquityChart points={points} baseline={initial} />
              </div>
            </section>
            <section className="panel">
              <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">Historial de Decisiones · Consenso en Vivo</div>
              <ConsensusTable logs={logs} />
            </section>
          </div>
        </div>
      </div>
      {showCapital && <CapitalModal current={state.current_compound_equity} onClose={() => setShowCapital(false)} />}
    </>
  );
}

export function Loading() {
  return <ConnectScreen />;
}
