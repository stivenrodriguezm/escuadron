import type { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  footer?: ReactNode;
  action?: ReactNode;
}

export function KpiCard({ label, value, delta, footer, action }: KpiCardProps) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        {action}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="num text-[22px] font-medium tracking-tight">{value}</span>
        {delta}
      </div>
      {footer && <div className="text-[12px] text-ink-faint">{footer}</div>}
    </div>
  );
}
