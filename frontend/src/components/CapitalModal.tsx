import { useState } from "react";
import { X } from "lucide-react";
import { api } from "../hooks/api";
import { fmtUsd } from "./format";

interface CapitalModalProps {
  current: number;
  onClose: () => void;
}

export function CapitalModal({ current, onClose }: CapitalModalProps) {
  const [amount, setAmount] = useState(current.toFixed(2));
  const [mode, setMode] = useState<"RESCALE" | "RESET">("RESCALE");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Introduce un monto positivo");
      return;
    }
    if (mode === "RESET" && !window.confirm("Reiniciar cierra todas las posiciones y borra el historial. ¿Continuar?")) return;
    setBusy(true);
    try {
      await api.post("/api/capital", { amount: value, mode });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setBusy(false);
    }
  };

  return (
    // En móvil se muestra como hoja inferior (al alcance del pulgar); en escritorio, centrado
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-[2px] md:items-center" onClick={onClose}>
      <div
        className="panel pb-safe w-full rounded-b-none p-5 md:w-[420px] md:rounded-b-[10px] md:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-line md:hidden" />
        <div className="flex items-center justify-between">
          <h2 className="text-[15px] font-semibold">Ajustar capital virtual</h2>
          <button className="-m-2 p-2 text-ink-faint hover:text-ink" onClick={onClose} aria-label="Cerrar"><X size={18} /></button>
        </div>
        <p className="mt-1 text-[12.5px] text-ink-faint">Balance compuesto actual: <span className="num">{fmtUsd(current)}</span></p>

        <label className="label mt-5 block">Nuevo monto (USDT)</label>
        <input className="input num mt-1.5" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" />

        <div className="mt-4 grid grid-cols-2 gap-2">
          {(["RESCALE", "RESET"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-md border px-3 py-2.5 text-left text-[12px] ${mode === m ? "border-[#3A4258] bg-panel2" : "border-line"}`}
            >
              <div className="font-medium text-ink">{m === "RESCALE" ? "Reescalar" : "Reiniciar curva"}</div>
              <div className="mt-0.5 text-ink-faint">
                {m === "RESCALE" ? "Mantiene el rendimiento % y el historial" : "Cierra posiciones y empieza de cero"}
              </div>
            </button>
          ))}
        </div>
        {error && <p className="mt-3 text-[12px] text-loss">{error}</p>}
        <div className="mt-6 grid grid-cols-2 gap-2 pb-2 md:flex md:justify-end md:pb-0">
          <button className="btn justify-center" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary justify-center" disabled={busy} onClick={submit}>{busy ? "Aplicando…" : "Aplicar"}</button>
        </div>
      </div>
    </div>
  );
}
