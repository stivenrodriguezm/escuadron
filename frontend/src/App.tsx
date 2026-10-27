import { useState } from "react";
import { Layout } from "./components/Layout";
import { api } from "./hooks/api";
import { useTelemetry } from "./hooks/useTelemetry";
import type { ViewKey } from "./types";
import { AgentsView } from "./views/AgentsView";
import { BacktestView } from "./views/BacktestView";
import { DashboardView } from "./views/DashboardView";
import { LedgerView } from "./views/LedgerView";
import { SettingsView } from "./views/SettingsView";

export default function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const telemetry = useTelemetry();
  const { data, socketOpen } = telemetry;

  const toggle = async (action: "START" | "PAUSE" | "KILL_SWITCH") => {
    try {
      await api.post("/api/engine/toggle", { action });
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "No se pudo cambiar el estado del motor");
    }
  };

  return (
    <Layout
      view={view}
      onNavigate={setView}
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
