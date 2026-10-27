import { useState } from "react";
import { ConsensusTable } from "../components/ConsensusTable";
import { PageHeader } from "../components/Layout";
import { fmtPct, fmtPrice } from "../components/format";
import type { TelemetryState } from "../hooks/useTelemetry";
import { Loading } from "./DashboardView";

const DESCRIPTIONS: Record<string, string> = {
  "01": "Python determinista. EMA 20/50/200, RSI(14), ATR(14), Z-Score de volumen, estructura HH/LL y desequilibrio del libro. Emite setup_score 0–100.",
  "02": "Capa determinista: funding, Open Interest, ratio long/short y velocidad de precio. Capa LLM (solo en setups): puntúa titulares RSS reales de las últimas 24 h. Caché de 30 minutos.",
  "03": "Única inferencia LLM. Solo despierta con setup_score ≥ umbral; responde un TradeProposal JSON validado.",
  "04": "Código duro. R/B neta ≥ 1:2, pérdida diaria < 3%, riesgo de cartera ≤ 3%, coherencia del stop con ATR y tamaño Q compuesto (1% por operación).",
  "05": "Ejecuta en el VirtualBroker con fricción real. El stop a break-even es configurable (BREAKEVEN_R); está desactivado porque la calibración mostró que corta las tendencias.",
};

export function AgentsView({ telemetry }: { telemetry: TelemetryState }) {
  const { data, logs } = telemetry;
  const [selected, setSelected] = useState("01");
  if (!data) return <Loading />;
  const agentLogs = logs.filter((l) => l.agent_id === selected);
  const totalTokens = data.agents.reduce((s, a) => s + a.tokens_used, 0);
  const current = data.agents.find((a) => a.id === selected);

  return (
    <>
      <PageHeader
        title="Módulos de Agentes"
        subtitle={`Activación por eventos · ${totalTokens.toLocaleString("en-US")} tokens consumidos`}
      />
      <div className="space-y-4 px-4 py-4 md:space-y-5 md:px-8 md:py-6">
        {/* Móvil: carrusel horizontal de agentes; escritorio: 5 columnas */}
        <div className="no-scrollbar -mx-4 flex snap-x snap-mandatory scroll-px-4 gap-2.5 overflow-x-auto px-4 md:mx-0 md:grid md:grid-cols-5 md:gap-3 md:overflow-visible md:px-0">
          {data.agents.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelected(a.id)}
              className={`panel w-[150px] shrink-0 snap-start p-3.5 text-left transition-colors md:w-auto md:p-4 ${
                selected === a.id ? "border-[#3A4258] bg-panel2" : "hover:border-[#2A3042]"
              }`}
            >
              <div className="num text-[11px] text-ink-faint">{a.id}</div>
              <div className="mt-1 text-[13px] font-medium leading-tight">{a.name}</div>
              <div className="mt-2.5 text-[11.5px] text-ink-dim">● {a.status}</div>
              <div className="num mt-1 truncate text-[11px] text-ink-faint">
                {a.deterministic ? "0 tokens · Python" : `${a.model ?? "LLM"} · ${a.tokens_used.toLocaleString("en-US")}`}
              </div>
            </button>
          ))}
        </div>

        <div className="grid gap-4 md:gap-5 lg:grid-cols-3">
          <section className="panel space-y-4 p-4 md:p-5">
            <div>
              <div className="label">Función</div>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-dim">{DESCRIPTIONS[selected]}</p>
            </div>
            <div>
              <div className="label">Lectura actual</div>
              <p className="num mt-1.5 break-words text-[12.5px] text-ink">{current?.metric}</p>
            </div>
            <div>
              <div className="label">Estrategia calibrada por par</div>
              <div className="mt-1.5 overflow-x-auto">
                <table className="data">
                  <thead><tr><th>Par</th><th>Velas</th><th>Umbral</th><th>SL</th><th>TP</th></tr></thead>
                  <tbody>
                    {Object.entries(data.strategy).map(([sym, st]) => (
                      <tr key={sym}>
                        <td>{sym.replace("USDT", "")}</td>
                        <td className="num">{st.interval}</td>
                        <td className="num">{st.setup_score_threshold}</td>
                        <td className="num">{st.sl_atr_mult}×</td>
                        <td className="num">{st.tp_atr_mult}×</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <div className="label">Microestructura en vivo</div>
              <div className="mt-1.5 overflow-x-auto">
                <table className="data">
                  <thead><tr><th>Par</th><th>Precio</th><th>Funding</th><th>Spread</th><th>OBI</th></tr></thead>
                  <tbody>
                    {Object.entries(data.stream.markets).map(([sym, mk]) => (
                      <tr key={sym}>
                        <td>{sym.replace("USDT", "")}</td>
                        <td className="num">{mk.price ? fmtPrice(mk.price) : "—"}</td>
                        <td className="num">{fmtPct(mk.funding_rate * 100, true, 4)}</td>
                        <td className="num">{mk.spread_pct !== null ? `${mk.spread_pct.toFixed(3)}%` : "—"}</td>
                        <td className="num">{mk.imbalance !== null ? mk.imbalance.toFixed(2) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
          <section className="panel min-w-0 lg:col-span-2">
            <div className="border-b border-line px-4 py-3 text-[13px] font-medium md:px-5 md:py-3.5">
              Telemetría · {current?.name}
            </div>
            <ConsensusTable logs={agentLogs} maxHeight={520} />
          </section>
        </div>
      </div>
    </>
  );
}
