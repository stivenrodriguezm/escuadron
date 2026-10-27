import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useIsMobile } from "../hooks/useMediaQuery";
import { fmtUsd } from "./format";

export interface ChartPoint {
  ts: number;
  equity: number;
}

interface EquityChartProps {
  points: ChartPoint[];
  baseline?: number;
  height?: number;
}

const tickTime = (ts: number) =>
  new Date(ts).toLocaleString("es-ES", { hour12: false, day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
const tickDay = (ts: number) => new Date(ts).toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" });
// Eje Y en móvil: sin decimales ("$1,004"), y en miles solo a partir de $100k para no repetir etiquetas
const wholeUsd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const compactUsd = (v: number) => (Math.abs(v) >= 100_000 ? `$${(v / 1000).toFixed(0)}k` : wholeUsd.format(v));

export function EquityChart({ points, baseline, height = 260 }: EquityChartProps) {
  const mobile = useIsMobile();
  if (mobile) height = Math.min(height, 210);
  if (points.length < 2) {
    return (
      <div className="grid place-items-center text-[12.5px] text-ink-faint" style={{ height }}>
        La curva se dibuja a medida que se registran snapshots (cada 60 s).
      </div>
    );
  }
  const values = points.map((p) => p.equity).concat(baseline ? [baseline] : []);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * 0.15, max * 0.0005);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10B981" stopOpacity={0.22} />
            <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#1E2230" strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="ts" type="number" domain={["dataMin", "dataMax"]} scale="time" tickFormatter={mobile ? tickDay : tickTime}
          stroke="#5D6474" fontSize={mobile ? 10 : 11} tickLine={false} axisLine={false} minTickGap={mobile ? 40 : 60}
        />
        <YAxis
          domain={[min - pad, max + pad]} stroke="#5D6474" fontSize={mobile ? 10 : 11} tickLine={false} axisLine={false}
          width={mobile ? 54 : 78} tickFormatter={(v: number) => (mobile ? compactUsd(v) : fmtUsd(v))}
        />
        <Tooltip
          contentStyle={{ background: "#11131A", border: "1px solid #1E2230", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(v: number) => tickTime(v)}
          formatter={(v: number) => [fmtUsd(v), "Balance compuesto"]}
        />
        {baseline !== undefined && (
          <ReferenceLine y={baseline} stroke="#5D6474" strokeDasharray="4 4"
            label={mobile ? undefined : { value: "Capital inicial", fill: "#5D6474", fontSize: 10, position: "insideTopLeft" }} />
        )}
        <Area type="monotone" dataKey="equity" stroke="#10B981" strokeWidth={1.75} fill="url(#eqFill)" isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
