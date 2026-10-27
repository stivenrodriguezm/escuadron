const usd = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function fmtUsd(v: number, signed = false): string {
  const s = usd.format(Math.abs(v));
  if (signed) return `${v >= 0 ? "+" : "−"}$${s}`;
  return `${v < 0 ? "−" : ""}$${s}`;
}

export function fmtPct(v: number, signed = true, digits = 2): string {
  const s = Math.abs(v).toFixed(digits);
  return signed ? `${v >= 0 ? "+" : "−"}${s}%` : `${v < 0 ? "−" : ""}${s}%`;
}

export function fmtPrice(v: number): string {
  const digits = v >= 1000 ? 2 : v >= 10 ? 3 : 4;
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", { hour12: false });
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-ES", { hour12: false, dateStyle: "short", timeStyle: "medium" });
}

export function tone(v: number): string {
  if (v > 0) return "text-gain";
  if (v < 0) return "text-loss";
  return "text-ink-dim";
}

export const AGENT_NAMES: Record<string, string> = {
  "01": "Analista Cuantitativo",
  "02": "Analista de Sentimiento",
  "03": "Estratega",
  "04": "Guardián de Riesgo",
  "05": "Ejecutor de Órdenes",
};

export const MODE_LABEL: Record<string, string> = {
  PAPER_LIVE: "Modo Simulado · Dinero Falso",
  TESTNET: "Binance Testnet",
  LIVE: "Dinero Real",
};
