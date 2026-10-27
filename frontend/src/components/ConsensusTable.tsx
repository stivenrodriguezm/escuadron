import { useState } from "react";
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
const PAGE = 25;

export function ConsensusTable({ logs, maxHeight = 340 }: { logs: ConsensusLog[]; maxHeight?: number }) {
  const rows = [...logs].reverse();
  const [visible, setVisible] = useState(PAGE);

  if (rows.length === 0) {
    return <div className="px-4 py-8 text-center text-[12.5px] text-ink-faint">Sin decisiones registradas todavía.</div>;
  }

  return (
    <>
      {/* Móvil: lista con el mensaje completo y paginación, sin scroll anidado */}
      <ul className="divide-y divide-line md:hidden">
        {rows.slice(0, visible).map((l) => (
          <li key={l.id} className="px-4 py-3">
            <div className="flex items-center gap-2 text-[11.5px]">
              <span className="num shrink-0 text-ink-faint">{fmtTime(l.timestamp)}</span>
              <span className="min-w-0 truncate text-ink-dim">
                <span className="num text-ink-faint">{l.agent_id}</span> {AGENT_NAMES[l.agent_id] ?? l.agent_id}
              </span>
              <span className={`num ml-auto shrink-0 text-[11px] ${VERDICT_TONE[l.status] ?? "text-ink-dim"}`}>{l.status}</span>
            </div>
            <p className="mt-1 break-words text-[12.5px] leading-snug text-[#C9CDD6]">
              {l.message}
              {l.token_cost > 0 && <span className="num ml-1.5 text-[11px] text-ink-faint">· {l.token_cost} tok</span>}
            </p>
          </li>
        ))}
        {visible < rows.length && (
          <li className="p-3">
            <button className="btn w-full justify-center" onClick={() => setVisible((v) => v + PAGE)}>
              Mostrar más ({rows.length - visible})
            </button>
          </li>
        )}
      </ul>

      {/* Escritorio: tabla */}
      <div className="hidden overflow-y-auto md:block" style={{ maxHeight }}>
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
    </>
  );
}
