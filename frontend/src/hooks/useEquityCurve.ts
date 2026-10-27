import { useEffect, useState } from "react";
import type { ChartPoint } from "../components/EquityChart";
import type { EquityPoint } from "../types";
import { api } from "./api";

interface EquityResponse {
  initial_capital: number;
  points: EquityPoint[];
}

/** Curva persistida (snapshots de 60 s) + punto en vivo de la telemetría. */
export function useEquityCurve(liveEquity: number | undefined, hours = 24 * 30) {
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [initial, setInitial] = useState<number | undefined>();

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await api.get<EquityResponse>(`/api/equity?hours=${hours}`);
        if (!alive) return;
        setInitial(res.initial_capital);
        setPoints(res.points.map((p) => ({ ts: new Date(p.t).getTime(), equity: p.equity })));
      } catch {
        /* backend no disponible: se reintenta en el próximo ciclo */
      }
    };
    void load();
    const id = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [hours]);

  const withLive = liveEquity !== undefined ? [...points, { ts: Date.now(), equity: liveEquity }] : points;
  return { points: withLive, initial };
}
