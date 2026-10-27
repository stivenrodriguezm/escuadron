import type { ConsensusLog } from "../types";
import { AGENT_NAMES, fmtTime } from "./format";

const VERDICT_TONE: Record<string, string> = {
  APPROVED: "text-gain",
  EJECUTADA: "text-gain",
  BUY: "text-gain",
  SELL: "text-loss",
  VETOED: "text-loss",
  ERROR: "text-loss",
  KILL_SWITCH: "text-loss",
  PANIC_EVENT: "text-loss",
  EUPHORIA: "text-warn",
  SETUP: "text-accent",
};

export function ConsensusTable({ logs, maxHeight = 340 }: { logs: ConsensusLog[]; maxHeight?: number }) {
  const rows = [...logs].reverse();
  return (
    <div className="overflow-y-auto" style={{ maxHeight }}>
      <table className="data">
        <thead>
          <tr>
            <th className="w-[84px]">Hora</th>
            <th className="w-[190px]">Agente</th>
            <th className="w-[110px]">Estado</th>
            <th>Decisión</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="py-8 text-center text-ink-faint">Sin decisiones registradas todavía.</td>
            </tr>
          )}
          {rows.map((l) => (
            <tr key={l.id}>
              <td className="num text-ink-faint">{fmtTime(l.timestamp)}</td>
              <td>
                <span className="num mr-1.5 text-ink-faint">{l.agent_id}</span>
                {AGENT_NAMES[l.agent_id] ?? l.agent_id}
              </td>
              <td className={`num text-[11.5px] ${VERDICT_TONE[l.status] ?? "text-ink-dim"}`}>{l.status}</td>
              <td className="max-w-0 truncate" title={l.message}>
                {l.message}
                {l.token_cost > 0 && <span className="num ml-2 text-[11px] text-ink-faint">· {l.token_cost} tok</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
