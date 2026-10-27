/**
 * Ubicación del backend.
 * - Servida por el propio backend (./start.sh) o por Vite: rutas relativas.
 * - Publicada en GitHub Pages: el motor corre en la máquina del usuario o en su servidor
 *   (por defecto http://localhost:8000; editable desde la pantalla de conexión).
 * - Si el servidor tiene API_TOKEN, el token se guarda en el navegador y viaja en cada petición.
 */
const STORAGE_KEY = "escuadron.backendUrl";
const TOKEN_KEY = "escuadron.apiToken";
export const AUTH_EVENT = "escuadron:auth-required";
export const DEFAULT_REMOTE_BACKEND = "http://localhost:8000";

export const isStaticHost = (): boolean => window.location.hostname.endsWith("github.io");

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value.trim());
  } catch {
    /* almacenamiento bloqueado: se usará el valor por defecto */
  }
}

/** Token de acceso del motor (solo si el servidor tiene API_TOKEN). */
export const getToken = (): string => read(TOKEN_KEY) ?? "";
export const setToken = (token: string): void => write(TOKEN_KEY, token);

/** Base HTTP sin barra final ("" = mismo origen). */
export function backendBase(): string {
  if (!isStaticHost()) return "";
  return (read(STORAGE_KEY) ?? DEFAULT_REMOTE_BACKEND).replace(/\/+$/, "");
}

export const setBackendBase = (url: string): void => write(STORAGE_KEY, url);

export function telemetryUrl(): string {
  const base = backendBase();
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const url = base ? `${base.replace(/^http/, "ws")}/ws/telemetry` : `${proto}://${window.location.host}/ws/telemetry`;
  const token = getToken();
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}
