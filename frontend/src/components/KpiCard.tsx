import type { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  footer?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function KpiCard({ label, value, delta, footer, action, className = "" }: KpiCardProps) {
  return (
    <div className={`panel flex min-w-0 flex-col gap-1.5 p-3.5 md:gap-2 md:p-4 ${className}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="label leading-tight">{label}</span>
        {action}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="num text-[19px] font-medium tracking-tight md:text-[22px]">{value}</span>
        {delta}
      </div>
      {footer && <div className="text-[11.5px] leading-snug text-ink-faint md:text-[12px]">{footer}</div>}
    </div>
  );
}
