import { useEffect, useState } from "react";
import { ConnectScreen } from "./components/ConnectScreen";
import { Layout } from "./components/Layout";
import { api } from "./hooks/api";
import { useTelemetry } from "./hooks/useTelemetry";
import type { ViewKey } from "./types";
import { AgentsView } from "./views/AgentsView";
import { BacktestView } from "./views/BacktestView";
import { DashboardView } from "./views/DashboardView";
import { LedgerView } from "./views/LedgerView";
import { SettingsView } from "./views/SettingsView";

const VIEWS: ViewKey[] = ["dashboard", "agents", "ledger", "backtest", "settings"];

/** La vista vive en el hash (#agents…): el botón Atrás del móvil navega entre pestañas. */
function viewFromHash(): ViewKey {
  const hash = window.location.hash.slice(1);
  return VIEWS.find((v) => v === hash) ?? "dashboard";
}

export default function App() {
  const [view, setView] = useState<ViewKey>(viewFromHash);
  useEffect(() => {
    const onHash = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = (v: ViewKey) => {
    if (v !== view) window.location.hash = v;
  };
  const telemetry = useTelemetry();
  const { data, socketOpen, authRequired } = telemetry;

  const toggle = async (action: "START" | "PAUSE" | "KILL_SWITCH") => {
    try {
      await api.post("/api/engine/toggle", { action });
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "No se pudo cambiar el estado del motor");
    }
  };

  if (authRequired) return <ConnectScreen authRequired />;

  return (
    <Layout
      view={view}
      onNavigate={navigate}
      streamConnected={data?.stream.connected ?? false}
      socketOpen={socketOpen}
      mode={data?.mode}
      running={data?.running ?? false}
      onToggle={toggle}
    >
      {view === "dashboard" && <DashboardView telemetry={telemetry} />}
      {view === "agents" && <AgentsView telemetry={telemetry} />}
      {view === "ledger" && <LedgerView telemetry={telemetry} />}
      {view === "backtest" && <BacktestView />}
      {view === "settings" && <SettingsView />}
    </Layout>
  );
}
