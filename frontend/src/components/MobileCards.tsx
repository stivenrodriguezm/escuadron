import type { ReactNode } from "react";
import type { BacktestResult, Position, Trade } from "../types";
import { fmtDateTime, fmtPct, fmtPrice, fmtUsd, tone } from "./format";

/** Par clave/valor compacto para las tarjetas móviles. */
export function KV({ label, value, className = "" }: { label: string; value: ReactNode; className?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[10.5px] uppercase tracking-wide text-ink-faint">{label}</div>
      <div className={`num truncate text-[12.5px] text-[#C9CDD6] ${className}`}>{value}</div>
    </div>
  );
}

function SideBadge({ side }: { side: "LONG" | "SHORT" }) {
  const long = side === "LONG";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10.5px] font-medium ${long ? "bg-gain/10 text-gain" : "bg-loss/10 text-loss"}`}>
      {side}
    </span>
  );
}

export function PositionCard({ p }: { p: Position }) {
  return (
    <div className="px-4 py-3.5">
      <div className="flex items-center gap-2">
        <span className="text-[14px] font-medium">{p.symbol}</span>
        <SideBadge side={p.side} />
        <span className={`num ml-auto text-[15px] font-medium ${tone(p.unrealized_pnl)}`}>{fmtUsd(p.unrealized_pnl, true)}</span>
      </div>
      <div className="mt-2.5 grid grid-cols-3 gap-x-3 gap-y-2">
        <KV label="Entrada" value={fmtPrice(p.entry_price)} />
        <KV label="Actual" value={fmtPrice(p.current_price)} />
        <KV label="Cantidad" value={p.quantity} />
        <KV label="Stop" value={<>{fmtPrice(p.stop_loss)}{p.breakeven_moved && <span className="ml-1 text-[10px] text-warn">BE</span>}</>} />
        <KV label="Take-profit" value={fmtPrice(p.take_profit)} />
        <KV label="Comisión" value={fmtUsd(p.entry_fee)} />
      </div>
      <div className="mt-2 text-[11px] text-ink-faint">
        Abierta {fmtDateTime(p.opened_at)} · funding {fmtUsd(p.accumulated_funding)}
      </div>
    </div>
  );
}

export function TradeCard({ t }: { t: Trade }) {
  return (
    <div className="px-4 py-3.5">
      <div className="flex items-center gap-2">
        <span className="text-[14px] font-medium">{t.symbol}</span>
        <SideBadge side={t.side} />
        <span className="text-[11px] text-ink-faint">{t.exit_reason}</span>
        <span className={`num ml-auto text-[15px] font-medium ${tone(t.net_pnl)}`}>{fmtUsd(t.net_pnl, true)}</span>
      </div>
      <div className="mt-2.5 grid grid-cols-3 gap-x-3 gap-y-2">
        <KV label="Entrada" value={fmtPrice(t.entry_price)} />
        <KV label="Salida" value={fmtPrice(t.exit_price)} />
        <KV label="PnL bruto" value={fmtUsd(t.gross_pnl, true)} className={tone(t.gross_pnl)} />
        <KV label="Comisiones" value={fmtUsd(t.entry_fee + t.exit_fee)} />
        <KV label="Slippage" value={fmtUsd(t.slippage_cost)} />
        <KV label="Funding" value={fmtUsd(t.funding_paid)} />
      </div>
      <div className="mt-2 flex justify-between text-[11px] text-ink-faint">
        <span>{fmtDateTime(t.closed_at)}</span>
        <span>Balance <span className="num text-ink-dim">{fmtUsd(t.equity_after)}</span></span>
      </div>
    </div>
  );
}

interface ResultCardProps {
  r: BacktestResult;
  selected: boolean;
  onSelect: () => void;
  onApply: () => void;
}

export function ResultCard({ r, selected, onSelect, onApply }: ResultCardProps) {
  return (
    <div className={`px-4 py-3.5 ${selected ? "bg-panel2" : ""}`} onClick={onSelect}>
      <div className="flex items-center gap-2">
        <span className="num text-[12.5px] text-ink-dim">
          Umbral <span className="text-ink">{r.score_threshold}</span> · SL <span className="text-ink">{r.sl_atr_mult}</span> · TP{" "}
          <span className="text-ink">{r.tp_atr_mult}</span>
        </span>
        <span className={`num ml-auto text-[15px] font-medium ${tone(r.compound_return_pct)}`}>{fmtPct(r.compound_return_pct)}</span>
      </div>
      <div className="mt-2.5 grid grid-cols-4 gap-x-3 gap-y-2">
        <KV label="Trades" value={r.trades} />
        <KV label="Win" value={`${r.win_rate_pct.toFixed(0)}%`} />
        <KV label="Sharpe" value={r.sharpe_ratio.toFixed(2)} />
        <KV label="Max DD" value={`${r.max_drawdown_pct.toFixed(1)}%`} />
      </div>
      <button
        className="btn mt-3 w-full justify-center"
        onClick={(e) => {
          e.stopPropagation();
          onApply();
        }}
      >
        Aplicar en vivo
      </button>
    </div>
  );
}
