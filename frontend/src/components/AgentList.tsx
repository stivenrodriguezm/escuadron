import type { AgentStatus } from "../types";

const STATUS_TONE: Record<string, string> = {
  Activo: "bg-gain",
  Analizando: "bg-accent",
  Vigilando: "bg-warn",
  Razonando: "bg-accent",
  Determinista: "bg-ink-faint",
};

export function AgentList({ agents, compact = false }: { agents: AgentStatus[]; compact?: boolean }) {
  return (
    <div className="flex flex-col divide-y divide-line">
      {agents.map((a) => (
        <div key={a.id} className={compact ? "px-4 py-3" : "px-5 py-4"}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="num text-[11px] text-ink-faint">{a.id}.</span>
              <span className="text-[13px] font-medium">{a.name}</span>
            </div>
            <span className="flex items-center gap-1.5 text-[11.5px] text-ink-dim">
              <span className={`h-1.5 w-1.5 rounded-full ${STATUS_TONE[a.status] ?? "bg-ink-faint"}`} />
              {a.status}
            </span>
          </div>
          <div className="mt-1.5 flex items-center justify-between gap-3 pl-6">
            <span className="truncate text-[12px] text-ink-faint" title={a.metric}>
              {a.metric}
            </span>
            <span className="num shrink-0 text-[11px] text-ink-faint">
              {a.deterministic ? "Python · 0 tokens" : `${a.model ?? "LLM"} · ${a.tokens_used.toLocaleString("en-US")} tok`}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
