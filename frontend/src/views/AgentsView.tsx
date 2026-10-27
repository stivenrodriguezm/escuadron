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

  return (
    <>
      <PageHeader
        title="Módulos de Agentes"
        subtitle={`Activación por eventos · ${totalTokens.toLocaleString("en-US")} tokens consumidos en total`}
      />
      <div className="space-y-5 px-8 py-6">
        <div className="grid grid-cols-5 gap-3">
          {data.agents.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelected(a.id)}
              className={`panel p-4 text-left transition-colors ${selected === a.id ? "border-[#3A4258]" : "hover:border-[#2A3042]"}`}
            >
              <div className="num text-[11px] text-ink-faint">{a.id}</div>
              <div className="mt-1 text-[13px] font-medium">{a.name}</div>
              <div className="mt-3 text-[11.5px] text-ink-dim">● {a.status}</div>
              <div className="num mt-1 text-[11px] text-ink-faint">{a.deterministic ? "0 tokens · determinista" : `${a.model ?? "LLM"} · ${a.tokens_used.toLocaleString("en-US")} tokens`}</div>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-5">
          <section className="panel col-span-1 space-y-4 p-5">
            <div>
              <div className="label">Función</div>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-dim">{DESCRIPTIONS[selected]}</p>
            </div>
            <div>
              <div className="label">Lectura actual</div>
              <p className="num mt-1.5 text-[12.5px] text-ink">{data.agents.find((a) => a.id === selected)?.metric}</p>
            </div>
            <div>
              <div className="label">Estrategia calibrada por par</div>
              <table className="data mt-1.5">
                <thead><tr><th>Par</th><th>Velas</th><th>Umbral</th><th>SL</th><th>TP</th></tr></thead>
                <tbody>
                  {Object.entries(data.strategy).map(([sym, st]) => (
                    <tr key={sym}>
                      <td>{sym}</td>
                      <td className="num">{st.interval}</td>
                      <td className="num">{st.setup_score_threshold}</td>
                      <td className="num">{st.sl_atr_mult}×ATR</td>
                      <td className="num">{st.tp_atr_mult}×ATR</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <div className="label">Microestructura en vivo</div>
              <table className="data mt-1.5">
                <thead><tr><th>Par</th><th>Precio</th><th>Funding</th><th>Spread</th><th>OBI</th></tr></thead>
                <tbody>
                  {Object.entries(data.stream.markets).map(([sym, mk]) => (
                    <tr key={sym}>
                      <td>{sym}</td>
                      <td className="num">{mk.price ? fmtPrice(mk.price) : "—"}</td>
                      <td className="num">{fmtPct(mk.funding_rate * 100, true, 4)}</td>
                      <td className="num">{mk.spread_pct !== null ? `${mk.spread_pct.toFixed(4)}%` : "—"}</td>
                      <td className="num">{mk.imbalance !== null ? mk.imbalance.toFixed(2) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel col-span-2">
            <div className="border-b border-line px-5 py-3.5 text-[13px] font-medium">
              Telemetría · {data.agents.find((a) => a.id === selected)?.name}
            </div>
            <ConsensusTable logs={agentLogs} maxHeight={520} />
          </section>
        </div>
      </div>
    </>
  );
}
