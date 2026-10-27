import type { ReactNode } from "react";
import { Bot, FlaskConical, LayoutDashboard, OctagonX, Pause, Play, Settings2, Table2 } from "lucide-react";
import type { ExecutionMode, ViewKey } from "../types";
import { MODE_LABEL } from "./format";

const NAV: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "agents", label: "Módulos de Agentes", icon: Bot },
  { key: "ledger", label: "Posiciones y Ledger", icon: Table2 },
  { key: "backtest", label: "Calibración (Backtest)", icon: FlaskConical },
  { key: "settings", label: "Configuración & API", icon: Settings2 },
];

interface LayoutProps {
  view: ViewKey;
  onNavigate: (v: ViewKey) => void;
  streamConnected: boolean;
  socketOpen: boolean;
  mode: ExecutionMode | undefined;
  running: boolean;
  onToggle: (action: "START" | "PAUSE" | "KILL_SWITCH") => void;
  children: ReactNode;
}

export function Layout(props: LayoutProps) {
  const { view, onNavigate, streamConnected, socketOpen, mode, running, onToggle, children } = props;
  const live = socketOpen && streamConnected;
  return (
    <div className="flex h-full">
      <aside className="fixed inset-y-0 left-0 flex w-[240px] flex-col border-r border-line bg-[#0B0C12]">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="grid h-7 w-7 place-items-center rounded-md border border-line bg-panel2">
            <div className="h-2.5 w-2.5 rotate-45 rounded-[2px] bg-gain" />
          </div>
          <div>
            <div className="text-[13.5px] font-semibold tracking-tight">Escuadrón</div>
            <div className="text-[11px] text-ink-faint">Trading multi-agente</div>
          </div>
        </div>

        <nav className="mt-2 flex flex-col gap-0.5 px-3">
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => onNavigate(key)}
              className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors ${
                view === key ? "bg-panel2 text-ink" : "text-ink-dim hover:bg-panel hover:text-ink"
              }`}
            >
              <Icon size={15} strokeWidth={1.75} />
              {label}
            </button>
          ))}
        </nav>

        <div className="mt-auto space-y-3 border-t border-line p-4">
          <div className="flex items-center gap-2 text-[12px]">
            <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-gain" : "bg-loss"}`} />
            <span className="text-ink-dim">
              {!socketOpen ? "Backend desconectado" : streamConnected ? "Binance Stream Activo" : "Reconectando stream…"}
            </span>
          </div>
          <div className="inline-flex rounded border border-line bg-panel px-2 py-1 text-[11px] text-ink-dim">
            {mode ? MODE_LABEL[mode] : "—"}
          </div>
          <div className="flex gap-2">
            <button className="btn flex-1 justify-center" onClick={() => onToggle(running ? "PAUSE" : "START")}>
              {running ? <Pause size={13} /> : <Play size={13} />}
              {running ? "Pausar Algoritmo" : "Iniciar"}
            </button>
            <button
              className="btn btn-danger px-2.5"
              title="Kill-Switch: cerrar todas las posiciones"
              onClick={() => {
                if (window.confirm("¿Activar Kill-Switch? Se cerrarán todas las posiciones a mercado.")) onToggle("KILL_SWITCH");
              }}
            >
              <OctagonX size={14} />
            </button>
          </div>
        </div>
      </aside>
      <main className="ml-[240px] min-h-full flex-1 overflow-x-hidden">{children}</main>
    </div>
  );
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <header className="flex items-end justify-between gap-4 border-b border-line px-8 py-5">
      <div>
        <h1 className="text-[17px] font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-[12.5px] text-ink-faint">{subtitle}</p>}
      </div>
      {right}
    </header>
  );
}
