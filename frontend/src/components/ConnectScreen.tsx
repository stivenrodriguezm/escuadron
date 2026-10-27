import { useEffect, useState } from "react";
import { Github, KeyRound, PlugZap } from "lucide-react";
import { backendBase, getToken, isStaticHost, setBackendBase, setToken } from "../hooks/backend";

const REPO_URL = "https://github.com/stivenrodriguezm/escuadron";

/**
 * Espera de conexión. Muestra el formulario cuando el motor pide token (servidor público)
 * o cuando, desde GitHub Pages, no se encuentra el motor.
 */
export function ConnectScreen({ authRequired = false }: { authRequired?: boolean }) {
  const [waited, setWaited] = useState(false);
  const [url, setUrl] = useState(backendBase());
  const [token, setTokenInput] = useState(getToken());

  useEffect(() => {
    const id = setTimeout(() => setWaited(true), 2500);
    return () => clearTimeout(id);
  }, []);

  const showForm = authRequired || (isStaticHost() && waited);
  if (!showForm) {
    return <div className="grid h-full place-items-center text-[13px] text-ink-faint">Conectando con el motor…</div>;
  }

  const connect = () => {
    if (isStaticHost()) setBackendBase(url);
    setToken(token);
    window.location.reload();
  };

  return (
    <div className="pt-safe grid min-h-full place-items-center px-4 py-8">
      <div className="panel w-full max-w-[520px] p-5 md:p-7">
        <div className="flex items-center gap-2.5">
          {authRequired ? <KeyRound size={17} className="text-accent" /> : <PlugZap size={17} className="text-warn" />}
          <h2 className="text-[15px] font-semibold">{authRequired ? "Acceso al motor" : "Motor no conectado"}</h2>
        </div>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-dim">
          {authRequired
            ? "Este motor está protegido. Introduce el token de acceso (API_TOKEN del servidor)."
            : "Este dashboard es solo la interfaz. Los agentes, el ledger y la conexión con Binance corren en tu máquina o en tu servidor; arranca el motor e indica su dirección."}
        </p>
        {!authRequired && (
          <pre className="num mt-4 overflow-x-auto rounded-md border border-line bg-[#0D0F15] p-3 text-[12px] text-ink-dim">
{`git clone ${REPO_URL}.git
cd escuadron && ./start.sh`}
          </pre>
        )}
        {isStaticHost() && (
          <>
            <label className="label mt-5 block">Dirección del motor</label>
            <input className="input num mt-1.5" value={url} onChange={(e) => setUrl(e.target.value)}
                   placeholder="https://1-2-3-4.sslip.io" />
          </>
        )}
        <label className="label mt-4 block">Token de acceso {authRequired ? "" : "(si el servidor lo exige)"}</label>
        <div className="mt-1.5 flex gap-2">
          <input className="input num" type="password" value={token} onChange={(e) => setTokenInput(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && connect()} />
          <button className="btn btn-primary shrink-0 justify-center" onClick={connect}>Conectar</button>
        </div>
        {isStaticHost() && (
          <p className="mt-2 text-[11.5px] text-ink-faint">
            Para un motor en localhost, Chrome puede pedir permiso de red local (acéptalo); Safari lo bloquea.
          </p>
        )}
        <a className="mt-5 inline-flex items-center gap-1.5 text-[12px] text-ink-dim hover:text-ink" href={REPO_URL}>
          <Github size={13} /> Código y documentación
        </a>
      </div>
    </div>
  );
}
