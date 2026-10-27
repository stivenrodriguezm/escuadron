import { useEffect, useRef, useState } from "react";
import type { ConsensusLog, TelemetryMessage } from "../types";
import { telemetryUrl } from "./backend";

const MAX_LOGS = 300;

export interface TelemetryState {
  data: TelemetryMessage | null;
  logs: ConsensusLog[];
  socketOpen: boolean;
}

/** WebSocket unificado /ws/telemetry con reconexión automática. */
export function useTelemetry(): TelemetryState {
  const [data, setData] = useState<TelemetryMessage | null>(null);
  const [logs, setLogs] = useState<ConsensusLog[]>([]);
  const [socketOpen, setSocketOpen] = useState(false);
  const retry = useRef(1000);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;

    const connect = () => {
      ws = new WebSocket(telemetryUrl());
      ws.onopen = () => {
        retry.current = 1000;
        setSocketOpen(true);
      };
      ws.onmessage = (ev: MessageEvent<string>) => {
        const msg = JSON.parse(ev.data) as TelemetryMessage;
        setData(msg);
        if (msg.logs.length) {
          setLogs((prev) => {
            const seen = new Set(prev.map((l) => l.id));
            const merged = [...prev, ...msg.logs.filter((l) => !seen.has(l.id))];
            return merged.slice(-MAX_LOGS);
          });
        }
      };
      ws.onclose = () => {
        setSocketOpen(false);
        if (!disposed) {
          timer = setTimeout(connect, retry.current);
          retry.current = Math.min(retry.current * 2, 15000);
        }
      };
    };
    connect();
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { data, logs, socketOpen };
}
