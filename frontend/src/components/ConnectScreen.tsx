import { useEffect, useState } from "react";
import { Github, PlugZap } from "lucide-react";
import { backendBase, isStaticHost, setBackendBase } from "../hooks/backend";

const REPO_URL = "https://github.com/stivenrodriguezm/escuadron";

/** Estado de espera; en GitHub Pages explica cómo conectar con el motor local. */
export function ConnectScreen() {
  const [waited, setWaited] = useState(false);
  const [url, setUrl] = useState(backendBase());

  useEffect(() => {
    const id = setTimeout(() => setWaited(true), 2500);
    return () => clearTimeout(id);
  }, []);

  if (!isStaticHost() || !waited) {
    return <div className="grid h-full place-items-center text-[13px] text-ink-faint">Conectando con el motor…</div>;
  }

  return (
    <div className="grid h-full place-items-center px-6">
      <div className="panel w-full max-w-[520px] p-7">
        <div className="flex items-center gap-2.5">
          <PlugZap size={17} className="text-warn" />
          <h2 className="text-[15px] font-semibold">Motor no conectado</h2>
        </div>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-dim">
          Este dashboard es solo la interfaz. Los agentes, el ledger y la conexión con Binance corren en tu
          máquina; arranca el motor y esta página se conectará sola.
        </p>
        <pre className="num mt-4 overflow-x-auto rounded-md border border-line bg-[#0D0F15] p-3 text-[12px] text-ink-dim">
{`git clone ${REPO_URL}.git
cd escuadron && ./start.sh`}
        </pre>
        <label className="label mt-5 block">Dirección del motor</label>
        <div className="mt-1.5 flex gap-2">
          <input className="input num" value={url} onChange={(e) => setUrl(e.target.value)} />
          <button
            className="btn btn-primary shrink-0"
            onClick={() => {
              setBackendBase(url);
              window.location.reload();
            }}
          >
            Conectar
          </button>
        </div>
        <p className="mt-2 text-[11.5px] text-ink-faint">
          Chrome puede pedir permiso para acceder a la red local: acéptalo. Safari bloquea esta conexión; usa
          http://localhost:8000 directamente.
        </p>
        <a className="mt-5 inline-flex items-center gap-1.5 text-[12px] text-ink-dim hover:text-ink" href={REPO_URL}>
          <Github size={13} /> Código y documentación
        </a>
      </div>
    </div>
  );
}
