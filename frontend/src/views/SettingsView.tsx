import { useEffect, useState } from "react";
import { ConnectScreen } from "../components/ConnectScreen";
import { PageHeader } from "../components/Layout";
import { MODE_LABEL } from "../components/format";
import { api } from "../hooks/api";
import type { ExecutionMode, SettingsView as Settings } from "../types";

const MODES: { key: ExecutionMode; detail: string }[] = [
  { key: "PAPER_LIVE", detail: "Dinero falso sobre el libro de órdenes real de Binance. Sin claves necesarias." },
  { key: "TESTNET", detail: "Órdenes reales en Binance Testnet / Demo. Requiere claves de testnet y ccxt." },
  { key: "LIVE", detail: "Órdenes reales con dinero real. Requiere claves de producción. Usar con extrema precaución." },
];

export function SettingsView() {
  const [cfg, setCfg] = useState<Settings | null>(null);
  useEffect(() => {
    api.get<Settings>("/api/settings").then(setCfg).catch(() => undefined);
  }, []);
  if (!cfg) return <ConnectScreen />;

  const rows: [string, string][] = [
    ["Pares operados", Object.entries(cfg.strategy).map(([sym, st]) => `${sym} (${st.interval})`).join(" · ")],
    ["Proveedor LLM", cfg.llm_enabled ? cfg.llm_provider : `${cfg.llm_provider} · sin clave (modo determinista)`],
    ...Object.entries(cfg.agent_models).map(([id, model]): [string, string] => [`Modelo agente ${id}`, model]),
    ["Respaldo del Estratega", cfg.strategist_fallbacks.join(" → ") || "—"],
    ["Claves Binance", cfg.binance_keys ? "Configuradas" : "No configuradas (no necesarias en modo simulado)"],
    ["Comisión taker / maker", `${(cfg.taker_fee * 100).toFixed(3)}% / ${(cfg.maker_fee * 100).toFixed(3)}%`],
    ["Latencia simulada", `${cfg.latency_ms} ms`],
    ["Riesgo por operación", `${(cfg.max_risk_per_trade * 100).toFixed(2)}% del balance compuesto`],
    ["Riesgo máximo de cartera", `${(cfg.max_portfolio_risk * 100).toFixed(2)}%`],
    ["Pérdida diaria máxima", `${(cfg.max_daily_drawdown * 100).toFixed(2)}%`],
    ["Apalancamiento máximo", `${cfg.max_leverage}×`],
    ["R/B neta mínima", `1:${cfg.min_reward_risk}`],
    ["Stop a break-even", cfg.breakeven_r > 0 ? `al alcanzar +${cfg.breakeven_r}R` : "Desactivado"],
  ];

  return (
    <>
      <PageHeader title="Configuración & API" subtitle="Los valores se definen en el archivo .env del servidor y se aplican al reiniciar" />
      <div className="space-y-5 px-8 py-6">
        <section className="grid grid-cols-3 gap-3">
          {MODES.map((m) => (
            <div key={m.key} className={`panel p-4 ${cfg.execution_mode === m.key ? "border-[#3A4258]" : "opacity-70"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-medium">{MODE_LABEL[m.key]}</span>
                {cfg.execution_mode === m.key && <span className="rounded bg-gain/10 px-1.5 py-0.5 text-[10.5px] text-gain">ACTIVO</span>}
              </div>
              <p className="mt-2 text-[12px] leading-relaxed text-ink-faint">{m.detail}</p>
              <code className="num mt-3 block text-[11px] text-ink-dim">EXECUTION_MODE={m.key}</code>
            </div>
          ))}
        </section>
        <section className="panel">
          <table className="data">
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k}><td className="w-[280px] text-ink-faint">{k}</td><td className="num">{v}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}
