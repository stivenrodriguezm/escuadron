import { useState, type ReactNode } from "react";
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

function SectionTitle({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 md:px-5 md:py-3.5">
      <span className="text-[13px] font-medium">{title}</span>
      {right}
    </div>
  );
}

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
          <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:gap-5 md:px-0">
            {Object.entries(data.stream.markets).map(([sym, mk]) => (
              <div key={sym} className="shrink-0 rounded-md border border-line bg-panel px-3 py-1.5 md:border-0 md:bg-transparent md:p-0 md:text-right">
                <div className="label">{sym.replace("USDT", "")}</div>
                <div className="num text-[12.5px] text-ink-dim">{mk.price ? fmtPrice(mk.price) : "—"}</div>
              </div>
            ))}
          </div>
        }
      />
      <div className="space-y-4 px-4 py-4 md:space-y-5 md:px-8 md:py-6">
        <div className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
          <KpiCard
            className="col-span-2 xl:col-span-1"
            label="Balance estimado (compuesto)"
            value={fmtUsd(m.equity_with_unrealized)}
            delta={<span className={`num text-[12.5px] ${tone(m.total_return_pct)}`}>{fmtPct(m.total_return_pct)}</span>}
            footer="USDT · incluye PnL no realizado"
            action={
              <button className="btn shrink-0 px-2.5 py-1 text-[11.5px]" onClick={() => setShowCapital(true)}>
                <SlidersHorizontal size={12} /> Ajustar
              </button>
            }
          />
          <KpiCard
            label="Hoy (neto)"
            value={<span className={tone(m.daily_pnl)}>{fmtUsd(m.daily_pnl, true)}</span>}
            delta={<span className={`num text-[12px] ${tone(m.daily_return_pct)}`}>{fmtPct(m.daily_return_pct)}</span>}
            footer={<>Fricción hoy <span className="num text-ink-dim">−{fmtUsd(m.daily_friction)}</span> · total <span className="num">−{fmtUsd(friction)}</span></>}
          />
          <KpiCard
            label="Riesgo comprometido"
            value={`${m.risk_committed_pct.toFixed(2)}%`}
            delta={<span className="num text-[12px] text-ink-faint">/ {(limits.max_portfolio_risk * 100).toFixed(1)}%</span>}
            footer={<>DD máx <span className="num text-ink-dim">{m.max_drawdown_pct.toFixed(2)}%</span> · Win <span className="num text-ink-dim">{m.win_rate_pct.toFixed(0)}%</span></>}
          />
          <KpiCard
            className="col-span-2 xl:col-span-1"
            label="Capital base / en trabajo"
            value={fmtUsd(state.initial_capital)}
            footer={<>Margen desplegado <span className="num text-ink-dim">{fmtUsd(state.allocated_margin)}</span> · {data.positions.length} posiciones · Sharpe <span className="num text-ink-dim">{m.sharpe_ratio.toFixed(2)}</span></>}
          />
        </div>

        {/* Móvil: curva → agentes → decisiones. Escritorio: agentes a la izquierda, curva y decisiones a la derecha */}
        <div className="grid gap-4 md:gap-5 lg:grid-cols-[38fr_62fr]">
          <section className="panel min-w-0 lg:col-start-2 lg:row-start-1">
            <SectionTitle
              title="Evolución de cartera"
              right={<span className={`num text-[12px] ${tone(m.total_return_pct)}`}>{fmtPct(m.total_return_pct)}</span>}
            />
            <div className="px-1 py-3 md:px-3 md:py-4">
              <EquityChart points={points} baseline={initial} />
            </div>
          </section>

          <section className="panel self-start lg:col-start-1 lg:row-span-2 lg:row-start-1">
            <SectionTitle
              title="Módulos de agentes"
              right={<span className="text-[11.5px] text-ink-faint">{data.llm_enabled ? "LLM activo" : "LLM desactivado"}</span>}
            />
            <AgentList agents={data.agents} />
          </section>

          <section className="panel min-w-0 lg:col-start-2 lg:row-start-2">
            <SectionTitle title="Historial de decisiones" right={<span className="text-[11.5px] text-ink-faint">en vivo</span>} />
            <ConsensusTable logs={logs} />
          </section>
        </div>
      </div>
      {showCapital && <CapitalModal current={state.current_compound_equity} onClose={() => setShowCapital(false)} />}
    </>
  );
}

export function Loading() {
  return <ConnectScreen />;
}
