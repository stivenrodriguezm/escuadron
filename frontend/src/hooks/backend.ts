/**
 * Ubicación del backend.
 * - Servida por el propio backend (./start.sh) o por Vite: rutas relativas.
 * - Publicada en GitHub Pages: el motor corre en la máquina del usuario, por defecto
 *   http://localhost:8000; se puede cambiar desde la pantalla de conexión.
 */
const STORAGE_KEY = "escuadron.backendUrl";
export const DEFAULT_REMOTE_BACKEND = "http://localhost:8000";

export const isStaticHost = (): boolean => window.location.hostname.endsWith("github.io");

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Base HTTP sin barra final ("" = mismo origen). */
export function backendBase(): string {
  if (!isStaticHost()) return "";
  return (readStored() ?? DEFAULT_REMOTE_BACKEND).replace(/\/+$/, "");
}

export function setBackendBase(url: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, url.trim());
  } catch {
    /* almacenamiento bloqueado: se usará el valor por defecto */
  }
}

export function telemetryUrl(): string {
  const base = backendBase();
  if (base) return `${base.replace(/^http/, "ws")}/ws/telemetry`;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/telemetry`;
}
