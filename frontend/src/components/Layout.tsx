import { useState, type ReactNode } from "react";
import {
  Bot, FlaskConical, LayoutDashboard, OctagonX, PanelLeftClose, PanelLeftOpen, Pause, Play, Settings2, Table2,
} from "lucide-react";
import type { ExecutionMode, ViewKey } from "../types";
import { MODE_LABEL } from "./format";

const NAV: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "agents", label: "Módulos de Agentes", icon: Bot },
  { key: "ledger", label: "Posiciones y Ledger", icon: Table2 },
  { key: "backtest", label: "Calibración (Backtest)", icon: FlaskConical },
  { key: "settings", label: "Configuración & API", icon: Settings2 },
];

const COLLAPSED_KEY = "escuadron.sidebarCollapsed";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveCollapsed(value: boolean): void {
  try {
    window.localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0");
  } catch {
    /* preferencia no persistente si el almacenamiento está bloqueado */
  }
}

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
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const live = socketOpen && streamConnected;
  const statusText = !socketOpen ? "Backend desconectado" : streamConnected ? "Binance Stream Activo" : "Reconectando stream…";
  const width = collapsed ? 64 : 240;

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      saveCollapsed(!c);
      return !c;
    });
  };

  const killSwitch = () => {
    if (window.confirm("¿Activar Kill-Switch? Se cerrarán todas las posiciones a mercado.")) onToggle("KILL_SWITCH");
  };

  return (
    <div className="flex h-full">
      <aside
        className="fixed inset-y-0 left-0 z-20 flex flex-col border-r border-line bg-[#0B0C12] transition-[width] duration-200"
        style={{ width }}
      >
        <div className={`flex items-center py-5 ${collapsed ? "flex-col gap-3 px-0" : "gap-2.5 px-5"}`}>
          <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-panel2">
            <div className="h-2.5 w-2.5 rotate-45 rounded-[2px] bg-gain" />
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold tracking-tight">Escuadrón</div>
              <div className="text-[11px] text-ink-faint">Trading multi-agente</div>
            </div>
          )}
          <button
            onClick={toggleCollapsed}
            className="rounded-md p-1.5 text-ink-faint transition-colors hover:bg-panel hover:text-ink"
            title={collapsed ? "Mostrar barra lateral" : "Ocultar barra lateral"}
            aria-label={collapsed ? "Mostrar barra lateral" : "Ocultar barra lateral"}
          >
            {collapsed ? <PanelLeftOpen size={16} strokeWidth={1.75} /> : <PanelLeftClose size={16} strokeWidth={1.75} />}
          </button>
        </div>

        <nav className={`mt-2 flex flex-col gap-0.5 ${collapsed ? "px-2" : "px-3"}`}>
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => onNavigate(key)}
              title={collapsed ? label : undefined}
              aria-label={label}
              className={`flex items-center rounded-md py-2 text-left text-[13px] transition-colors ${
                collapsed ? "justify-center px-0" : "gap-2.5 px-2.5"
              } ${view === key ? "bg-panel2 text-ink" : "text-ink-dim hover:bg-panel hover:text-ink"}`}
            >
              <Icon size={15} strokeWidth={1.75} className="shrink-0" />
              {!collapsed && label}
            </button>
          ))}
        </nav>

        <div className={`mt-auto border-t border-line ${collapsed ? "flex flex-col items-center gap-3 px-2 py-4" : "space-y-3 p-4"}`}>
          <div className="flex items-center gap-2 text-[12px]" title={collapsed ? statusText : undefined}>
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${live ? "bg-gain" : "bg-loss"}`} />
            {!collapsed && <span className="text-ink-dim">{statusText}</span>}
          </div>
          {!collapsed && (
            <div className="inline-flex rounded border border-line bg-panel px-2 py-1 text-[11px] text-ink-dim">
              {mode ? MODE_LABEL[mode] : "—"}
            </div>
          )}
          <div className={collapsed ? "flex flex-col gap-2" : "flex gap-2"}>
            <button
              className={`btn ${collapsed ? "justify-center px-2.5" : "flex-1 justify-center"}`}
              onClick={() => onToggle(running ? "PAUSE" : "START")}
              title={running ? "Pausar Algoritmo" : "Iniciar"}
            >
              {running ? <Pause size={13} /> : <Play size={13} />}
              {!collapsed && (running ? "Pausar Algoritmo" : "Iniciar")}
            </button>
            <button className="btn btn-danger px-2.5" title="Kill-Switch: cerrar todas las posiciones" onClick={killSwitch}>
              <OctagonX size={14} />
            </button>
          </div>
        </div>
      </aside>
      <main className="min-h-full flex-1 overflow-x-hidden transition-[margin] duration-200" style={{ marginLeft: width }}>
        {children}
      </main>
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
