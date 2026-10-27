import { OctagonX, Pause, Play } from "lucide-react";
import type { ViewKey } from "../types";
import type { NavItem } from "./Layout";

interface MobileTopBarProps {
  live: boolean;
  socketOpen: boolean;
  running: boolean;
  onToggle: (action: "START" | "PAUSE" | "KILL_SWITCH") => void;
  onKill: () => void;
}

/** Barra superior fija en móvil: marca, estado de conexión y controles del algoritmo. */
export function MobileTopBar({ live, socketOpen, running, onToggle, onKill }: MobileTopBarProps) {
  return (
    <header className="pt-safe sticky top-0 z-30 border-b border-line bg-[#0B0C12]/95 backdrop-blur md:hidden">
      <div className="flex h-14 items-center gap-3 px-4">
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-line bg-panel2">
          <div className="h-2.5 w-2.5 rotate-45 rounded-[2px] bg-gain" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[14px] font-semibold leading-tight tracking-tight">Escuadrón</div>
          <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
            <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-gain" : "bg-loss"}`} />
            {!socketOpen ? "Sin conexión" : live ? "En vivo" : "Reconectando…"}
            <span className="text-ink-faint">·</span>
            <span className={running ? "text-gain" : "text-warn"}>{running ? "Operando" : "En pausa"}</span>
          </div>
        </div>
        <button
          className="grid h-10 w-10 place-items-center rounded-lg border border-line bg-panel2 text-ink active:bg-panel"
          onClick={() => onToggle(running ? "PAUSE" : "START")}
          aria-label={running ? "Pausar algoritmo" : "Iniciar algoritmo"}
        >
          {running ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          className="grid h-10 w-10 place-items-center rounded-lg border border-[#3A1E22] bg-[#1A1013] text-[#FCA5A5] active:bg-[#24141A]"
          onClick={onKill}
          aria-label="Kill-Switch: cerrar todas las posiciones"
        >
          <OctagonX size={17} />
        </button>
      </div>
    </header>
  );
}

/** Navegación inferior tipo app, al alcance del pulgar. */
export function MobileTabBar({ items, view, onNavigate }: { items: NavItem[]; view: ViewKey; onNavigate: (v: ViewKey) => void }) {
  return (
    <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-[#0B0C12]/95 backdrop-blur md:hidden">
      <div className="grid h-16 grid-cols-5">
        {items.map(({ key, short, icon: Icon }) => {
          const active = view === key;
          return (
            <button
              key={key}
              onClick={() => {
                onNavigate(key);
                window.scrollTo({ top: 0 });
              }}
              className={`flex flex-col items-center justify-center gap-1 text-[10.5px] font-medium transition-colors ${
                active ? "text-ink" : "text-ink-faint active:text-ink-dim"
              }`}
              aria-current={active ? "page" : undefined}
            >
              <span className={`grid h-7 w-12 place-items-center rounded-full ${active ? "bg-panel2" : ""}`}>
                <Icon size={18} strokeWidth={active ? 2 : 1.75} />
              </span>
              {short}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
